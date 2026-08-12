#!/usr/bin/env python3
"""Tests for license-gated processed-corpus promotion pipeline."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts" / "data"
sys.path.insert(0, str(SCRIPTS))

import promote_processed_corpus as promo  # noqa: E402


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _eligible_source(
    source_id: str,
    *,
    training: bool | None = True,
    redistrib: bool | None = True,
    include: bool | None = True,
    provenance: str = "verified",
    license_status: str = "verified",
    technical: str = "cleaning_v2_validated",
    redundant: bool = False,
    excluded: bool = False,
    holdout_only: bool = False,
) -> dict:
    return {
        "source_id": source_id,
        "provenance_status": provenance,
        "source_url": "https://example.test/source",
        "license_status": license_status,
        "license_name": "Test-License",
        "license_url": "https://example.test/license",
        "allowed_for_training": training,
        "allowed_for_redistribution": redistrib,
        "attribution_required": True,
        "reviewed_by": "tester",
        "reviewed_at": "2026-08-05T00:00:00Z",
        "evidence_notes": "fixture",
        "technical_status": technical,
        "include_in_processed_corpus": include,
        "redundant": redundant,
        "holdout_only": holdout_only,
        "excluded": excluded,
    }


def _build_fixture(
    root: Path,
    *,
    eligibility_sources: list[dict],
    bible_text: str = "line a\nline b\nline a\n",
    wiki_text: str = "line a\nline c\n",
    raw_bible: str | None = None,
    raw_wiki: str | None = None,
    within_dedupe: bool = True,
    cross_dedupe: bool = False,
    mess_cleaning_config_sha: bool = False,
    mess_interim_checksum: bool = False,
) -> tuple[dict, dict, dict]:
    """Create synthetic repo layout; return config, eligibility, inventory."""
    raw_bible = raw_bible if raw_bible is not None else "RAW BIBLE\n"
    raw_wiki = raw_wiki if raw_wiki is not None else "RAW WIKI\n"
    raw_existing = "RAW EXISTING\n"

    _write(root / "data/raw/bible/bible_clean.txt", raw_bible)
    _write(root / "data/raw/wikipedia/wiki_clean.txt", raw_wiki)
    _write(root / "data/raw/existing_corpus/chichewa_corpus.txt", raw_existing)

    bible_clean = bible_text
    wiki_clean = wiki_text
    _write(root / "data/interim/cleaning_v2/bible/cleaned.txt", bible_clean)
    _write(root / "data/interim/cleaning_v2/wikipedia/cleaned.txt", wiki_clean)

    cleaning_cfg = {"version": "2.0.0", "fixture": True}
    cfg_path = root / "configs/data/cleaning_v2.json"
    _write(cfg_path, json.dumps(cleaning_cfg, indent=2) + "\n")
    cfg_sha = _sha(cfg_path.read_bytes())

    summary = {
        "sources": {
            "bible": {
                "cleaned_sha256": _sha(bible_clean.encode("utf-8")),
                "raw_sha256": _sha(raw_bible.encode("utf-8")),
            },
            "wikipedia": {
                "cleaned_sha256": (
                    "deadbeef" * 8
                    if mess_interim_checksum
                    else _sha(wiki_clean.encode("utf-8"))
                ),
                "raw_sha256": _sha(raw_wiki.encode("utf-8")),
            },
        }
    }
    _write(
        root / "data/interim/cleaning_v2/summary.json",
        json.dumps(summary, indent=2) + "\n",
    )

    inventory = {
        "files": [
            {
                "source_id": "bible",
                "relative_path": "data/raw/bible/bible_clean.txt",
                "sha256": _sha(raw_bible.encode("utf-8")),
            },
            {
                "source_id": "wikipedia",
                "relative_path": "data/raw/wikipedia/wiki_clean.txt",
                "sha256": _sha(raw_wiki.encode("utf-8")),
            },
            {
                "source_id": "existing_corpus",
                "relative_path": "data/raw/existing_corpus/chichewa_corpus.txt",
                "sha256": _sha(raw_existing.encode("utf-8")),
            },
        ]
    }
    _write(root / "data/metadata/inventory.json", json.dumps(inventory, indent=2) + "\n")

    expected_cfg_sha = "0" * 64 if mess_cleaning_config_sha else cfg_sha
    config = {
        "version": "0.1.0",
        "corpus_name": "chichewa_corpus",
        "corpus_version": "v0.1",
        "output": {
            "processed_root": "data/processed",
            "corpus_dirname": "chichewa_corpus_v0.1",
            "exportable_subdir": "corpus",
            "restricted_subdir": "corpus_restricted_local",
            "restricted_notice_filename": "NON_REDISTRIBUTION_NOTICE.txt",
        },
        "gates": {
            "require_provenance_verified": True,
            "require_license_verified": True,
            "require_allowed_for_training_true": True,
            "require_include_in_processed_corpus_true": True,
            "require_technical_output_exists": True,
            "require_technical_checksum_match": True,
            "require_raw_checksum_match_inventory": True,
            "require_cleaning_config_checksum_match": True,
            "block_redundant": True,
            "block_excluded": True,
            "block_holdout_only": True,
        },
        "sources": {
            "bible": {
                "source_id": "bible",
                "raw_relative_path": "data/raw/bible/bible_clean.txt",
                "interim_cleaned_path": "data/interim/cleaning_v2/bible/cleaned.txt",
                "interim_summary_path": "data/interim/cleaning_v2/summary.json",
                "cleaning_config_path": "configs/data/cleaning_v2.json",
                "expected_cleaning_config_sha256": expected_cfg_sha,
                "output_filename": "bible.txt",
            },
            "wikipedia": {
                "source_id": "wikipedia",
                "raw_relative_path": "data/raw/wikipedia/wiki_clean.txt",
                "interim_cleaned_path": "data/interim/cleaning_v2/wikipedia/cleaned.txt",
                "interim_summary_path": "data/interim/cleaning_v2/summary.json",
                "cleaning_config_path": "configs/data/cleaning_v2.json",
                "expected_cleaning_config_sha256": expected_cfg_sha,
                "output_filename": "wikipedia.txt",
            },
            "existing_corpus": {
                "source_id": "existing_corpus",
                "raw_relative_path": "data/raw/existing_corpus/chichewa_corpus.txt",
                "interim_cleaned_path": None,
            },
        },
        "deduplication": {
            "within_source_exact": within_dedupe,
            "cross_source_exact": cross_dedupe,
            "source_priority": ["bible", "wikipedia"],
        },
        "holdout_metrics_reference": {
            "stage1_removal_precision": 0.975,
            "stage1_false_removal_rate": 0.025,
            "stage1_useful_text_retention": 0.955,
            "combined_stage1_stage2_n_labels": 120,
            "combined_removal_precision": 0.988,
            "combined_false_removal_rate": 0.0125,
            "combined_useful_text_retention": 0.955,
            "notes": "fixture",
        },
    }
    eligibility = {
        "schema_version": "1.0.0",
        "sources": eligibility_sources,
    }
    return config, eligibility, inventory


class TestPromotionGates(unittest.TestCase):
    def test_unresolved_eligibility_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source(
                    "bible",
                    training=None,
                    redistrib=None,
                    include=None,
                    provenance="pending",
                    license_status="pending",
                    technical="light_touch_clean",
                ),
                _eligible_source(
                    "wikipedia",
                    training=None,
                    redistrib=None,
                    include=None,
                    provenance="pending",
                    license_status="pending",
                ),
                _eligible_source(
                    "existing_corpus",
                    training=None,
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(root, eligibility_sources=sources)
            plan = promo.run_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
                dry_run=True,
            )
            self.assertFalse(plan["promotion_allowed"])
            self.assertEqual(plan["status"], "blocked")
            self.assertIn("unresolved source eligibility", plan["primary_reason"])
            self.assertFalse((root / "data/processed/chichewa_corpus_v0.1").exists())

    def test_training_permission_null_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", training=None, include=True),
                _eligible_source("wikipedia", training=True, include=True),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(root, eligibility_sources=sources)
            plan = promo.plan_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
            )
            self.assertFalse(plan["promotion_allowed"])
            joined = " ".join(plan["blocking_reasons"])
            self.assertIn("allowed_for_training is null", joined)

    def test_training_permission_false_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", training=False, include=True),
                _eligible_source("wikipedia", training=True, include=True),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(root, eligibility_sources=sources)
            plan = promo.plan_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
            )
            self.assertFalse(plan["promotion_allowed"])
            self.assertTrue(
                any("allowed_for_training is false" in r for r in plan["blocking_reasons"])
            )

    def test_verified_training_permits_local_only_when_redistrib_false(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", training=True, redistrib=False, include=True),
                _eligible_source("wikipedia", training=True, redistrib=False, include=True),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(root, eligibility_sources=sources)
            plan = promo.run_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
                dry_run=False,
            )
            self.assertTrue(plan["promotion_allowed"] or plan["status"] == "promoted")
            self.assertEqual(plan["status"], "promoted")
            self.assertEqual(plan["redistribution_mode"], "restricted_local")
            out = root / "data/processed/chichewa_corpus_v0.1"
            self.assertTrue(out.is_dir())
            restricted = out / "corpus_restricted_local"
            self.assertTrue(restricted.is_dir())
            self.assertTrue((restricted / "bible.txt").is_file())
            self.assertTrue((restricted / "NON_REDISTRIBUTION_NOTICE.txt").is_file())
            self.assertFalse((out / "corpus").exists())

    def test_redistribution_true_exportable_structure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", training=True, redistrib=True, include=True),
                _eligible_source("wikipedia", training=True, redistrib=True, include=True),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(root, eligibility_sources=sources)
            plan = promo.run_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
                dry_run=False,
            )
            self.assertEqual(plan["status"], "promoted")
            self.assertEqual(plan["redistribution_mode"], "exportable")
            out = root / "data/processed/chichewa_corpus_v0.1"
            self.assertTrue((out / "corpus" / "bible.txt").is_file())
            self.assertTrue((out / "corpus" / "wikipedia.txt").is_file())
            self.assertTrue((out / "metadata" / "build_manifest.json").is_file())
            self.assertTrue((out / "reports" / "CORPUS_CARD.md").is_file())

    def test_redundant_source_cannot_be_included(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", include=True),
                _eligible_source(
                    "existing_corpus",
                    include=True,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=False,
                ),
            ]
            config, eligibility, inventory = _build_fixture(root, eligibility_sources=sources)
            plan = promo.plan_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
            )
            self.assertFalse(plan["promotion_allowed"])
            joined = " ".join(plan["blocking_reasons"]).lower()
            self.assertTrue("redundant" in joined or "existing_corpus" in joined)

    def test_existing_corpus_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", include=True),
                _eligible_source("wikipedia", include=True),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(root, eligibility_sources=sources)
            plan = promo.run_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
                dry_run=False,
            )
            self.assertEqual(plan["status"], "promoted")
            out = root / "data/processed/chichewa_corpus_v0.1"
            text_files = list((out / "corpus").glob("*.txt"))
            names = {p.name for p in text_files}
            self.assertNotIn("existing_corpus.txt", names)
            self.assertNotIn("chichewa_corpus.txt", names)
            sources_meta = json.loads(
                (out / "metadata" / "sources.json").read_text(encoding="utf-8")
            )
            self.assertIn("existing_corpus", sources_meta["excluded"])

    def test_checksum_mismatch_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", include=True),
                _eligible_source("wikipedia", include=True),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(
                root, eligibility_sources=sources, mess_interim_checksum=True
            )
            plan = promo.plan_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
            )
            self.assertFalse(plan["promotion_allowed"])
            self.assertTrue(
                any("checksum mismatch" in r for r in plan["blocking_reasons"])
            )

    def test_cleaning_config_mismatch_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", include=True),
                _eligible_source("wikipedia", include=True),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(
                root, eligibility_sources=sources, mess_cleaning_config_sha=True
            )
            plan = promo.plan_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
            )
            self.assertFalse(plan["promotion_allowed"])
            self.assertTrue(
                any("cleaning-config checksum mismatch" in r for r in plan["blocking_reasons"])
            )

    def test_dry_run_creates_no_corpus_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", include=True),
                _eligible_source("wikipedia", include=True),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(root, eligibility_sources=sources)
            plan = promo.run_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
                dry_run=True,
            )
            self.assertTrue(plan["promotion_allowed"])
            self.assertFalse((root / "data/processed/chichewa_corpus_v0.1").exists())
            self.assertEqual(plan.get("files_written"), [])

    def test_no_raw_file_modifications(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", include=True),
                _eligible_source("wikipedia", include=True),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(root, eligibility_sources=sources)
            raw_b = root / "data/raw/bible/bible_clean.txt"
            before = raw_b.read_bytes()
            promo.run_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
                dry_run=False,
            )
            self.assertEqual(raw_b.read_bytes(), before)

    def test_exact_deduplication_within_source(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", include=True),
                _eligible_source("wikipedia", include=False, training=None, provenance="pending", license_status="pending"),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(
                root,
                eligibility_sources=sources,
                bible_text="alpha\nbeta\nalpha\ngamma\n",
                within_dedupe=True,
                cross_dedupe=False,
            )
            plan = promo.run_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
                dry_run=False,
            )
            self.assertEqual(plan["status"], "promoted")
            text = (root / "data/processed/chichewa_corpus_v0.1/corpus/bible.txt").read_text(
                encoding="utf-8"
            )
            self.assertEqual(text.splitlines(), ["alpha", "beta", "gamma"])

    def test_source_attribution_preserved_after_cross_dedup(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", include=True),
                _eligible_source("wikipedia", include=True),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(
                root,
                eligibility_sources=sources,
                bible_text="shared\nbible_only\n",
                wiki_text="shared\nwiki_only\n",
                within_dedupe=True,
                cross_dedupe=True,
            )
            plan = promo.run_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
                dry_run=False,
            )
            self.assertEqual(plan["status"], "promoted")
            out = root / "data/processed/chichewa_corpus_v0.1"
            bible_lines = (out / "corpus/bible.txt").read_text(encoding="utf-8").splitlines()
            wiki_lines = (out / "corpus/wikipedia.txt").read_text(encoding="utf-8").splitlines()
            self.assertIn("shared", bible_lines)
            self.assertNotIn("shared", wiki_lines)  # dropped from lower priority
            log = [
                json.loads(line)
                for line in (out / "metadata/deduplication_log.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            ]
            cross = [r for r in log if r["action"] == "drop_cross_source_exact"]
            self.assertTrue(cross)
            self.assertIn("bible", cross[0]["retained_sources"])
            self.assertIn("wikipedia", cross[0]["retained_sources"])

    def test_atomic_output_and_failed_promotion_no_partial(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Unresolved → blocked, no directory
            sources = [
                _eligible_source("bible", include=None, training=None, provenance="pending"),
            ]
            config, eligibility, inventory = _build_fixture(root, eligibility_sources=sources)
            plan = promo.run_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
                dry_run=False,
            )
            self.assertFalse(plan["promotion_allowed"])
            processed = root / "data/processed"
            if processed.exists():
                leftovers = list(processed.rglob("*"))
                # staging should not remain
                self.assertFalse(
                    any(".promoting" in str(p) or "_staging_" in str(p) for p in leftovers)
                )
            self.assertFalse((root / "data/processed/chichewa_corpus_v0.1").exists())

    def test_corpus_card_contains_required_sections(self) -> None:
        plan = {
            "corpus_name": "chichewa_corpus",
            "corpus_version": "v0.1",
            "generated_at": "2026-08-05T00:00:00Z",
            "eligible_sources": [{"source_id": "bible"}],
            "redistribution_mode": "exportable",
            "redistribution_permitted": True,
            "git_commit": None,
        }
        config = {
            "deduplication": {
                "within_source_exact": True,
                "cross_source_exact": False,
                "source_priority": ["bible", "wikipedia"],
            },
            "holdout_metrics_reference": {"notes": "n/a"},
        }
        eligibility = {
            "sources": [
                {"source_id": "bible", "provenance_status": "verified", "source_url": "x",
                 "license_status": "verified", "license_name": "L",
                 "allowed_for_training": True, "allowed_for_redistribution": True,
                 "attribution_required": True},
                {"source_id": "existing_corpus"},
            ]
        }
        card = promo.render_corpus_card(plan, config, eligibility)
        for section in promo.CORPUS_CARD_SECTIONS:
            self.assertIn(section, card)
        # numbered headings present
        for i in range(1, 21):
            self.assertIn(f"## {i}.", card)

    def test_deterministic_manifest_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = [
                _eligible_source("bible", include=True),
                _eligible_source(
                    "existing_corpus",
                    include=False,
                    technical="redundant_composite",
                    redundant=True,
                    excluded=True,
                ),
            ]
            config, eligibility, inventory = _build_fixture(
                root,
                eligibility_sources=sources,
                bible_text="a\nb\n",
            )
            p1 = promo.run_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
                dry_run=False,
            )
            man1 = json.loads(
                (root / "data/processed/chichewa_corpus_v0.1/metadata/build_manifest.json")
                .read_text(encoding="utf-8")
            )
            # rebuild into new dirname
            shutil.rmtree(root / "data/processed/chichewa_corpus_v0.1")
            config["output"]["corpus_dirname"] = "chichewa_corpus_v0.1b"
            p2 = promo.run_promotion(
                config=config,
                eligibility=eligibility,
                inventory=inventory,
                repo_root=root,
                dry_run=False,
            )
            man2 = json.loads(
                (root / "data/processed/chichewa_corpus_v0.1b/metadata/build_manifest.json")
                .read_text(encoding="utf-8")
            )
            self.assertEqual(man1["eligible_sources"], man2["eligible_sources"])
            self.assertEqual(man1["input_checksums"], man2["input_checksums"])
            self.assertEqual(man1["output_checksums"], man2["output_checksums"])
            self.assertEqual(man1["deduplication"], man2["deduplication"])
            self.assertEqual(p1["status"], "promoted")
            self.assertEqual(p2["status"], "promoted")


class TestRealRepoVerifiedEligibility(unittest.TestCase):
    """Against the actual verified eligibility records (dry-run only)."""

    def test_verified_wikipedia_and_bible_eligibility(self) -> None:
        eligibility = promo.load_eligibility(
            REPO_ROOT / "data/metadata/source_eligibility.json"
        )
        by_id = {s["source_id"]: s for s in eligibility["sources"]}
        wiki = by_id["wikipedia"]
        bible = by_id["bible"]
        self.assertEqual(wiki["provenance_status"], "verified")
        self.assertEqual(wiki["license_status"], "verified")
        self.assertEqual(wiki["license_identifier"], "CC-BY-SA-4.0")
        self.assertTrue(wiki["allowed_for_training"])
        self.assertTrue(wiki["allowed_for_redistribution"])
        self.assertTrue(wiki["attribution_required"])
        self.assertTrue(wiki["share_alike_required"])
        self.assertTrue(wiki["modification_notice_required"])
        self.assertTrue(wiki["include_in_processed_corpus"])
        self.assertIn("latest", wiki["original_download_url"])
        self.assertIsNone(wiki.get("immutable_dated_dump_url"))
        self.assertEqual(bible["provenance_status"], "verified")
        self.assertEqual(bible["license_identifier"], "CC-BY-SA-4.0")
        self.assertEqual(bible["copyright_holder"], "Biblica, Inc.")
        self.assertTrue(bible["allowed_for_training"])
        self.assertTrue(bible["include_in_processed_corpus"])
        self.assertTrue(bible["trademark_conditions"]["do_not_use_trademark_as_corpus_brand"])
        self.assertTrue(
            bible["trademark_conditions"]["processed_corpus_is_modified_derivative"]
        )

    def test_existing_corpus_remains_excluded(self) -> None:
        eligibility = promo.load_eligibility(
            REPO_ROOT / "data/metadata/source_eligibility.json"
        )
        by_id = {s["source_id"]: s for s in eligibility["sources"]}
        ex = by_id["existing_corpus"]
        self.assertFalse(ex["include_in_processed_corpus"])
        self.assertFalse(ex["allowed_for_training"])
        self.assertTrue(ex["redundant"])
        self.assertTrue(ex["excluded"])
        self.assertEqual(ex["technical_status"], "redundant_composite")

    def test_source_specific_attribution_document(self) -> None:
        path = REPO_ROOT / "data/reports/SOURCE_ATTRIBUTION.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("Chichewa Wikipedia", text)
        self.assertIn("Biblica", text)
        self.assertIn("CC BY-SA 4.0", text)
        self.assertIn("Biblica®", text)
        self.assertIn("not necessarily endorsed", text)
        self.assertIn("unresolved legal interpretation", text.lower())
        # Must not use one merged generic-only attribution section
        self.assertIn("## 1. Chichewa Wikipedia", text)
        self.assertIn("## 2. Biblica Chichewa Bible", text)

    def test_bible_trademark_and_modification_notices_in_provenance(self) -> None:
        bible = promo.load_json(
            REPO_ROOT / "data/metadata/source_provenance/bible.json"
        )
        tm = bible["trademark_conditions"]
        self.assertTrue(tm["processed_corpus_is_treated_as_modified_derivative"])
        self.assertTrue(tm["do_not_use_biblica_as_processed_corpus_brand"])
        self.assertTrue(bible["extraction_and_cleaning"]["modification_notice_required"])
        self.assertIn("Biblica, Inc.", bible["required_attribution_text"])

    def test_moving_url_versus_dated_snapshot_metadata(self) -> None:
        wiki = promo.load_json(
            REPO_ROOT / "data/metadata/source_provenance/wikipedia.json"
        )
        acq = wiki["acquisition"]
        self.assertEqual(acq["url_class"], "moving_latest")
        self.assertIsNone(acq["original_download_url_immutable_dated"])
        self.assertIn("/latest/", acq["original_download_url_moving"])
        self.assertFalse(wiki["archive_evidence_in_repository"]["original_bz2_present"])

    def test_manual_acquisition_manifest(self) -> None:
        man = promo.load_json(
            REPO_ROOT / "configs/data/source_acquisition_manifest.json"
        )
        self.assertFalse(man["auto_download"])
        ids = {s["source_id"] for s in man["sources"]}
        self.assertEqual(ids, {"wikipedia", "bible", "existing_corpus"})
        wiki = next(s for s in man["sources"] if s["source_id"] == "wikipedia")
        self.assertEqual(wiki["artifacts"][0]["url_class"], "moving_latest")

    def test_real_dry_run_passes_with_verified_records(self) -> None:
        config = promo.load_json(REPO_ROOT / "configs/data/promotion_v0_1.json")
        eligibility = promo.load_eligibility(
            REPO_ROOT / "data/metadata/source_eligibility.json"
        )
        inventory = promo.load_json(REPO_ROOT / "data/metadata/inventory.json")
        plan = promo.run_promotion(
            config=config,
            eligibility=eligibility,
            inventory=inventory,
            repo_root=REPO_ROOT,
            dry_run=True,
        )
        self.assertTrue(plan["promotion_allowed"])
        self.assertEqual(plan["status"], "ok")
        self.assertEqual(
            {e["source_id"] for e in plan["eligible_sources"]},
            {"bible", "wikipedia"},
        )
        self.assertEqual(plan["redistribution_mode"], "exportable")
        self.assertEqual(plan.get("files_written"), [])
        # dry-run must not create the versioned corpus
        # (may already exist from a real promotion in the same session — only check
        # that this dry-run call itself wrote nothing)
        self.assertTrue(plan.get("dry_run"))

    def test_corpus_card_licenses_and_no_model_weight_claims(self) -> None:
        config = promo.load_json(REPO_ROOT / "configs/data/promotion_v0_1.json")
        eligibility = promo.load_eligibility(
            REPO_ROOT / "data/metadata/source_eligibility.json"
        )
        inventory = promo.load_json(REPO_ROOT / "data/metadata/inventory.json")
        plan = promo.plan_promotion(
            config=config,
            eligibility=eligibility,
            inventory=inventory,
            repo_root=REPO_ROOT,
        )
        card = promo.render_corpus_card(plan, config, eligibility)
        self.assertIn("CC BY-SA 4.0", card)
        self.assertIn("Biblica", card)
        self.assertIn("Chichewa Wikipedia", card)
        self.assertIn("unresolved legal interpretation", card)
        self.assertNotIn("model weights are free of CC BY-SA", card.lower())
        self.assertNotIn("weights are not adapted material", card.lower())
        self.assertIn("risk-stratified", card)
        self.assertIn("straightforward removal", card)
        for section in promo.CORPUS_CARD_SECTIONS:
            self.assertIn(section, card)

    def test_no_raw_or_holdout_changes_from_eligibility_update(self) -> None:
        """Sanity: critical paths still match inventory checksums."""
        inv = promo.load_json(REPO_ROOT / "data/metadata/inventory.json")
        for f in inv["files"]:
            p = REPO_ROOT / f["relative_path"]
            self.assertTrue(p.is_file(), f["relative_path"])
            self.assertEqual(promo.sha256_file(p), f["sha256"], f["source_id"])
        # holdout extension still locked present
        ext = REPO_ROOT / "data/reports/cleaning_holdout_extension_pool.jsonl"
        self.assertTrue(ext.is_file())
        n = sum(1 for line in ext.read_text(encoding="utf-8").splitlines() if line.strip())
        self.assertEqual(n, 130)
        self.assertFalse(
            (REPO_ROOT / "data/reports/cleaning_holdout_stage3_sample.jsonl").exists()
        )


if __name__ == "__main__":
    unittest.main()
