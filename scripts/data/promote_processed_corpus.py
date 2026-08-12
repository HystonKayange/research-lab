#!/usr/bin/env python3
"""Promote interim cleaning outputs to a versioned processed corpus.

License-gated and eligibility-gated. Refuses automatic approval for training.
Does not modify data/raw/, Cleaning Policy v2, human labels, or holdout pools.

Requires Python 3.11+. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from audit_sources import load_json, utc_now_iso  # noqa: E402
from build_inventory import sha256_file  # noqa: E402

TOOL_NAME = "promote_processed_corpus"
TOOL_VERSION = "0.1.0"

ALLOWED_STATUS = frozenset(
    {
        "pending",
        "verified",
        "rejected",
        "not_applicable_as_independent_source",
    }
)
CORPUS_CARD_SECTIONS = [
    "Corpus name and version",
    "Purpose",
    "Languages and orthographic observations",
    "Included sources",
    "Excluded sources",
    "Provenance",
    "Licenses and permissions",
    "Cleaning methodology",
    "Human-review methodology",
    "Development and blind-holdout metrics",
    "Known biases",
    "Religious-domain concentration",
    "Wikipedia-domain concentration",
    "Orthographic difference, including Bible ŵ observation",
    "Deduplication policy",
    "Intended uses",
    "Prohibited or unsupported uses",
    "Redistribution status",
    "Reproducibility instructions",
    "Limitations",
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def load_eligibility(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if "sources" not in data or not isinstance(data["sources"], list):
        raise ValueError("eligibility file must contain a sources array")
    return data


def eligibility_by_id(eligibility: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for src in eligibility["sources"]:
        sid = src.get("source_id")
        if not sid:
            raise ValueError("eligibility source missing source_id")
        out[str(sid)] = src
    return out


def validate_eligibility_record(src: dict[str, Any]) -> list[str]:
    """Return structural validation errors (not gate failures)."""
    errs: list[str] = []
    sid = src.get("source_id", "<unknown>")
    for key in ("provenance_status", "license_status"):
        val = src.get(key)
        if val not in ALLOWED_STATUS:
            errs.append(
                f"{sid}.{key} must be one of {sorted(ALLOWED_STATUS)}, got {val!r}"
            )
    for key in (
        "allowed_for_training",
        "allowed_for_redistribution",
        "attribution_required",
        "include_in_processed_corpus",
        "share_alike_required",
        "modification_notice_required",
    ):
        if key not in src:
            continue
        val = src.get(key)
        if val not in (True, False, None):
            errs.append(f"{sid}.{key} must be true, false, or null, got {val!r}")
    return errs


@dataclass
class GateResult:
    source_id: str
    eligible: bool
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def evaluate_source_gates(
    *,
    source_id: str,
    elig: dict[str, Any],
    source_cfg: dict[str, Any],
    config: dict[str, Any],
    inventory_by_id: dict[str, dict[str, Any]],
    repo_root: Path,
    candidate_for_inclusion: bool,
) -> GateResult:
    """Evaluate all promotion gates for one source.

    candidate_for_inclusion: whether we intend to include this source in the corpus.
    For sources marked include=false/null that are not candidates, we still report
    exclusion reasons without requiring training=true.
    """
    gates = config.get("gates", {})
    reasons: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {
        "provenance_status": elig.get("provenance_status"),
        "license_status": elig.get("license_status"),
        "allowed_for_training": elig.get("allowed_for_training"),
        "allowed_for_redistribution": elig.get("allowed_for_redistribution"),
        "include_in_processed_corpus": elig.get("include_in_processed_corpus"),
        "technical_status": elig.get("technical_status"),
        "redundant": bool(elig.get("redundant")),
        "excluded": bool(elig.get("excluded")),
        "holdout_only": bool(elig.get("holdout_only")),
    }

    if elig.get("redundant") and gates.get("block_redundant", True):
        reasons.append("source marked redundant")
    if elig.get("excluded") and gates.get("block_excluded", True):
        reasons.append("source marked excluded")
    if elig.get("holdout_only") and gates.get("block_holdout_only", True):
        reasons.append("source marked holdout_only")
    if elig.get("technical_status") == "redundant_composite":
        reasons.append("technical_status is redundant_composite")

    if not candidate_for_inclusion:
        # Not a candidate: either explicitly false or null include flag.
        if elig.get("include_in_processed_corpus") is False:
            reasons.append("include_in_processed_corpus is false")
        elif elig.get("include_in_processed_corpus") is None:
            reasons.append("include_in_processed_corpus is null (unresolved)")
        return GateResult(
            source_id=source_id,
            eligible=False,
            blocking_reasons=reasons or ["not selected for inclusion"],
            warnings=warnings,
            details=details,
        )

    # Candidate path: full gate suite
    if gates.get("require_include_in_processed_corpus_true", True):
        if elig.get("include_in_processed_corpus") is not True:
            reasons.append(
                f"include_in_processed_corpus is {elig.get('include_in_processed_corpus')!r}, required true"
            )

    if gates.get("require_provenance_verified", True):
        if elig.get("provenance_status") != "verified":
            reasons.append(
                f"provenance_status is {elig.get('provenance_status')!r}, required verified"
            )

    if gates.get("require_license_verified", True):
        if elig.get("license_status") != "verified":
            reasons.append(
                f"license_status is {elig.get('license_status')!r}, required verified"
            )

    if gates.get("require_allowed_for_training_true", True):
        train = elig.get("allowed_for_training")
        if train is None:
            reasons.append("allowed_for_training is null (unresolved)")
        elif train is False:
            reasons.append("allowed_for_training is false")

    interim_path = source_cfg.get("interim_cleaned_path")
    if gates.get("require_technical_output_exists", True):
        if not interim_path:
            reasons.append("no interim_cleaned_path configured")
        else:
            p = repo_root / interim_path
            details["expected_input"] = str(interim_path)
            if not p.is_file():
                reasons.append(f"technical cleaning output missing: {interim_path}")
            else:
                details["interim_sha256"] = sha256_file(p)
                details["interim_size_bytes"] = p.stat().st_size

    # Cleaning config checksum
    if gates.get("require_cleaning_config_checksum_match", True):
        cfg_path = source_cfg.get("cleaning_config_path")
        expected = source_cfg.get("expected_cleaning_config_sha256")
        if cfg_path and expected:
            cp = repo_root / cfg_path
            if not cp.is_file():
                reasons.append(f"cleaning config missing: {cfg_path}")
            else:
                actual = sha256_file(cp)
                details["cleaning_config_sha256"] = actual
                details["expected_cleaning_config_sha256"] = expected
                if actual != expected:
                    reasons.append(
                        f"cleaning-config checksum mismatch for {cfg_path}: "
                        f"expected {expected}, got {actual}"
                    )
        elif cfg_path:
            warnings.append("no expected_cleaning_config_sha256 in promotion config")

    # Technical cleaned checksum vs interim summary if available
    if gates.get("require_technical_checksum_match", True):
        summary_path = source_cfg.get("interim_summary_path")
        if summary_path and interim_path:
            sp = repo_root / summary_path
            ip = repo_root / interim_path
            if sp.is_file() and ip.is_file():
                try:
                    summary = load_json(sp)
                    src_sum = (summary.get("sources") or {}).get(source_id) or {}
                    expected_clean = src_sum.get("cleaned_sha256")
                    actual_clean = sha256_file(ip)
                    details["summary_cleaned_sha256"] = expected_clean
                    details["actual_cleaned_sha256"] = actual_clean
                    if expected_clean and actual_clean != expected_clean:
                        reasons.append(
                            f"technical cleaning output checksum mismatch for {source_id}: "
                            f"summary {expected_clean}, file {actual_clean}"
                        )
                except (OSError, ValueError, TypeError) as e:
                    reasons.append(f"could not verify technical checksum: {e}")

    # Raw inventory checksum
    if gates.get("require_raw_checksum_match_inventory", True):
        inv = inventory_by_id.get(source_id)
        raw_rel = source_cfg.get("raw_relative_path")
        if inv is None:
            reasons.append(f"source {source_id} missing from inventory")
        elif raw_rel:
            raw_p = repo_root / raw_rel
            details["raw_path"] = raw_rel
            if not raw_p.is_file():
                reasons.append(f"raw file missing: {raw_rel}")
            else:
                actual = sha256_file(raw_p)
                expected = inv.get("sha256")
                details["raw_sha256"] = actual
                details["inventory_sha256"] = expected
                if expected and actual != expected:
                    reasons.append(
                        f"raw checksum mismatch for {source_id}: "
                        f"inventory {expected}, file {actual}"
                    )

    # Redistribution is not a hard block for local training promotion
    redistrib = elig.get("allowed_for_redistribution")
    details["redistribution_permitted"] = redistrib is True
    details["local_training_permitted"] = elig.get("allowed_for_training") is True
    if redistrib is None:
        warnings.append(
            "allowed_for_redistribution is null; local restricted artifact only if promoted"
        )
    elif redistrib is False:
        warnings.append(
            "allowed_for_redistribution is false; exportable corpus directory not used"
        )

    return GateResult(
        source_id=source_id,
        eligible=len(reasons) == 0,
        blocking_reasons=reasons,
        warnings=warnings,
        details=details,
    )


def inventory_index(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for f in inventory.get("files") or []:
        sid = f.get("source_id")
        if sid:
            out[str(sid)] = f
    return out


def plan_promotion(
    *,
    config: dict[str, Any],
    eligibility: dict[str, Any],
    inventory: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    """Build a full dry-run / pre-flight plan without writing corpus files."""
    elig_map = eligibility_by_id(eligibility)
    inv_map = inventory_index(inventory)
    source_cfgs: dict[str, dict[str, Any]] = config.get("sources") or {}

    structural_errors: list[str] = []
    for src in eligibility["sources"]:
        structural_errors.extend(validate_eligibility_record(src))

    # Candidate sources: include_in_processed_corpus is True (explicit human yes)
    # Also evaluate known configured sources that are not True for blocking report.
    candidates: list[str] = []
    blocked: list[dict[str, Any]] = []
    eligible_sources: list[dict[str, Any]] = []
    gate_results: list[GateResult] = []

    # Evaluate all eligibility entries
    for sid, elig in elig_map.items():
        src_cfg = source_cfgs.get(sid) or {
            "source_id": sid,
            "raw_relative_path": None,
            "interim_cleaned_path": None,
        }
        want = elig.get("include_in_processed_corpus") is True
        if want:
            candidates.append(sid)
        gr = evaluate_source_gates(
            source_id=sid,
            elig=elig,
            source_cfg=src_cfg,
            config=config,
            inventory_by_id=inv_map,
            repo_root=repo_root,
            candidate_for_inclusion=want,
        )
        gate_results.append(gr)
        entry = {
            "source_id": sid,
            "eligible": gr.eligible,
            "blocking_reasons": gr.blocking_reasons,
            "warnings": gr.warnings,
            "details": gr.details,
            "expected_input": src_cfg.get("interim_cleaned_path"),
            "output_filename": src_cfg.get("output_filename"),
            "redistribution_permitted": gr.details.get("redistribution_permitted"),
            "local_training_permitted": gr.details.get("local_training_permitted"),
        }
        if gr.eligible and want:
            eligible_sources.append(entry)
        else:
            blocked.append(entry)

    # Any unresolved source that could be included (bible, wikipedia) still pending
    unresolved_fields: list[dict[str, Any]] = []
    for sid in ("bible", "wikipedia"):
        elig = elig_map.get(sid)
        if not elig:
            unresolved_fields.append({"source_id": sid, "field": "<missing>", "value": None})
            continue
        for field_name in (
            "provenance_status",
            "license_status",
            "allowed_for_training",
            "allowed_for_redistribution",
            "attribution_required",
            "include_in_processed_corpus",
            "source_url",
            "license_name",
            "reviewed_by",
            "reviewed_at",
        ):
            val = elig.get(field_name)
            if val is None or val == "pending":
                unresolved_fields.append(
                    {"source_id": sid, "field": field_name, "value": val}
                )

    corpus_name = config.get("corpus_name", "chichewa_corpus")
    corpus_version = config.get("corpus_version", "v0.1")
    out_cfg = config.get("output") or {}
    processed_root = repo_root / out_cfg.get("processed_root", "data/processed")
    dirname = out_cfg.get("corpus_dirname", f"{corpus_name}_{corpus_version}")
    corpus_root = processed_root / dirname

    # Redistribution: all eligible sources must allow redistribution for exportable layout
    any_redistrib_false_or_null = False
    all_redistrib_true = True
    for e in eligible_sources:
        if e.get("redistribution_permitted") is not True:
            any_redistrib_false_or_null = True
            all_redistrib_true = False

    if not eligible_sources:
        # Still report intended layout
        all_redistrib_true = False
        any_redistrib_false_or_null = True

    if all_redistrib_true and eligible_sources:
        text_subdir = out_cfg.get("exportable_subdir", "corpus")
        redistrib_mode = "exportable"
    else:
        text_subdir = out_cfg.get("restricted_subdir", "corpus_restricted_local")
        redistrib_mode = "restricted_local"

    planned_outputs = {
        "corpus_root": str(corpus_root.relative_to(repo_root))
        if corpus_root.is_relative_to(repo_root)
        else str(corpus_root),
        "text_subdir": text_subdir,
        "redistribution_mode": redistrib_mode,
        "files": {
            "readme": "README.md",
            "corpus_card": "reports/CORPUS_CARD.md",
            "cleaning_summary": "reports/cleaning_summary.md",
            "known_limitations": "reports/known_limitations.md",
            "documents": "metadata/documents.jsonl",
            "sources": "metadata/sources.json",
            "checksums": "metadata/checksums.json",
            "build_manifest": "metadata/build_manifest.json",
            "deduplication_log": "metadata/deduplication_log.jsonl",
            "deduplication_report": "reports/deduplication_report.md",
            "eligibility_snapshot": "metadata/eligibility_snapshot.json",
        },
        "source_text_files": [
            {
                "source_id": e["source_id"],
                "path": f"{text_subdir}/{e.get('output_filename') or (e['source_id'] + '.txt')}",
            }
            for e in eligible_sources
        ],
    }

    # Block if structural issues, no eligible sources, or any explicit candidate failed.
    block_reasons: list[str] = []
    if structural_errors:
        block_reasons.append("structural eligibility validation failed")
        block_reasons.extend(structural_errors)

    failed_candidates = [b for b in blocked if b["source_id"] in candidates]

    # Always require at least one eligible included source for successful promotion
    if not eligible_sources:
        block_reasons.append("unresolved source eligibility")
        block_reasons.append("no sources eligible for inclusion")
        # Surface pending default sources when nothing is approved yet
        for sid in ("bible", "wikipedia"):
            elig = elig_map.get(sid) or {}
            if elig.get("include_in_processed_corpus") is True:
                continue
            block_reasons.append(
                f"{sid}: include_in_processed_corpus is "
                f"{elig.get('include_in_processed_corpus')!r}"
            )
            for field_name, required in (
                ("provenance_status", "verified"),
                ("license_status", "verified"),
                ("allowed_for_training", True),
            ):
                val = elig.get(field_name)
                if val != required:
                    block_reasons.append(
                        f"{sid}: {field_name} is {val!r}, need {required!r}"
                    )

    for b in blocked:
        if b["source_id"] in candidates:
            for r in b["blocking_reasons"]:
                block_reasons.append(f"{b['source_id']}: {r}")
    # Dedup planned checksums of inputs for dry-run
    planned_checksums: dict[str, str] = {}
    for e in eligible_sources:
        sid = e["source_id"]
        inp = e.get("expected_input")
        if inp:
            p = repo_root / inp
            if p.is_file():
                planned_checksums[f"input:{sid}"] = sha256_file(p)

    promotion_allowed = len(block_reasons) == 0 and len(eligible_sources) > 0

    return {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc_now_iso(),
        "promotion_allowed": promotion_allowed,
        "status": "ok" if promotion_allowed else "blocked",
        "primary_reason": (
            None if promotion_allowed else "unresolved source eligibility"
            if not eligible_sources
            else block_reasons[0]
        ),
        "blocking_reasons": block_reasons,
        "unresolved_fields": unresolved_fields,
        "eligible_sources": eligible_sources,
        "blocked_sources": blocked,
        "candidates": candidates,
        "planned_outputs": planned_outputs,
        "planned_checksums": planned_checksums,
        "redistribution_mode": redistrib_mode,
        "local_training_permitted": any(
            e.get("local_training_permitted") for e in eligible_sources
        ),
        "redistribution_permitted": all_redistrib_true and bool(eligible_sources),
        "any_redistribution_false_or_null": any_redistrib_false_or_null,
        "git_commit": git_commit(repo_root),
        "config_version": config.get("version"),
        "corpus_name": corpus_name,
        "corpus_version": corpus_version,
        "failed_candidates": failed_candidates,
    }


def exact_dedupe_lines(
    lines: list[str],
    *,
    source_id: str,
    seen_global: dict[str, list[str]] | None,
    cross_source: bool,
    source_priority_rank: dict[str, int],
) -> tuple[list[str], list[dict[str, Any]]]:
    """Exact within-source dedupe; optional cross-source with priority.

    seen_global maps line_hash -> list of source_ids that contributed.
    When cross_source and a higher-priority source already kept the line,
    drop it here but log attribution.
    """
    kept: list[str] = []
    log: list[dict[str, Any]] = []
    seen_local: set[str] = set()

    for idx, line in enumerate(lines):
        # Preserve empty lines? Drop exact empty duplicates only if repeated
        h = sha256_text(line)
        if h in seen_local:
            log.append(
                {
                    "action": "drop_within_source_exact",
                    "source_id": source_id,
                    "line_index": idx,
                    "line_sha256": h,
                }
            )
            continue
        if cross_source and seen_global is not None and h in seen_global:
            prior = seen_global[h]
            # Keep attribution; drop text instance
            if source_id not in prior:
                prior.append(source_id)
            log.append(
                {
                    "action": "drop_cross_source_exact",
                    "source_id": source_id,
                    "line_index": idx,
                    "line_sha256": h,
                    "retained_sources": list(prior),
                }
            )
            continue
        seen_local.add(h)
        if seen_global is not None:
            seen_global.setdefault(h, []).append(source_id)
        kept.append(line)
    return kept, log


def render_corpus_card(
    plan: dict[str, Any],
    config: dict[str, Any],
    eligibility_snapshot: dict[str, Any],
) -> str:
    """Generate CORPUS_CARD.md with required sections; no invented facts."""
    holdout = config.get("holdout_metrics_reference") or {}
    elig_sources = eligibility_snapshot.get("sources") or []
    elig_by = {s.get("source_id"): s for s in elig_sources}
    included = [e["source_id"] for e in plan.get("eligible_sources") or []]
    excluded = [
        s.get("source_id")
        for s in elig_sources
        if s.get("source_id") not in included
    ]
    lines = [
        f"# Corpus card: {plan.get('corpus_name')} {plan.get('corpus_version')}",
        "",
        f"_Generated at {plan.get('generated_at')} by {TOOL_NAME} {TOOL_VERSION}_",
        "",
        "**Legal note:** This card documents licensing and provenance for research "
        "reproducibility. It is **not legal advice**. Downstream users remain "
        "responsible for compliance with CC BY-SA 4.0 and source-specific conditions.",
        "",
        "## 1. Corpus name and version",
        "",
        f"- **Name:** {plan.get('corpus_name')} (display: **Chichewa Corpus v0.1**)",
        f"- **Version:** {plan.get('corpus_version')}",
        "- This brand is distinct from Biblica® trademarks and from Wikipedia branding.",
        "",
        "## 2. Purpose",
        "",
        "Research-grade Chichewa text corpus assembled from approved interim "
        "cleaning outputs after explicit human eligibility decisions. Supports "
        "reproducible packaging with attribution; not a substitute for legal "
        "review of any specific downstream use.",
        "",
        "## 3. Languages and orthographic observations",
        "",
        "- Primary language: Chichewa (Nyanja); codes `ny` / `nya` appear in source records.",
        "- Orthography is not normalized across sources.",
        "- Bible text may retain characters such as `ŵ` that are less frequent "
        "or absent in other sources; this is an observed orthographic difference, "
        "not a cleaning error.",
        "",
        "## 4. Included sources",
        "",
    ]
    if included:
        for sid in included:
            s = elig_by.get(sid) or {}
            lines.append(
                f"- `{sid}` — {s.get('license_identifier') or s.get('license_name')} "
                f"({s.get('license_url')})"
            )
    else:
        lines.append("- _(none — promotion blocked or dry-run without eligibility)_")
    lines.extend(["", "## 5. Excluded sources", ""])
    for sid in excluded:
        lines.append(f"- `{sid}`")
    if "existing_corpus" in excluded or "existing_corpus" not in included:
        lines.append(
            "- `existing_corpus` is excluded as a **redundant composite** of Bible "
            "and Wikipedia (complete line-level containment; no unique residual). "
            "This is a technical exclusion, not a claim that underlying Bible or "
            "Wikipedia content is unlicensed."
        )
    lines.extend(
        [
            "",
            "## 6. Provenance",
            "",
            "Structured records: `data/metadata/source_provenance/` "
            "(copied into this build under `metadata/source_provenance/`).",
            "",
        ]
    )
    for s in elig_sources:
        sid = s.get("source_id")
        lines.append(
            f"- **{sid}:** provenance_status=`{s.get('provenance_status')}`, "
            f"source_url=`{s.get('source_url')}`, "
            f"original_artifact=`{s.get('original_artifact_name')}`, "
            f"snapshot/date fields=`source_snapshot_date={s.get('source_snapshot_date')}` "
            f"`stated_local_download_date={s.get('stated_local_download_date')}`"
        )
        if sid == "wikipedia":
            lines.append(
                "  - Dump URL class: moving `/latest/` "
                f"(`{s.get('original_download_url')}`). "
                f"Immutable dated dump URL: `{s.get('immutable_dated_dump_url')}` "
                "(null if not proven). Original `.bz2` not retained in-repo."
            )
        if sid == "bible":
            lines.append(
                "  - Product page date / stated source date: "
                f"`{s.get('source_snapshot_date')}`. "
                f"Download: `{s.get('original_download_url')}`. "
                "Original zip not retained in-repo."
            )
    lines.extend(
        [
            "",
            "## 7. Licenses and permissions",
            "",
            "### Summary",
            "",
            "- **Both included textual sources are CC BY-SA 4.0.**",
            "- **Attribution is required** for each source (see "
            "`reports/SOURCE_ATTRIBUTION.md` — source-specific, not one generic string).",
            "- **Redistributed processed text** must retain applicable license "
            "obligations: attribution, license notice, modification notice, and "
            "share-alike for adapted text.",
            "- **Modifications were made** during extraction and cleaning; treat "
            "processed outputs as derived/adapted text for notice purposes.",
            "- **Bible-specific Biblica® trademark conditions apply:** unmodified "
            "redistribution may retain the trademark; modified/adapted text must "
            "remove Biblica® unless written permission exists. This corpus is "
            "treated as modified; do not brand the corpus as Biblica®.",
            "- **Chichewa Wikipedia contributors retain their respective copyrights.** "
            "Do not claim the Wikimedia Foundation owns all article copyrights.",
            "- **No endorsement** by Biblica, Inc., Wikimedia Foundation, or Wikipedia "
            "is implied.",
            "- **Model training use** and **text redistribution** are different actions. "
            "Training permission in eligibility gates does not erase text-redistribution "
            "obligations.",
            "- **Model weights:** Whether trained weights are adapted material under "
            "CC BY-SA is an **unresolved legal interpretation**. This project has not "
            "received qualified legal advice on that point. **No claim is made** that "
            "resulting model weights are or are not share-alike-encumbered.",
            "- Downstream users remain responsible for compliance. This is documentation, "
            "not legal advice.",
            "",
            "### Per-source fields",
            "",
        ]
    )
    for s in elig_sources:
        lines.append(
            f"- **{s.get('source_id')}:** license_status=`{s.get('license_status')}`, "
            f"license_name=`{s.get('license_name')}`, "
            f"license_id=`{s.get('license_identifier')}`, "
            f"license_url=`{s.get('license_url')}`, "
            f"copyright_holder=`{s.get('copyright_holder')}`, "
            f"training=`{s.get('allowed_for_training')}`, "
            f"redistribution=`{s.get('allowed_for_redistribution')}`, "
            f"attribution_required=`{s.get('attribution_required')}`, "
            f"share_alike_required=`{s.get('share_alike_required')}`, "
            f"modification_notice_required=`{s.get('modification_notice_required')}`"
        )
    lines.extend(
        [
            "",
            "## 8. Cleaning methodology",
            "",
            "- Bible: light-touch cleaning; local interim cleaned checksum currently "
            "matches raw extracted text under Cleaning Policy v2 path packaging.",
            "- Wikipedia: Cleaning Policy v2 (`configs/data/cleaning_v2.json`) is the "
            "selected technical candidate.",
            "- existing_corpus: not cleaned for independent promotion (redundant composite).",
            "- Cleaning Policy v2 must not be modified based on blind holdout labels.",
            "",
            "## 9. Human-review methodology",
            "",
            "- Development set (~367 labels) used to design Cleaning Policy v2 only.",
            "- Blind holdout with sequential stages; remainder of the 250-pool stays locked "
            "until explicitly released.",
            "- Labels are frozen evaluation evidence; not a substitute for licensing.",
            "- Eligibility reviewed by the human named in `source_eligibility.json`.",
            "",
            "## 10. Development and blind-holdout metrics",
            "",
            "Provisional independent holdout evidence (**do not retune v2 on holdout**):",
            "",
            "**Context required when reading combined metrics:**",
            "",
            "- **Stage 1** was **risk-stratified** (oversampled ambiguous foreign/short/URL/"
            "mixed cases; deprioritized trivial blank/digit/Category chrome).",
            "- **Stage 2** consisted largely of **straightforward removal categories** "
            "(high removal precision; no kept-useful subsample in that chunk).",
            "- Combined Stage 1+2 metrics therefore mix a hard risk slice with easier "
            "removal cases and must not be quoted as a single undifferentiated benchmark.",
            "",
            f"- Stage 1 removal precision: {holdout.get('stage1_removal_precision')}",
            f"- Stage 1 false-removal rate: {holdout.get('stage1_false_removal_rate')}",
            f"- Stage 1 useful-text retention: {holdout.get('stage1_useful_text_retention')}",
            f"- Combined Stage 1+2 (n={holdout.get('combined_stage1_stage2_n_labels')}), "
            "with the context above: "
            f"precision={holdout.get('combined_removal_precision')}, "
            f"FRR={holdout.get('combined_false_removal_rate')}, "
            f"useful retention={holdout.get('combined_useful_text_retention')}",
            f"- Notes: {holdout.get('notes')}",
            "",
            "## 11. Known biases",
            "",
            "- Domain mix is not representative of all Chichewa text.",
            "- Religious text and Wikipedia encyclopedic style dominate when both are included.",
            "- Cleaning heuristics may under- or over-remove borderline mixed-language lines.",
            "",
            "## 12. Religious-domain concentration",
            "",
            "If Bible is included, a large fraction of tokens may be religious narrative "
            "and verse-like structure. Downstream models may overfit religious register.",
            "",
            "## 13. Wikipedia-domain concentration",
            "",
            "If Wikipedia is included, encyclopedic and list-like structures may dominate "
            "non-religious content. Foreign-language and chrome noise are reduced by v2 "
            "but residual risk remains.",
            "",
            "## 14. Orthographic difference, including Bible ŵ observation",
            "",
            "Bible text may use `ŵ` and related orthographic conventions that differ from "
            "Wikipedia or modern informal text. Promotion does not rewrite orthography.",
            "",
            "## 15. Deduplication policy",
            "",
            f"- Within-source exact: {config.get('deduplication', {}).get('within_source_exact')}",
            f"- Cross-source exact: {config.get('deduplication', {}).get('cross_source_exact')}",
            f"- Source priority: {config.get('deduplication', {}).get('source_priority')}",
            "- No MinHash, embedding, or fuzzy near-dedup in v0.1.",
            "- Attribution metadata is preserved even when exact cross-source duplicates "
            "collapse text instances.",
            "",
            "## 16. Intended uses",
            "",
            "- Research experimentation when `allowed_for_training` is explicitly true "
            "and the user accepts CC BY-SA text obligations for any redistribution of text.",
            "- Reproducible packaging of cleaned text with provenance and attribution.",
            "",
            "## 17. Prohibited or unsupported uses",
            "",
            "- Redistributing processed text without attribution, license notice, "
            "modification notice, or share-alike compliance.",
            "- Branding the corpus with Biblica® or implying Wikimedia/Biblica endorsement.",
            "- Silent inclusion of `existing_corpus` as an independent source.",
            "- Claiming that model weights are free of (or subject to) CC BY-SA without "
            "qualified legal advice.",
            "- Claiming language ID or perfect noise removal.",
            "",
            "## 18. Redistribution status",
            "",
            f"- Mode for this build: `{plan.get('redistribution_mode')}`",
            f"- Redistribution permitted (all included sources): `{plan.get('redistribution_permitted')}`",
            "- When exportable: text may be shared under CC BY-SA 4.0 with the notices in "
            "`reports/SOURCE_ATTRIBUTION.md`.",
            "",
            "## 19. Reproducibility instructions",
            "",
            "1. Acquire sources **manually** using `configs/data/source_acquisition_manifest.json` "
            "(no auto-download in this pipeline).",
            "2. Prefer dated Wikimedia dump URLs over `/latest/`; record dump SHA-256 at acquisition.",
            "3. Freeze raw inventory checksums (`data/metadata/inventory.json`).",
            "4. Run validated cleaning (Bible path + Cleaning Policy v2 for Wikipedia).",
            "5. Confirm eligibility in `data/metadata/source_eligibility.json`.",
            "6. Dry-run then promote with `scripts/data/promote_processed_corpus.py`.",
            f"- Git commit recorded at build time: `{plan.get('git_commit')}`",
            "",
            "## 20. Limitations",
            "",
            "- Original Wikipedia dump `.bz2` and Bible `nya_vpl.zip` are not retained in-repo; "
            "exact dump SHA-256 values are therefore unknown.",
            "- Wikimedia dump date is not independently proven from a retained archive "
            "(stated download date is human-reported).",
            "- Holdout useful-retention confidence intervals can be wide with few useful examples.",
            "- No train/validation/test splits are created by this pipeline.",
            "- Orthography and domain imbalance are not corrected.",
            "- Model-weight licensing under CC BY-SA remains unresolved without legal advice.",
            "",
        ]
    )
    return "\n".join(lines)


def write_atomic_tree(staging: Path, final: Path) -> None:
    """Atomically publish staging directory to final path (same filesystem)."""
    if final.exists():
        raise ValueError(f"Output corpus directory already exists: {final}")
    final.parent.mkdir(parents=True, exist_ok=True)
    # Use replace of a temp sibling for best-effort atomicity
    tmp_final = final.with_name(final.name + ".promoting")
    if tmp_final.exists():
        shutil.rmtree(tmp_final)
    shutil.move(str(staging), str(tmp_final))
    tmp_final.rename(final)


def run_promotion(
    *,
    config: dict[str, Any],
    eligibility: dict[str, Any],
    inventory: dict[str, Any],
    repo_root: Path,
    dry_run: bool,
) -> dict[str, Any]:
    plan = plan_promotion(
        config=config,
        eligibility=eligibility,
        inventory=inventory,
        repo_root=repo_root,
    )
    if dry_run:
        plan["dry_run"] = True
        plan["files_written"] = []
        return plan

    if not plan["promotion_allowed"]:
        plan["dry_run"] = False
        plan["files_written"] = []
        return plan

    out_cfg = config.get("output") or {}
    processed_root = repo_root / out_cfg.get("processed_root", "data/processed")
    dirname = out_cfg.get(
        "corpus_dirname",
        f"{plan['corpus_name']}_{plan['corpus_version']}",
    )
    final_root = processed_root / dirname
    if final_root.exists():
        plan["promotion_allowed"] = False
        plan["status"] = "blocked"
        plan["blocking_reasons"] = list(plan["blocking_reasons"]) + [
            f"output directory already exists: {final_root}"
        ]
        plan["primary_reason"] = "output directory already exists"
        return plan

    text_subdir = plan["planned_outputs"]["text_subdir"]
    dedup_cfg = config.get("deduplication") or {}
    within = bool(dedup_cfg.get("within_source_exact", True))
    cross = bool(dedup_cfg.get("cross_source_exact", False))
    priority = list(
        dedup_cfg.get("source_priority")
        or ["bible", "wikipedia"]
    )
    rank = {s: i for i, s in enumerate(priority)}

    elig_map = eligibility_by_id(eligibility)
    source_cfgs = config.get("sources") or {}

    # Order eligible sources by priority
    eligible_ids = [e["source_id"] for e in plan["eligible_sources"]]
    eligible_ids.sort(key=lambda s: rank.get(s, 999))

    staging_parent = processed_root
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{dirname}_staging_", dir=str(staging_parent))
    )

    try:
        (staging / text_subdir).mkdir(parents=True)
        (staging / "metadata").mkdir()
        (staging / "reports").mkdir()

        documents: list[dict[str, Any]] = []
        dedup_log: list[dict[str, Any]] = []
        checksums: dict[str, str] = {}
        seen_global: dict[str, list[str]] | None = {} if cross else None
        source_outputs: dict[str, Any] = {}

        for sid in eligible_ids:
            scfg = source_cfgs[sid]
            src_path = repo_root / scfg["interim_cleaned_path"]
            raw_text = src_path.read_text(encoding="utf-8")
            lines = raw_text.splitlines(keepends=True)
            # Normalize to lines without forcing extra newline issues
            plain = raw_text.splitlines()
            if within or cross:
                kept, log = exact_dedupe_lines(
                    plain,
                    source_id=sid,
                    seen_global=seen_global,
                    cross_source=cross,
                    source_priority_rank=rank,
                )
                dedup_log.extend(log)
            else:
                kept = plain
            out_name = scfg.get("output_filename") or f"{sid}.txt"
            out_path = staging / text_subdir / out_name
            body = "\n".join(kept)
            if kept and not body.endswith("\n"):
                body += "\n"
            out_path.write_text(body, encoding="utf-8")
            out_sha = sha256_file(out_path)
            checksums[f"corpus/{out_name}"] = out_sha
            checksums[f"input/{sid}"] = sha256_file(src_path)
            elig = elig_map[sid]
            source_outputs[sid] = {
                "source_id": sid,
                "output_path": f"{text_subdir}/{out_name}",
                "n_lines_in": len(plain),
                "n_lines_out": len(kept),
                "sha256": out_sha,
                "input_sha256": checksums[f"input/{sid}"],
                "eligibility": {
                    "provenance_status": elig.get("provenance_status"),
                    "license_status": elig.get("license_status"),
                    "allowed_for_training": elig.get("allowed_for_training"),
                    "allowed_for_redistribution": elig.get("allowed_for_redistribution"),
                    "attribution_required": elig.get("attribution_required"),
                },
            }
            for i, line in enumerate(kept):
                documents.append(
                    {
                        "doc_id": f"{sid}:{i}",
                        "source_id": sid,
                        "line_index": i,
                        "text_sha256": sha256_text(line),
                        "n_chars": len(line),
                    }
                )

        # metadata files
        eligibility_snapshot = eligibility
        (staging / "metadata" / "eligibility_snapshot.json").write_text(
            json.dumps(eligibility_snapshot, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        checksums["metadata/eligibility_snapshot.json"] = sha256_file(
            staging / "metadata" / "eligibility_snapshot.json"
        )

        sources_meta = {
            "corpus_name": plan["corpus_name"],
            "corpus_version": plan["corpus_version"],
            "sources": source_outputs,
            "excluded": [
                s["source_id"]
                for s in eligibility.get("sources") or []
                if s["source_id"] not in eligible_ids
            ],
            "redistribution_mode": plan["redistribution_mode"],
        }
        (staging / "metadata" / "sources.json").write_text(
            json.dumps(sources_meta, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        with (staging / "metadata" / "documents.jsonl").open(
            "w", encoding="utf-8"
        ) as f:
            for doc in documents:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        with (staging / "metadata" / "deduplication_log.jsonl").open(
            "w", encoding="utf-8"
        ) as f:
            for row in dedup_log:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        dedup_report = [
            "# Deduplication report",
            "",
            f"- Within-source exact: {within}",
            f"- Cross-source exact: {cross}",
            f"- Source priority: {priority}",
            f"- Log entries: {len(dedup_log)}",
            "",
        ]
        (staging / "reports" / "deduplication_report.md").write_text(
            "\n".join(dedup_report) + "\n", encoding="utf-8"
        )

        cleaning_summary = [
            "# Cleaning summary",
            "",
            "Inputs were taken from validated interim cleaning outputs.",
            "",
        ]
        for sid in eligible_ids:
            scfg = source_cfgs[sid]
            cleaning_summary.append(
                f"- **{sid}:** `{scfg.get('interim_cleaned_path')}` "
                f"(config `{scfg.get('cleaning_config_path')}`)"
            )
        # Attach holdout validation references if present in repo
        holdout_refs = [
            "data/metadata/cleaning_holdout_stage1_validation.json",
            "data/metadata/cleaning_holdout_stage2_validation.json",
            "data/metadata/cleaning_v2_validation.json",
            "data/reports/cleaning_v2_validation_report.md",
        ]
        cleaning_summary.extend(["", "## Validation artifacts (repository paths)", ""])
        for rel in holdout_refs:
            p = repo_root / rel
            cleaning_summary.append(
                f"- `{'present' if p.is_file() else 'missing'}`: `{rel}`"
            )
        (staging / "reports" / "cleaning_summary.md").write_text(
            "\n".join(cleaning_summary) + "\n", encoding="utf-8"
        )

        limitations = [
            "# Known limitations",
            "",
            "- See CORPUS_CARD.md section 20.",
            "- Eligibility decisions are human; re-verify if sources change.",
            "- No train/val/test split is provided.",
            "- Original dump/archive binaries may be absent; see provenance records.",
            "- Model-weight licensing under CC BY-SA is unresolved legal interpretation.",
            "",
        ]
        (staging / "reports" / "known_limitations.md").write_text(
            "\n".join(limitations) + "\n", encoding="utf-8"
        )

        card = render_corpus_card(plan, config, eligibility)
        (staging / "reports" / "CORPUS_CARD.md").write_text(card, encoding="utf-8")

        # Copy source-specific attribution and provenance into the build
        attr_src = repo_root / "data" / "reports" / "SOURCE_ATTRIBUTION.md"
        if attr_src.is_file():
            shutil.copy2(attr_src, staging / "reports" / "SOURCE_ATTRIBUTION.md")
        prov_dir = repo_root / "data" / "metadata" / "source_provenance"
        if prov_dir.is_dir():
            dest_prov = staging / "metadata" / "source_provenance"
            dest_prov.mkdir(parents=True, exist_ok=True)
            for p in sorted(prov_dir.glob("*.json")):
                shutil.copy2(p, dest_prov / p.name)

        if plan["redistribution_mode"] == "restricted_local":
            notice = (
                "NON-REDISTRIBUTION NOTICE\n"
                "=========================\n"
                "This processed artifact is for restricted local use only.\n"
                "allowed_for_redistribution is false or null for one or more sources.\n"
                "Do not publish or redistribute this directory without updated "
                "human eligibility decisions.\n"
            )
            notice_name = out_cfg.get(
                "restricted_notice_filename", "NON_REDISTRIBUTION_NOTICE.txt"
            )
            (staging / text_subdir / notice_name).write_text(notice, encoding="utf-8")
            (staging / notice_name).write_text(notice, encoding="utf-8")

        readme = [
            f"# {plan['corpus_name']} {plan['corpus_version']}",
            "",
            f"Redistribution mode: **{plan['redistribution_mode']}**",
            "",
            "See `reports/CORPUS_CARD.md` for full documentation.",
            "",
            "This corpus was produced by a gated promotion pipeline. "
            "Do not treat interim data as approved for training without "
            "matching eligibility records.",
            "",
        ]
        (staging / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

        # checksums for key artifacts
        for rel in [
            "README.md",
            "reports/CORPUS_CARD.md",
            "metadata/sources.json",
            "metadata/documents.jsonl",
        ]:
            p = staging / rel
            if p.is_file():
                checksums[rel] = sha256_file(p)

        build_manifest = {
            "generated_at": plan["generated_at"],
            "tool": plan["tool"],
            "corpus_name": plan["corpus_name"],
            "corpus_version": plan["corpus_version"],
            "git_commit": plan.get("git_commit"),
            "promotion_config_version": config.get("version"),
            "redistribution_mode": plan["redistribution_mode"],
            "eligible_sources": eligible_ids,
            "deduplication": {
                "within_source_exact": within,
                "cross_source_exact": cross,
                "source_priority": priority,
                "n_log_entries": len(dedup_log),
            },
            "eligibility_snapshot_sha256": checksums.get(
                "metadata/eligibility_snapshot.json"
            ),
            "input_checksums": {
                sid: source_outputs[sid]["input_sha256"] for sid in eligible_ids
            },
            "output_checksums": {
                sid: source_outputs[sid]["sha256"] for sid in eligible_ids
            },
            "cleaning_config_checksums": {},
        }
        for sid in eligible_ids:
            scfg = source_cfgs[sid]
            cp = scfg.get("cleaning_config_path")
            if cp:
                build_manifest["cleaning_config_checksums"][sid] = {
                    "path": cp,
                    "sha256": sha256_file(repo_root / cp),
                }

        (staging / "metadata" / "build_manifest.json").write_text(
            json.dumps(build_manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        checksums["metadata/build_manifest.json"] = sha256_file(
            staging / "metadata" / "build_manifest.json"
        )
        (staging / "metadata" / "checksums.json").write_text(
            json.dumps(checksums, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        write_atomic_tree(staging, final_root)
        # staging moved; mark success
        plan["dry_run"] = False
        plan["status"] = "promoted"
        plan["output_root"] = str(
            final_root.relative_to(repo_root)
            if final_root.is_relative_to(repo_root)
            else final_root
        )
        plan["files_written"] = sorted(
            str(p.relative_to(final_root)) for p in final_root.rglob("*") if p.is_file()
        )
        plan["build_manifest"] = build_manifest
        return plan
    except Exception:
        # Clean up staging if still present
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        # Ensure no partial final
        promoting = final_root.with_name(final_root.name + ".promoting")
        if promoting.exists():
            shutil.rmtree(promoting, ignore_errors=True)
        if final_root.exists():
            # Only remove if we created a partial — prefer not to delete unknown
            pass
        raise


def format_dry_run_report(plan: dict[str, Any]) -> str:
    lines = [
        "# Promotion dry-run report",
        "",
        f"**Status:** `{plan['status']}`",
        f"**Promotion allowed:** {plan['promotion_allowed']}",
        f"**Primary reason:** {plan.get('primary_reason')}",
        f"**Redistribution mode (planned):** `{plan.get('redistribution_mode')}`",
        f"**Local training permitted (any eligible):** {plan.get('local_training_permitted')}",
        f"**Redistribution permitted (all eligible):** {plan.get('redistribution_permitted')}",
        "",
        "## Eligible sources",
        "",
    ]
    if plan.get("eligible_sources"):
        for e in plan["eligible_sources"]:
            lines.append(
                f"- `{e['source_id']}` → input `{e.get('expected_input')}` "
                f"output `{e.get('output_filename')}`"
            )
    else:
        lines.append("- _(none)_")
    lines.extend(["", "## Blocked sources", ""])
    for b in plan.get("blocked_sources") or []:
        lines.append(f"### `{b['source_id']}`")
        for r in b.get("blocking_reasons") or []:
            lines.append(f"- {r}")
        lines.append("")
    lines.extend(["## Blocking reasons (aggregate)", ""])
    for r in plan.get("blocking_reasons") or []:
        lines.append(f"- {r}")
    lines.extend(["", "## Unresolved fields", ""])
    for u in plan.get("unresolved_fields") or []:
        lines.append(f"- `{u['source_id']}.{u['field']}` = `{u['value']}`")
    lines.extend(["", "## Expected output paths", ""])
    po = plan.get("planned_outputs") or {}
    lines.append(f"- corpus root: `{po.get('corpus_root')}`")
    lines.append(f"- text subdir: `{po.get('text_subdir')}`")
    for sf in po.get("source_text_files") or []:
        lines.append(f"- source text: `{sf['path']}` ({sf['source_id']})")
    for k, v in (po.get("files") or {}).items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(["", "## Planned input checksums", ""])
    pcs = plan.get("planned_checksums") or {}
    if pcs:
        for k, v in pcs.items():
            lines.append(f"- `{k}`: `{v}`")
    else:
        lines.append("- _(none — no eligible inputs)_")
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Promote interim cleaning outputs to a versioned processed corpus (gated)."
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/data/promotion_v0_1.json"),
    )
    p.add_argument(
        "--eligibility",
        type=Path,
        default=Path("data/metadata/source_eligibility.json"),
    )
    p.add_argument(
        "--inventory",
        type=Path,
        default=None,
        help="Override inventory path (default from config)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Report plan without copying or modifying corpus content",
    )
    p.add_argument(
        "--report-output",
        type=Path,
        default=None,
        help="Optional path for dry-run markdown report",
    )
    p.add_argument("--repo-root", type=Path, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    elig_path = (
        args.eligibility
        if args.eligibility.is_absolute()
        else root / args.eligibility
    )
    try:
        config = load_json(config_path)
        eligibility = load_eligibility(elig_path)
        inv_rel = args.inventory or config.get(
            "inventory_path", "data/metadata/inventory.json"
        )
        inv_path = inv_rel if Path(inv_rel).is_absolute() else root / inv_rel
        inventory = load_json(Path(inv_path))
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    try:
        plan = run_promotion(
            config=config,
            eligibility=eligibility,
            inventory=inventory,
            repo_root=root,
            dry_run=bool(args.dry_run),
        )
    except (OSError, ValueError) as e:
        print(f"error: promotion failed: {e}", file=sys.stderr)
        return 1

    if args.dry_run or not plan.get("promotion_allowed"):
        report = format_dry_run_report(plan)
        report_path = args.report_output
        if report_path is None:
            report_path = root / "data" / "reports" / "promotion_dry_run_report.md"
        elif not report_path.is_absolute():
            report_path = root / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(report)
        print(f"\nWrote report: {report_path}")
        if not plan.get("promotion_allowed"):
            print("\npromotion blocked")
            print(f"reason: {plan.get('primary_reason')}")
            return 2
        print("\ndry-run complete (no corpus files written)")
        return 0

    print(f"promotion complete → {plan.get('output_root')}")
    print(f"  files: {len(plan.get('files_written') or [])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
