"""SentencePiece Unigram adapter for StatBound-Unigram V1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SegmentCandidate:
    pieces: list[str]
    unigram_score: float


class UnigramAdapter:
    """Thin wrapper around a frozen SentencePiece Unigram model."""

    def __init__(self, model_file: Path | str) -> None:
        try:
            import sentencepiece as spm  # type: ignore
        except ImportError as e:
            raise ImportError(
                "sentencepiece is required for StatBound-Unigram. "
                "Install with: .venv/bin/pip install sentencepiece==0.2.0"
            ) from e
        self._spm = spm
        self.model_file = Path(model_file)
        if not self.model_file.is_file():
            raise FileNotFoundError(f"Unigram model not found: {self.model_file}")
        self.sp = spm.SentencePieceProcessor(model_file=str(self.model_file))

    @property
    def vocab_size(self) -> int:
        return int(self.sp.vocab_size())

    def encode_as_pieces(self, text: str) -> list[str]:
        return list(self.sp.encode_as_pieces(text))

    def decode_pieces(self, pieces: list[str]) -> str:
        return self.sp.decode_pieces(pieces)

    def piece_score(self, piece: str) -> float:
        pid = self.sp.piece_to_id(piece)
        return float(self.sp.get_score(pid))

    def unigram_score(self, pieces: list[str]) -> float:
        return float(sum(self.piece_score(p) for p in pieces))

    def nbest_pieces(self, word: str, nbest_size: int) -> list[list[str]]:
        n = max(1, int(nbest_size))
        cands = self.sp.nbest_encode_as_pieces(word, n)
        return [list(c) for c in cands]

    def default_and_nbest(self, word: str, nbest_size: int) -> list[SegmentCandidate]:
        """Return unique candidates including the default SP segmentation."""
        default = self.encode_as_pieces(word)
        raw = self.nbest_pieces(word, nbest_size)
        # ensure default first consideration
        ordered: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()
        for seq in [default] + raw:
            key = tuple(seq)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(seq)
        out: list[SegmentCandidate] = []
        for seq in ordered:
            out.append(SegmentCandidate(pieces=seq, unigram_score=self.unigram_score(seq)))
        return out

    def vocab_accounting(self) -> dict[str, Any]:
        return {
            "model_file": str(self.model_file),
            "vocab_size": self.vocab_size,
            "extra_statbound_pieces": 0,
            "total_effective_vocabulary": self.vocab_size,
        }
