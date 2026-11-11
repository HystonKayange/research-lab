#!/usr/bin/env python3
"""Check presentation consistency against frozen reports; no evaluation runs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "data/reports/publication_snapshot_v0_2.json"
PAPER = ROOT / "docs/research/papers/unigram_undersegments_chichewa_v0_2.md"
MANIFEST = ROOT / "data/reports/publication_release_manifest_v0_2.json"
DOCUMENTS = [
    "README.md", "DATA_AND_LICENSES.md", "docs/research/PUBLIC_REPRODUCIBILITY_v0_2.md",
    "docs/research/PUBLICATION_REVIEW_v0_2.md", str(PAPER.relative_to(ROOT)),
]
ARTIFACTS = DOCUMENTS + [
    "CITATION.cff", "LICENSE", "requirements-publication.txt", ".gitattributes",
    "docs/research/papers/references_v0_2.bib",
    "docs/research/papers/unigram_undersegments_chichewa_v0_2.pdf",
    "data/reports/publication_snapshot_v0_2.json",
    "scripts/publication/build_publication_snapshot.py",
    "scripts/publication/build_paper_pdf.py",
    "scripts/publication/check_publication_release.py",
    "tests/test_publication_snapshot.py",
    ".github/workflows/repository-security.yml",
] + [f"data/reports/figures/paper_v0_2/{name}.{ext}" for name in [
    "f1_candidate_availability", "f2_oracle_changes", "f3_primary_lm",
] for ext in ["png", "svg"]]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_links() -> list[str]:
    tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0"))
    issues = []
    for name in DOCUMENTS:
        p = ROOT / name
        for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", p.read_text()):
            target = match.group(1).split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (p.parent / target).resolve()
            try:
                relative = resolved.relative_to(ROOT).as_posix()
            except ValueError:
                issues.append(f"{name}: link escapes repository")
                continue
            if not resolved.exists():
                issues.append(f"{name}: missing target {relative}")
            elif relative not in tracked and not any(x.startswith(relative.rstrip("/") + "/") for x in tracked):
                issues.append(f"{name}: target is not in public index: {relative}")
    return issues


def verify() -> dict:
    snapshot = json.loads(SNAPSHOT.read_text())
    for name, path in snapshot["input_files"].items():
        assert sha(ROOT / path) == snapshot["input_sha256"][name], f"Frozen input changed: {path}"
    assert snapshot["original_inputs_unchanged"]
    paper = PAPER.read_text()
    table = {}
    for line in paper.splitlines():
        if line.startswith("|"):
            cells = [s.strip() for s in line.strip("|").split("|")]
            if cells:
                table[cells[0]] = cells[1:]
    for label, name in [("BPE-8000", "bpe_8000"), ("Unigram-8000", "unigram_8000"), ("StatBound λ=0.25", "statbound_lambda_0_25")]:
        agg = snapshot["morphology"][name]["aggregate"]
        tpc = snapshot["efficiency"][name]["sequence_efficiency"]["tokens_per_character"]
        expected = [f"{agg[k]:.4f}" for k in ["boundary_precision", "boundary_recall", "boundary_f1", "exact_match_rate"]] + [f"{tpc:.4f}"]
        assert table[label] == expected, f"Table 1 mismatch: {label}"
    primary = snapshot["lm_conditions"]["parameter_matched_x_fixed_characters"]
    for row in primary["statbound"]["per_seed"]:
        values = table[str(row["seed"])]
        assert values[:2] == [f"{row['unigram_validation_bpc']:.6f}", f"{row['statbound_validation_bpc']:.6f}"]
        assert values[2].replace("−", "-") == f"{row['delta_bpc_statbound_minus_unigram']:+.6f}"
    for label, z in [("Left edge: offset ≤4", "left_edge"), ("Right edge: ≤2 characters remain", "right_edge"), ("Internal", "internal")]:
        misses = snapshot["candidate_descriptives"]["misses"]
        assert table[label] == [str(misses[k][z]) for k in ["unigram", "selected_oracle", "absent_from_union"]]
    assert snapshot["input_sha256"]["gold"] in paper
    pdf = PAPER.with_suffix(".pdf").read_bytes()
    assert pdf.startswith(b"%PDF-")
    pages = len(re.findall(rb"/Type\s*/Page\b", pdf))
    assert 6 <= pages <= 8, f"Expected 6–8 pages; got {pages}"
    assert len(re.findall(r"^@", (ROOT / "docs/research/papers/references_v0_2.bib").read_text(), re.M)) == 13
    issues = check_links()
    assert not issues, "\n".join(issues)
    return {
        "schema_version": "publication_release_manifest_v0_2",
        "prepared_on": "2026-11-10",
        "presentation_checks_passed": True,
        "formal_release_ready": False,
        "paper_status": "working_draft_requires_author_review",
        "paper_pages": pages,
        "code_license": "MIT",
        "code_license_scope": "original_software_code_only; see LICENSE",
        "remaining_owner_decisions": ["annotation_license_and_redistribution_permission", "author_approval_and_venue_specific_disclosures"],
        "frozen_input_sha256": snapshot["input_sha256"],
        "artifact_sha256": {p: sha(ROOT / p) for p in ARTIFACTS},
        "environment": {"python": platform.python_version(), "dependencies": {p: importlib.metadata.version(p) for p in ["matplotlib", "numpy", "Pillow", "reportlab"]}},
        "font_sha256": {p: sha(Path("/usr/share/fonts/truetype/dejavu") / p) for p in ["DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSansMono.ttf"]},
        "local_publication_links_valid": True,
        "table_values_match_frozen_sources": True,
        "historical_metrics_recomputed": False,
        "scoring_rules_changed": False,
        "tokenizer_changed": False,
        "lambda_selection_changed": False,
        "holdout_accessed": False,
        "lm_test_accessed": False,
        "scientific_evaluation_run": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    result = verify()
    if args.write_manifest:
        MANIFEST.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    else:
        existing = json.loads(MANIFEST.read_text())
        assert existing["frozen_input_sha256"] == result["frozen_input_sha256"]
        assert existing["artifact_sha256"] == result["artifact_sha256"], "Artifact hashes differ: rebuild and review before updating the manifest"
        for key in ("code_license", "code_license_scope", "remaining_owner_decisions"):
            assert existing[key] == result[key], f"Publication manifest status differs: {key}"
    print(json.dumps({k: result[k] for k in ["presentation_checks_passed", "paper_pages", "formal_release_ready", "code_license", "table_values_match_frozen_sources", "scientific_evaluation_run"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
