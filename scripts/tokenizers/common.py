#!/usr/bin/env python3
"""Shared utilities for Chichewa tokenizer baselines.

Standard library + optional sentencepiece. Python 3.11+.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

SPECIAL_ORDER = ("<pad>", "<unk>", "<bos>", "<eos>")


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


def sha256_json(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256_text(blob)


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


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def git_commit(repo_root: Path) -> str | None:
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


def sentencepiece_version() -> str | None:
    try:
        import sentencepiece as sp  # type: ignore

        return getattr(sp, "__version__", "unknown")
    except ImportError:
        return None


def platform_info() -> dict[str, Any]:
    return {
        "python_version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "sentencepiece_version": sentencepiece_version(),
        "git_commit": None,  # filled by caller
    }


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def identity_normalize(text: str) -> str:
    """Default normalization: identity (no casefold, no NFKC, no strip)."""
    return text


def normalization_audit(sample_lines: Sequence[str], policy: str) -> dict[str, Any]:
    """Show exact transformation applied to sample lines."""
    rows = []
    changed = 0
    for line in sample_lines:
        if policy == "identity":
            out = identity_normalize(line)
        else:
            out = line
        if out != line:
            changed += 1
        rows.append(
            {
                "before_sha256": sha256_text(line),
                "after_sha256": sha256_text(out),
                "unchanged": out == line,
                "before_preview": line[:120],
                "after_preview": out[:120],
            }
        )
    return {
        "policy": policy,
        "n_sampled": len(sample_lines),
        "n_changed": changed,
        "samples": rows[:20],
        "conclusion": (
            "Identity normalization: training text is passed through unchanged."
            if changed == 0 and policy == "identity"
            else f"Policy {policy} changed {changed}/{len(sample_lines)} samples."
        ),
    }


def verify_frozen_split(split_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Verify freeze marker, checksums, and training-path safety."""
    freeze_path = split_root / "metadata" / "FROZEN_SPLIT.json"
    if not freeze_path.is_file():
        raise FileNotFoundError(f"Missing freeze marker: {freeze_path}")
    freeze = load_json(freeze_path)
    if not freeze.get("frozen"):
        raise ValueError(f"Split is not frozen: {freeze_path}")

    checksums_path = split_root / "metadata" / "checksums.json"
    if not checksums_path.is_file():
        raise FileNotFoundError(f"Missing split checksums: {checksums_path}")
    checksums = load_json(checksums_path)
    mismatches: list[str] = []
    for rel, exp in checksums.items():
        p = split_root / rel
        if not p.is_file():
            mismatches.append(f"missing:{rel}")
            continue
        actual = sha256_file(p)
        if actual != exp:
            mismatches.append(f"mismatch:{rel}")
    if mismatches:
        raise ValueError(f"Split checksum verification failed: {mismatches[:10]}")

    # Training inputs safety
    train_cfg = config.get("training_inputs") or {}
    forbidden = list(train_cfg.get("forbidden_path_substrings") or [])
    allowed = list(train_cfg.get("allowed_path_substrings") or ["/train/"])
    paths = []
    for key in ("combined", "bible", "wikipedia"):
        if key in train_cfg:
            paths.append(str(train_cfg[key]))
    for p in paths:
        pl = p.replace("\\", "/")
        for bad in forbidden:
            if bad.replace("\\", "/") in pl:
                raise ValueError(f"Forbidden split path in training inputs: {p}")
        if allowed and not any(a.replace("\\", "/") in pl for a in allowed):
            raise ValueError(f"Training path not under allowed substrings: {p}")

    return {
        "frozen": True,
        "freeze": freeze,
        "n_checksums_verified": len(checksums),
        "training_paths": paths,
    }


def ensure_output_not_exists(path: Path, *, force: bool = False) -> None:
    if path.exists() and any(path.rglob("*")) and not force:
        raise FileExistsError(
            f"Tokenizer experiment directory exists: {path}. "
            "Refuse overwrite; use a new version path."
        )


def percentiles(values: Sequence[float], ps: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {f"p{int(p)}": None for p in ps}
    s = sorted(values)
    n = len(s)
    out: dict[str, float | None] = {}
    for p in ps:
        if n == 1:
            out[f"p{int(p)}"] = float(s[0])
            continue
        k = (p / 100.0) * (n - 1)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            out[f"p{int(p)}"] = float(s[int(k)])
        else:
            out[f"p{int(p)}"] = float(s[f] * (c - k) + s[c] * (k - f))
    return out


def looks_english_heavy(token: str) -> bool:
    """Heuristic diagnostic only — not a language ID."""
    t = token.lstrip("▁")
    if len(t) < 3:
        return False
    ascii_letters = sum(1 for ch in t if ("a" <= ch <= "z") or ("A" <= ch <= "Z"))
    return ascii_letters / max(len(t), 1) > 0.85 and " " not in t


@dataclass
class EncodeResult:
    tokens: list[str]
    ids: list[int]


class CharacterTokenizer:
    """Deterministic character-level tokenizer from training vocabulary only."""

    def __init__(
        self,
        stoi: dict[str, int],
        itos: list[str],
        *,
        unk_token: str = "<unk>",
        pad_token: str = "<pad>",
        bos_token: str = "<bos>",
        eos_token: str = "<eos>",
    ) -> None:
        self.stoi = dict(stoi)
        self.itos = list(itos)
        self.unk_token = unk_token
        self.pad_token = pad_token
        self.bos_token = bos_token
        self.eos_token = eos_token
        if unk_token not in self.stoi:
            raise ValueError("unk token missing from vocab")
        self.unk_id = self.stoi[unk_token]

    @classmethod
    def train_from_text(cls, text: str, specials: Sequence[str] = SPECIAL_ORDER) -> CharacterTokenizer:
        chars = sorted(set(text), key=lambda c: (ord(c), c))
        # Remove specials if they appear as literal substrings of length>1 — specials are multi-char
        # Characters are single Unicode code points; specials are separate reserved tokens.
        itos: list[str] = list(specials)
        for ch in chars:
            if ch not in itos:
                itos.append(ch)
        stoi = {t: i for i, t in enumerate(itos)}
        return cls(stoi, itos)

    def encode(
        self,
        text: str,
        *,
        add_bos: bool = False,
        add_eos: bool = False,
    ) -> EncodeResult:
        tokens: list[str] = []
        ids: list[int] = []
        if add_bos:
            tokens.append(self.bos_token)
            ids.append(self.stoi[self.bos_token])
        for ch in text:
            if ch in self.stoi:
                tokens.append(ch)
                ids.append(self.stoi[ch])
            else:
                tokens.append(self.unk_token)
                ids.append(self.unk_id)
        if add_eos:
            tokens.append(self.eos_token)
            ids.append(self.stoi[self.eos_token])
        return EncodeResult(tokens=tokens, ids=ids)

    def decode(self, ids: Sequence[int]) -> str:
        parts: list[str] = []
        specials = {self.pad_token, self.unk_token, self.bos_token, self.eos_token}
        for i in ids:
            if 0 <= i < len(self.itos):
                tok = self.itos[i]
                if tok not in specials or tok == self.unk_token:
                    # include unk surface as empty? keep as ''
                    if tok == self.unk_token:
                        parts.append("")
                    elif tok not in specials:
                        parts.append(tok)
        return "".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "character",
            "stoi": self.stoi,
            "itos": self.itos,
            "unk_token": self.unk_token,
            "pad_token": self.pad_token,
            "bos_token": self.bos_token,
            "eos_token": self.eos_token,
            "vocab_size": len(self.itos),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CharacterTokenizer:
        return cls(
            d["stoi"],
            d["itos"],
            unk_token=d.get("unk_token", "<unk>"),
            pad_token=d.get("pad_token", "<pad>"),
            bos_token=d.get("bos_token", "<bos>"),
            eos_token=d.get("eos_token", "<eos>"),
        )


class SentencePieceWrapper:
    """Thin wrapper around sentencepiece.SentencePieceProcessor."""

    def __init__(self, model_path: Path, tokenizer_id: str) -> None:
        try:
            import sentencepiece as spm  # type: ignore
        except ImportError as e:
            raise ImportError(
                "sentencepiece is required. Install with: "
                "pip install -r requirements-tokenizers.txt"
            ) from e
        if not model_path.is_file():
            raise FileNotFoundError(f"SentencePiece model missing: {model_path}")
        self.sp = spm.SentencePieceProcessor()
        self.sp.load(str(model_path))
        self.model_path = model_path
        self.tokenizer_id = tokenizer_id

    def encode(self, text: str, *, add_bos: bool = False, add_eos: bool = False) -> EncodeResult:
        ids = list(self.sp.encode(text, out_type=int))
        pieces = list(self.sp.encode(text, out_type=str))
        if add_bos:
            bos = self.sp.bos_id()
            if bos >= 0:
                ids = [bos] + ids
                pieces = [self.sp.id_to_piece(bos)] + pieces
        if add_eos:
            eos = self.sp.eos_id()
            if eos >= 0:
                ids = ids + [eos]
                pieces = pieces + [self.sp.id_to_piece(eos)]
        return EncodeResult(tokens=pieces, ids=ids)

    @property
    def vocab_size(self) -> int:
        return int(self.sp.get_piece_size())

    def id_to_piece(self, i: int) -> str:
        return self.sp.id_to_piece(i)

    def piece_to_id(self, p: str) -> int:
        return int(self.sp.piece_to_id(p))


def load_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def iter_eval_units(
    split_root: Path,
    split: str,
    sources: Sequence[str] = ("bible", "wikipedia"),
) -> list[dict[str, Any]]:
    """Load evaluation lines with source labels."""
    units: list[dict[str, Any]] = []
    for sid in sources:
        p = split_root / split / f"{sid}.txt"
        if not p.is_file():
            continue
        for i, line in enumerate(load_lines(p)):
            units.append(
                {
                    "split": split,
                    "source_id": sid,
                    "line_index": i,
                    "text": line,
                    "n_chars": len(line),
                    "n_bytes": len(line.encode("utf-8")),
                    "n_words": count_words(line),
                }
            )
    return units


def english_looking_fraction(tokens: Sequence[str]) -> float:
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if looks_english_heavy(t)) / len(tokens)


def evaluate_tokenizer_on_units(
    encode_fn,
    units: Sequence[dict[str, Any]],
    *,
    tokenizer_id: str,
    vocab_size: int,
    unk_id: int | None,
    piece_fn=None,
) -> dict[str, Any]:
    """Compute coverage, fertility, sequence stats for a list of line units."""
    total_tokens = 0
    total_words = 0
    total_chars = 0
    total_bytes = 0
    unk_tokens = 0
    lines_with_unk = 0
    seq_lens: list[float] = []
    fertilities: list[float] = []
    token_freq: Counter[str] = Counter()
    token_lens: list[int] = []
    by_source: dict[str, dict[str, Any]] = {}

    source_acc: dict[str, dict[str, float]] = {}

    for u in units:
        text = u["text"]
        res = encode_fn(text)
        toks = res.tokens
        ids = res.ids
        n_tok = len(ids)
        n_words = max(int(u["n_words"]), 0)
        n_chars = int(u["n_chars"])
        n_bytes = int(u["n_bytes"])
        n_unk = sum(1 for i in ids if unk_id is not None and i == unk_id)
        if n_unk:
            lines_with_unk += 1
        unk_tokens += n_unk
        total_tokens += n_tok
        total_words += n_words
        total_chars += n_chars
        total_bytes += n_bytes
        seq_lens.append(float(n_tok))
        if n_words > 0:
            fertilities.append(n_tok / n_words)
        for t in toks:
            token_freq[t] += 1
            # strip SP underscore for length of surface-ish content
            surface = t[1:] if t.startswith("▁") else t
            if t not in SPECIAL_ORDER:
                token_lens.append(len(surface) if surface else len(t))

        sid = u["source_id"]
        acc = source_acc.setdefault(
            sid,
            {
                "tokens": 0.0,
                "words": 0.0,
                "chars": 0.0,
                "bytes": 0.0,
                "unk": 0.0,
                "lines": 0.0,
            },
        )
        acc["tokens"] += n_tok
        acc["words"] += n_words
        acc["chars"] += n_chars
        acc["bytes"] += n_bytes
        acc["unk"] += n_unk
        acc["lines"] += 1

    n_lines = len(units) or 1
    observed_vocab = len(token_freq)
    unused = max(vocab_size - observed_vocab, 0)

    # token type analysis on observed pieces
    single_char = 0
    multi_char = 0
    with_punct = 0
    with_digit = 0
    with_what = 0
    eng_like = 0
    for t, _c in token_freq.items():
        surface = t[1:] if t.startswith("▁") else t
        if t in SPECIAL_ORDER:
            continue
        if len(surface) <= 1:
            single_char += 1
        else:
            multi_char += 1
        if any(unicodedata.category(ch).startswith("P") for ch in surface):
            with_punct += 1
        if any(ch.isdigit() for ch in surface):
            with_digit += 1
        if "ŵ" in surface or "Ŵ" in surface:
            with_what += 1
        if looks_english_heavy(t):
            eng_like += 1

    rare = sum(1 for _t, c in token_freq.items() if c == 1)
    top_tokens = token_freq.most_common(40)
    longest = sorted(token_freq.keys(), key=lambda t: len(t), reverse=True)[:20]

    for sid, acc in source_acc.items():
        w = acc["words"] or 1.0
        by_source[sid] = {
            "n_lines": int(acc["lines"]),
            "total_tokens": int(acc["tokens"]),
            "total_words": int(acc["words"]),
            "total_characters": int(acc["chars"]),
            "total_bytes": int(acc["bytes"]),
            "unk_tokens": int(acc["unk"]),
            "unk_rate": acc["unk"] / acc["tokens"] if acc["tokens"] else 0.0,
            "fertility": acc["tokens"] / w if acc["words"] else None,
            "tokens_per_character": acc["tokens"] / acc["chars"] if acc["chars"] else None,
            "characters_per_token": acc["chars"] / acc["tokens"] if acc["tokens"] else None,
        }

    fert_pct = percentiles(fertilities, [50, 90, 95, 99])
    seq_pct = percentiles(seq_lens, [50, 90, 95, 99])

    return {
        "tokenizer_id": tokenizer_id,
        "vocab_size": vocab_size,
        "n_lines": len(units),
        "coverage": {
            "unknown_token_count": unk_tokens,
            "unknown_token_rate": unk_tokens / total_tokens if total_tokens else 0.0,
            "lines_with_unknown": lines_with_unk,
            "pct_lines_with_unknown": lines_with_unk / n_lines,
            "character_coverage_note": (
                "Character coverage of the tokenizer alphabet is 1.0 for char models on train; "
                "for SentencePiece, character_coverage training param is recorded in config."
            ),
        },
        "sequence_efficiency": {
            "total_encoded_tokens": total_tokens,
            "tokens_per_line": total_tokens / n_lines,
            "tokens_per_word": total_tokens / total_words if total_words else None,
            "characters_per_token": total_chars / total_tokens if total_tokens else None,
            "bytes_per_token": total_bytes / total_tokens if total_tokens else None,
            "tokens_per_character": total_tokens / total_chars if total_chars else None,
            "tokens_per_byte": total_tokens / total_bytes if total_bytes else None,
            "avg_sequence_length_expansion_vs_words": (
                total_tokens / total_words if total_words else None
            ),
            "sequence_length_percentiles": seq_pct,
        },
        "fertility": {
            "definition": "subword_or_char_tokens / whitespace_delimited_words",
            "overall": total_tokens / total_words if total_words else None,
            "percentiles": fert_pct,
            "note": (
                "Character tokenizer fertility is tokens-per-word at character granularity "
                "and is not directly comparable to subword fertility for 'winner' selection."
            ),
        },
        "vocabulary_usage": {
            "total_vocabulary_size": vocab_size,
            "tokens_observed": observed_vocab,
            "unused_vocabulary_entries": unused,
            "utilization": observed_vocab / vocab_size if vocab_size else None,
            "rare_token_pct_observed": rare / observed_vocab if observed_vocab else None,
            "pct_single_character_types": single_char / max(single_char + multi_char, 1),
            "pct_multi_character_types": multi_char / max(single_char + multi_char, 1),
            "average_token_length_chars": (
                sum(token_lens) / len(token_lens) if token_lens else None
            ),
            "longest_tokens": longest,
            "types_with_punctuation": with_punct,
            "types_with_digits": with_digit,
            "types_with_w_hat": with_what,
            "types_english_looking_diagnostic": eng_like,
            "top_tokens": [{"token": t, "count": c} for t, c in top_tokens],
        },
        "totals": {
            "words": total_words,
            "characters": total_chars,
            "bytes": total_bytes,
        },
        "by_source": by_source,
    }


def selection_score(val_metrics: dict[str, Any], *, is_character: bool = False) -> dict[str, Any]:
    """Multi-criteria score for subword models on validation only."""
    if is_character:
        return {"score": None, "eligible": False, "reason": "character not in BPE/Unigram selection"}
    fert = val_metrics.get("fertility", {}).get("overall")
    unk = val_metrics.get("coverage", {}).get("unknown_token_rate")
    util = val_metrics.get("vocabulary_usage", {}).get("utilization")
    p95 = (
        val_metrics.get("sequence_efficiency", {})
        .get("sequence_length_percentiles", {})
        .get("p95")
    )
    avg_tok_len = val_metrics.get("vocabulary_usage", {}).get("average_token_length_chars")
    # Lower fertility better, lower unk better, higher util better (capped), moderate p95
    score = 0.0
    details = {}
    if fert is not None:
        # typical subword fert 1.2–3.5; map lower better
        s_fert = max(0.0, 5.0 - fert)
        score += 2.0 * s_fert
        details["fertility_component"] = s_fert
    if unk is not None:
        s_unk = max(0.0, 1.0 - min(unk * 100, 1.0))
        score += 3.0 * s_unk
        details["unk_component"] = s_unk
    if util is not None:
        # prefer util in 0.4–0.95; penalize very low
        s_util = min(util, 1.0) if util >= 0.2 else util * 0.5
        score += 1.5 * s_util
        details["util_component"] = s_util
    if p95 is not None:
        # mild preference for shorter p95
        s_p95 = max(0.0, 2.0 - (p95 / 200.0))
        score += 1.0 * s_p95
        details["p95_component"] = s_p95
    if avg_tok_len is not None:
        # discourage extreme whole-word memorization (very long avg pieces)
        s_len = 1.0 if avg_tok_len < 8 else max(0.0, 2.0 - avg_tok_len / 8.0)
        score += 0.5 * s_len
        details["token_len_component"] = s_len
    # smaller vocab mild bonus among near ties
    vs = val_metrics.get("vocab_size") or 0
    details["vocab_size"] = vs
    score += max(0.0, (9000 - vs) / 9000.0) * 0.25
    return {"score": score, "eligible": True, "details": details}
