"""Leakage guards for StatBound-Unigram V1 boundary learning."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


class LeakageError(RuntimeError):
    """Raised when a forbidden path or resource is used for V1 learning."""


DEFAULT_FORBIDDEN = (
    "/validation/",
    "/test/",
    "/locked/",
    "morphology_benchmark",
    "annotator_a",
    "annotator_b",
    "self_review",
    "ai_annotator",
)


def normalize_path(path: Path | str) -> str:
    return str(Path(path).resolve()).replace("\\", "/")


def assert_train_only_path(
    path: Path | str,
    *,
    forbidden_substrings: Iterable[str] | None = None,
    require_train_substring: bool = True,
) -> Path:
    """Ensure path is allowed for boundary-stat learning (TRAIN corpus only)."""
    p = Path(path).resolve()
    s = normalize_path(p)
    forbidden = tuple(forbidden_substrings) if forbidden_substrings is not None else DEFAULT_FORBIDDEN
    for bad in forbidden:
        if bad.replace("\\", "/") in s:
            raise LeakageError(
                f"refusing path for StatBound-Unigram boundary learning (leakage): "
                f"matched forbidden substring {bad!r} in {s}"
            )
    if require_train_substring and "/train/" not in s:
        raise LeakageError(
            f"refusing path for StatBound-Unigram boundary learning: "
            f"must contain '/train/' (got {s})"
        )
    if not p.is_file():
        raise FileNotFoundError(f"train corpus not found: {p}")
    return p


def assert_not_forbidden_path(
    path: Path | str,
    *,
    forbidden_substrings: Iterable[str] | None = None,
) -> Path:
    """Block holdout/test/morph annotation paths for any learning entrypoint."""
    p = Path(path).resolve()
    s = normalize_path(p)
    forbidden = tuple(forbidden_substrings) if forbidden_substrings is not None else DEFAULT_FORBIDDEN
    for bad in forbidden:
        if bad.replace("\\", "/") in s:
            raise LeakageError(f"forbidden path: {s} (matched {bad!r})")
    return p
