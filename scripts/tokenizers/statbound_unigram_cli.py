#!/usr/bin/env python3
"""CLI for StatBound-Unigram V1 (learn stats / encode / decode / inspect).

Does not run scientific morphology or LM evaluation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.tokenizers.statbound.tokenizer import StatBoundUnigramTokenizer  # noqa: E402
from src.tokenizers.statbound.leakage import LeakageError  # noqa: E402


def cmd_learn(args: argparse.Namespace) -> int:
    obj = StatBoundUnigramTokenizer.learn_stats_from_config(
        args.config,
        repo_root=args.repo_root,
        train_path=args.train,
        out_path=args.out,
    )
    print(
        json.dumps(
            {
                "written_to": obj.get("written_to"),
                "n_types": obj["n_types"],
                "n_tokens": obj["n_tokens"],
                "formula_id": obj["formula_id"],
            },
            indent=2,
        )
    )
    return 0


def _load_tok(args: argparse.Namespace) -> StatBoundUnigramTokenizer:
    return StatBoundUnigramTokenizer.from_config(
        args.config,
        stats_path=args.stats,
        lambda_bias=args.lambda_bias,
        repo_root=args.repo_root,
    )


def cmd_encode(args: argparse.Namespace) -> int:
    tok = _load_tok(args)
    if args.text is not None:
        text = args.text
    else:
        text = Path(args.input).read_text(encoding="utf-8")
    pieces = tok.encode_text(text)
    if args.ids:
        # map pieces via adapter
        ids = [tok.adapter.sp.piece_to_id(p) for p in pieces]
        print(json.dumps({"pieces": pieces, "ids": ids}, ensure_ascii=False))
    else:
        print(" ".join(pieces))
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    tok = _load_tok(args)
    pieces = args.pieces.split() if args.pieces else Path(args.input).read_text(encoding="utf-8").split()
    print(tok.decode_pieces(pieces))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    tok = _load_tok(args)
    info = tok.inspect_word(args.word)
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def cmd_vocab(args: argparse.Namespace) -> int:
    tok = _load_tok(args)
    print(json.dumps(tok.vocab_accounting(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="StatBound-Unigram V1 CLI")
    p.add_argument("--repo-root", type=Path, default=_REPO)
    p.add_argument(
        "--config",
        type=Path,
        default=_REPO / "configs/tokenizers/statbound_unigram_v1.json",
    )
    p.add_argument("--stats", type=Path, default=None)
    p.add_argument("--lambda", dest="lambda_bias", type=float, default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("learn-stats", help="Learn boundary stats from TRAIN only")
    pl.add_argument("--train", type=Path, default=None)
    pl.add_argument("--out", type=Path, default=None)
    pl.set_defaults(func=cmd_learn)

    pe = sub.add_parser("encode", help="Encode text")
    pe.add_argument("--text", type=str, default=None)
    pe.add_argument("--input", type=Path, default=None)
    pe.add_argument("--ids", action="store_true")
    pe.set_defaults(func=cmd_encode)

    pd = sub.add_parser("decode", help="Decode pieces")
    pd.add_argument("--pieces", type=str, default=None)
    pd.add_argument("--input", type=Path, default=None)
    pd.set_defaults(func=cmd_decode)

    pi = sub.add_parser("inspect", help="Inspect candidates for one word")
    pi.add_argument("--word", type=str, required=True)
    pi.set_defaults(func=cmd_inspect)

    pv = sub.add_parser("vocab", help="Vocabulary accounting")
    pv.set_defaults(func=cmd_vocab)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except LeakageError as e:
        print(f"LEAKAGE GUARD: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
