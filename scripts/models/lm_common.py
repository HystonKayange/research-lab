#!/usr/bin/env python3
"""Shared utilities for controlled LM baselines (character / BPE / Unigram).

Python 3.11+. Requires torch and sentencepiece for full training.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

# Make tokenizer common importable
_REPO_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_REPO_SCRIPTS / "tokenizers") not in sys.path:
    sys.path.insert(0, str(_REPO_SCRIPTS / "tokenizers"))

import common as tok_common  # type: ignore  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def git_commit(repo_root: Path) -> str | None:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def env_metadata(repo_root: Path) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "python_version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "git_commit": git_commit(repo_root),
        "sentencepiece_version": tok_common.sentencepiece_version(),
    }
    try:
        import torch

        meta["torch_version"] = torch.__version__
        meta["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            meta["cuda_device_name"] = torch.cuda.get_device_name(0)
            meta["cuda_version"] = getattr(torch.version, "cuda", None)
    except ImportError:
        meta["torch_version"] = None
        meta["cuda_available"] = False
    return meta


def verify_frozen_split(split_root: Path) -> dict[str, Any]:
    freeze = split_root / "metadata" / "FROZEN_SPLIT.json"
    if not freeze.is_file():
        raise FileNotFoundError(f"Missing freeze marker: {freeze}")
    fr = load_json(freeze)
    if not fr.get("frozen"):
        raise ValueError("Split is not frozen")
    checksums = load_json(split_root / "metadata" / "checksums.json")
    bad: list[str] = []
    for rel, exp in checksums.items():
        p = split_root / rel
        if not p.is_file() or sha256_file(p) != exp:
            bad.append(rel)
    if bad:
        raise ValueError(f"Split checksum mismatch: {bad[:10]}")
    return {"frozen": True, "n_ok": len(checksums), "freeze": fr}


def verify_tokenizer_artifacts(tok_cfg: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    path = repo_root / tok_cfg["path"]
    if not path.is_dir():
        raise FileNotFoundError(f"Tokenizer path missing: {path}")
    man_path = path / "manifest.json"
    if not man_path.is_file():
        raise FileNotFoundError(f"Missing tokenizer manifest: {man_path}")
    man = load_json(man_path)
    arts = man.get("artifacts") or {}
    # Verify stable model artifacts only (not self-referential manifest.json)
    check_names = []
    if tok_cfg["kind"] == "sentencepiece":
        check_names = ["model.model", "model.vocab", "training_config.json"]
    elif tok_cfg["kind"] == "character":
        check_names = ["vocab.json", "tokenizer_config.json"]
    for name in check_names:
        exp = arts.get(name)
        p = path / name
        if not p.is_file():
            raise FileNotFoundError(f"Missing tokenizer file: {p}")
        if exp is not None and sha256_file(p) != exp:
            raise ValueError(f"Tokenizer artifact checksum mismatch: {p}")
    return {
        "path": str(path),
        "manifest_sha256": sha256_file(man_path),
        "tokenizer_id": tok_cfg["tokenizer_id"],
        "artifact_checks": check_names,
    }

def ensure_run_dir_free(path: Path, *, force: bool = False) -> None:
    """Refuse non-empty run dirs. Empty dirs are allowed (mkdir will reuse)."""
    if not path.exists():
        return
    entries = [p for p in path.iterdir() if p.name not in {".", ".."}]
    # Ignore ephemeral lock files if any slipped into the run dir historically
    entries = [p for p in entries if p.name not in {".run.lock", ".lock"}]
    if entries and not force:
        raise FileExistsError(
            f"Run directory exists and is non-empty: {path}. "
            "Refuse overwrite; use new version/seed or --force only with care."
        )


# ---------------------------------------------------------------------------
# Tokenizer adapters
# ---------------------------------------------------------------------------


class TokenizerAdapter:
    pad_id: int
    unk_id: int
    bos_id: int
    eos_id: int
    vocab_size: int
    tokenizer_id: str

    def encode(self, text: str) -> list[int]:
        raise NotImplementedError

    def decode(self, ids: Sequence[int]) -> str:
        raise NotImplementedError

    def id_to_token(self, i: int) -> str:
        raise NotImplementedError


class CharacterAdapter(TokenizerAdapter):
    def __init__(self, path: Path) -> None:
        vocab = load_json(path / "vocab.json")
        cfg = load_json(path / "tokenizer_config.json")
        self.tok = tok_common.CharacterTokenizer(vocab["stoi"], vocab["itos"])
        self.pad_id = int(cfg["pad_id"])
        self.unk_id = int(cfg["unk_id"])
        self.bos_id = int(cfg["bos_id"])
        self.eos_id = int(cfg["eos_id"])
        self.vocab_size = int(cfg["vocab_size"])
        self.tokenizer_id = "character"

    def encode(self, text: str) -> list[int]:
        return self.tok.encode(text).ids

    def decode(self, ids: Sequence[int]) -> str:
        return self.tok.decode(list(ids))

    def id_to_token(self, i: int) -> str:
        return self.tok.itos[i] if 0 <= i < len(self.tok.itos) else "<unk>"


class SentencePieceAdapter(TokenizerAdapter):
    def __init__(self, path: Path, tokenizer_id: str) -> None:
        self.wrap = tok_common.SentencePieceWrapper(path / "model.model", tokenizer_id)
        self.sp = self.wrap.sp
        self.pad_id = int(self.sp.pad_id())
        self.unk_id = int(self.sp.unk_id())
        self.bos_id = int(self.sp.bos_id())
        self.eos_id = int(self.sp.eos_id())
        self.vocab_size = int(self.sp.get_piece_size())
        self.tokenizer_id = tokenizer_id

    def encode(self, text: str) -> list[int]:
        return list(self.sp.encode(text, out_type=int))

    def decode(self, ids: Sequence[int]) -> str:
        return self.sp.decode(list(ids))

    def id_to_token(self, i: int) -> str:
        return self.sp.id_to_piece(i)


def load_tokenizer(tok_cfg: dict[str, Any], repo_root: Path) -> TokenizerAdapter:
    path = repo_root / tok_cfg["path"]
    if tok_cfg["kind"] == "character":
        return CharacterAdapter(path)
    return SentencePieceAdapter(path, tok_cfg["tokenizer_id"])


# ---------------------------------------------------------------------------
# Sequence packing
# ---------------------------------------------------------------------------


@dataclass
class PackedBatchMeta:
    n_sequences: int
    n_tokens: int
    n_characters_in_source_text: int
    n_bytes_in_source_text: int
    n_words_in_source_text: int
    truncation_events: int
    packing_method: str
    encoding_sha256: str


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def pack_lines_to_sequences(
    lines: Sequence[str],
    tokenizer: TokenizerAdapter,
    *,
    context_length: int,
    eos_between_lines: bool = True,
) -> tuple[list[list[int]], PackedBatchMeta, list[str], list[float]]:
    """Pack lines into fixed-length sequences with per-sequence character exposure credits.

    Character accounting: for each source line with C characters and T content tokens
    (excluding EOS), each content token receives C/T character credit; EOS and PAD get 0.

    Returns:
      sequences, meta, lines, char_credits_per_sequence
    """
    stream: list[int] = []
    char_stream: list[float] = []
    trunc = 0
    total_chars = 0
    total_bytes = 0
    total_words = 0
    for line in lines:
        c = len(line)
        total_chars += c
        total_bytes += len(line.encode("utf-8"))
        total_words += count_words(line)
        ids = tokenizer.encode(line)
        if ids:
            credit = c / len(ids)
            stream.extend(ids)
            char_stream.extend([credit] * len(ids))
        if eos_between_lines and tokenizer.eos_id >= 0:
            stream.append(tokenizer.eos_id)
            char_stream.append(0.0)

    assert len(stream) == len(char_stream)
    sequences: list[list[int]] = []
    seq_char_credits: list[float] = []
    i = 0
    while i + context_length <= len(stream):
        sequences.append(stream[i : i + context_length])
        # character exposure for training uses content credits on the *input* side
        # (positions 0..context_length-2 map to predictions of 1..context_length-1)
        seq_char_credits.append(float(sum(char_stream[i : i + context_length - 1])))
        i += context_length
    if i < len(stream):
        tail = stream[i:]
        tail_chars = char_stream[i:]
        pad_len = context_length - len(tail)
        if pad_len > 0 and tokenizer.pad_id >= 0:
            tail = tail + [tokenizer.pad_id] * pad_len
            tail_chars = tail_chars + [0.0] * pad_len
            sequences.append(tail)
            seq_char_credits.append(float(sum(tail_chars[: context_length - 1])))
        else:
            trunc += 1

    enc_mat = sha256_text(
        json.dumps([s for s in sequences[:3]]) + f"|n={len(sequences)}|tok={len(stream)}"
    )
    meta = PackedBatchMeta(
        n_sequences=len(sequences),
        n_tokens=len(stream),
        n_characters_in_source_text=total_chars,
        n_bytes_in_source_text=total_bytes,
        n_words_in_source_text=total_words,
        truncation_events=trunc,
        packing_method="line_pack_with_eos_nonoverlap_windows_char_credits",
        encoding_sha256=enc_mat,
    )
    return sequences, meta, list(lines), seq_char_credits


def sequences_to_tensors(sequences: list[list[int]], pad_id: int):
    import torch

    if not sequences:
        return torch.zeros((0, 0), dtype=torch.long), torch.zeros((0, 0), dtype=torch.long)
    x = torch.tensor([s[:-1] for s in sequences], dtype=torch.long)
    y = torch.tensor([s[1:] for s in sequences], dtype=torch.long)
    return x, y


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


def build_gpt(
    *,
    vocab_size: int,
    n_layer: int,
    n_embd: int,
    n_head: int,
    n_inner: int,
    context_length: int,
    dropout: float,
    tie_embeddings: bool,
    pre_ln: bool = True,
):
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class CausalSelfAttention(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            assert n_embd % n_head == 0
            self.n_head = n_head
            self.n_embd = n_embd
            self.c_attn = nn.Linear(n_embd, 3 * n_embd)
            self.c_proj = nn.Linear(n_embd, n_embd)
            self.attn_drop = nn.Dropout(dropout)
            self.resid_drop = nn.Dropout(dropout)
            mask = torch.tril(torch.ones(context_length, context_length)).view(
                1, 1, context_length, context_length
            )
            self.register_buffer("mask", mask)

        def forward(self, x):
            B, T, C = x.size()
            qkv = self.c_attn(x)
            q, k, v = qkv.split(self.n_embd, dim=2)
            hs = C // self.n_head
            q = q.view(B, T, self.n_head, hs).transpose(1, 2)
            k = k.view(B, T, self.n_head, hs).transpose(1, 2)
            v = v.view(B, T, self.n_head, hs).transpose(1, 2)
            att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(hs))
            att = att.masked_fill(self.mask[:, :, :T, :T] == 0, float("-inf"))
            att = F.softmax(att, dim=-1)
            att = self.attn_drop(att)
            y = att @ v
            y = y.transpose(1, 2).contiguous().view(B, T, C)
            return self.resid_drop(self.c_proj(y))

    class Block(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.ln1 = nn.LayerNorm(n_embd)
            self.attn = CausalSelfAttention()
            self.ln2 = nn.LayerNorm(n_embd)
            self.mlp = nn.Sequential(
                nn.Linear(n_embd, n_inner),
                nn.GELU(),
                nn.Linear(n_inner, n_embd),
                nn.Dropout(dropout),
            )
            self.pre_ln = pre_ln

        def forward(self, x):
            if self.pre_ln:
                x = x + self.attn(self.ln1(x))
                x = x + self.mlp(self.ln2(x))
            else:
                x = self.ln1(x + self.attn(x))
                x = self.ln2(x + self.mlp(x))
            return x

    class GPT(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.context_length = context_length
            self.vocab_size = vocab_size
            self.wte = nn.Embedding(vocab_size, n_embd)
            self.wpe = nn.Embedding(context_length, n_embd)
            self.drop = nn.Dropout(dropout)
            self.blocks = nn.ModuleList([Block() for _ in range(n_layer)])
            self.ln_f = nn.LayerNorm(n_embd)
            self.lm_head = nn.Linear(n_embd, vocab_size, bias=False)
            if tie_embeddings:
                self.lm_head.weight = self.wte.weight
            self.apply(self._init)

        def _init(self, module):
            if isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)

        def forward(self, idx, targets=None, pad_id: int = -1):
            B, T = idx.size()
            if T > self.context_length:
                raise ValueError("sequence longer than context")
            pos = torch.arange(0, T, device=idx.device).unsqueeze(0)
            x = self.drop(self.wte(idx) + self.wpe(pos))
            for block in self.blocks:
                x = block(x)
            x = self.ln_f(x)
            logits = self.lm_head(x)
            loss = None
            nll_sum = None
            n_tokens = None
            if targets is not None:
                # token NLL in nats
                loss_flat = F.cross_entropy(
                    logits.view(-1, logits.size(-1)),
                    targets.view(-1),
                    ignore_index=pad_id if pad_id >= 0 else -100,
                    reduction="none",
                )
                mask = (targets.view(-1) != pad_id) if pad_id >= 0 else torch.ones_like(loss_flat)
                mask = mask.float()
                n_tokens = int(mask.sum().item())
                nll_sum = (loss_flat * mask).sum()
                loss = nll_sum / max(n_tokens, 1)
            return logits, loss, nll_sum, n_tokens

        def count_parameters(self) -> dict[str, int]:
            total = sum(p.numel() for p in self.parameters())
            emb = self.wte.weight.numel() + self.wpe.weight.numel()
            # if tied, lm_head not extra
            non_emb = total - emb
            return {
                "total": total,
                "embedding": emb,
                "non_embedding": non_emb,
                "tied_embeddings": bool(
                    self.lm_head.weight.data_ptr() == self.wte.weight.data_ptr()
                ),
            }

    return GPT()


# ---------------------------------------------------------------------------
# Metrics: BPC / BPB
# ---------------------------------------------------------------------------


def nll_nats_to_bits(nll_nats: float) -> float:
    return nll_nats / math.log(2.0)


def frozen_train_character_count(train_text: str) -> int:
    """Content character count matching exposure accounting (sum of line lengths).

    Newlines between lines are not counted — same definition as per-line
    character credits used during packing.
    """
    return sum(len(line) for line in train_text.splitlines())


def effective_epochs(
    cumulative_original_characters_processed: float,
    frozen_training_corpus_character_count: int,
) -> float | None:
    """Derived metric: characters_processed / frozen_corpus_chars.

    Character exposure remains the primary accounting unit.
    """
    if frozen_training_corpus_character_count <= 0:
        return None
    return float(cumulative_original_characters_processed) / float(
        frozen_training_corpus_character_count
    )


def bits_per_character(total_nll_nats: float, n_chars: int) -> float | None:
    if n_chars <= 0:
        return None
    return nll_nats_to_bits(total_nll_nats) / n_chars


def bits_per_byte(total_nll_nats: float, n_bytes: int) -> float | None:
    if n_bytes <= 0:
        return None
    return nll_nats_to_bits(total_nll_nats) / n_bytes


def token_perplexity_from_nll(total_nll_nats: float, n_tokens: int) -> float | None:
    """NOT cross-comparable across tokenizers."""
    if n_tokens <= 0:
        return None
    return math.exp(total_nll_nats / n_tokens)


# ---------------------------------------------------------------------------
# Arch resolution
# ---------------------------------------------------------------------------


def resolve_arch(config: dict[str, Any], track: str, tokenizer_id: str) -> dict[str, Any]:
    if track == "architecture_matched":
        a = dict(config["architecture_matched"])
        a["track"] = track
        return a
    if track == "parameter_matched":
        pm = config["parameter_matched"]
        base = {
            "n_layer": pm["overrides"][tokenizer_id]["n_layer"],
            "n_embd": pm["overrides"][tokenizer_id]["n_embd"],
            "n_head": pm["overrides"][tokenizer_id]["n_head"],
            "n_inner": pm["overrides"][tokenizer_id]["n_inner"],
            "dropout": pm["dropout"],
            "context_length": pm["context_length"],
            "pre_ln": pm["pre_ln"],
            "tie_embeddings": pm["tie_embeddings"],
            "positional_encoding": pm["positional_encoding"],
            "track": track,
            "tolerance_fraction": pm["tolerance_fraction"],
        }
        return base
    raise ValueError(f"Unknown track: {track}")


def longest_common_substring_len(a: str, b: str, max_scan: int = 50000) -> int:
    """O(n*m) LCS length of substrings — limited scan for diagnostics."""
    if not a or not b:
        return 0
    a = a[:max_scan]
    b = b[:max_scan]
    # rolling hash approximate: use DP on shorter windows
    n, m = len(a), len(b)
    if n * m > 5_000_000:
        # sample: use word-level
        return longest_exact_token_run(a, b)
    prev = [0] * (m + 1)
    best = 0
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        ca = a[i - 1]
        for j in range(1, m + 1):
            if ca == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def longest_exact_token_run(a: str, b: str) -> int:
    wa, wb = a.split(), b.split()
    best = 0
    for i in range(len(wa)):
        for j in range(len(wb)):
            k = 0
            while i + k < len(wa) and j + k < len(wb) and wa[i + k] == wb[j + k]:
                k += 1
            # approximate char length
            if k:
                best = max(best, len(" ".join(wa[i : i + k])))
    return best


def ngram_overlap(gen: str, train: str, n: int = 5) -> float:
    def grams(s: str) -> set[str]:
        toks = s.split()
        if len(toks) < n:
            return set()
        return {" ".join(toks[i : i + n]) for i in range(len(toks) - n + 1)}

    g, t = grams(gen), grams(train)
    if not g:
        return 0.0
    return len(g & t) / len(g)
