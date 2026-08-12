"""StatBound-Unigram V1 tokenizer: encode/decode + inspection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .boundary_stats import (
    BoundaryDiscoveryConfig,
    learn_boundary_stats,
    load_boundary_stats,
    save_boundary_stats,
)
from .leakage import assert_train_only_path
from .reranker import RankedCandidate, rank_candidates, select_segmentation, surface_from_pieces
from .unigram_adapter import UnigramAdapter


def load_config(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass
class StatBoundUnigramTokenizer:
    adapter: UnigramAdapter
    stats: dict[str, Any]
    lambda_bias: float
    nbest_size: int
    config: dict[str, Any] | None = None

    @classmethod
    def from_config(
        cls,
        config_path: Path | str,
        *,
        stats_path: Path | str | None = None,
        lambda_bias: float | None = None,
        repo_root: Path | str | None = None,
    ) -> "StatBoundUnigramTokenizer":
        root = Path(repo_root) if repo_root else Path.cwd()
        cfg = load_config(config_path)
        model = root / cfg["base_unigram"]["model_file"]
        adapter = UnigramAdapter(model)
        spath = stats_path or (root / cfg["outputs"]["boundary_stats_default"])
        stats = load_boundary_stats(spath)
        lam = float(cfg["reranking"]["lambda"] if lambda_bias is None else lambda_bias)
        nbest = int(cfg["reranking"]["nbest_size"])
        return cls(
            adapter=adapter,
            stats=stats,
            lambda_bias=lam,
            nbest_size=nbest,
            config=cfg,
        )

    @classmethod
    def learn_stats_from_config(
        cls,
        config_path: Path | str,
        *,
        repo_root: Path | str | None = None,
        train_path: Path | str | None = None,
        out_path: Path | str | None = None,
    ) -> dict[str, Any]:
        root = Path(repo_root) if repo_root else Path.cwd()
        cfg = load_config(config_path)
        forbidden = cfg.get("leakage_guard", {}).get("forbid_path_substrings")
        tpath = Path(train_path) if train_path else root / cfg["corpus"]["train_text"]
        assert_train_only_path(tpath, forbidden_substrings=forbidden)
        bcfg = BoundaryDiscoveryConfig.from_dict(cfg["boundary_discovery"])
        obj = learn_boundary_stats(tpath, bcfg, forbidden_substrings=forbidden)
        opath = Path(out_path) if out_path else root / cfg["outputs"]["boundary_stats_default"]
        save_boundary_stats(obj, opath)
        obj["written_to"] = str(opath)
        return obj

    def encode_word(self, word: str) -> list[str]:
        if word == "":
            return []
        # non-letter short tokens: fall back to base SP for consistency
        chosen = select_segmentation(
            word,
            self.adapter,
            self.stats,
            lambda_bias=self.lambda_bias,
            nbest_size=self.nbest_size,
        )
        return list(chosen.pieces)

    def encode_text(self, text: str) -> list[str]:
        words = text.split()
        pieces: list[str] = []
        for w in words:
            pieces.extend(self.encode_word(w))
        return pieces

    def decode_pieces(self, pieces: list[str]) -> str:
        return self.adapter.decode_pieces(pieces)

    def reconstruct_words(self, text: str) -> list[str]:
        """Return surface forms of each whitespace word after encode (must match)."""
        words = text.split()
        out = []
        for w in words:
            pieces = self.encode_word(w)
            out.append(surface_from_pieces(pieces))
        return out

    def inspect_word(self, word: str) -> dict[str, Any]:
        cands = self.adapter.default_and_nbest(word, self.nbest_size)
        ranked = rank_candidates(
            word, cands, self.stats, lambda_bias=self.lambda_bias
        )
        selected = ranked[0] if ranked else None
        return {
            "word": word,
            "lambda": self.lambda_bias,
            "nbest_size": self.nbest_size,
            "default_unigram_pieces": self.adapter.encode_as_pieces(word),
            "selected": None
            if selected is None
            else {
                "pieces": selected.pieces,
                "unigram_score": selected.unigram_score,
                "boundary_compatibility": selected.boundary_compatibility,
                "combined_score": selected.combined_score,
            },
            "candidates": [
                {
                    "pieces": r.pieces,
                    "unigram_score": r.unigram_score,
                    "boundary_compatibility": r.boundary_compatibility,
                    "combined_score": r.combined_score,
                }
                for r in ranked
            ],
        }

    def vocab_accounting(self) -> dict[str, Any]:
        acc = self.adapter.vocab_accounting()
        acc["boundary_stats_not_in_vocab"] = True
        acc["lambda"] = self.lambda_bias
        return acc

    def base_unigram_pieces(self, word: str) -> list[str]:
        return self.adapter.encode_as_pieces(word)
