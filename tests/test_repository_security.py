"""Publication safeguards must fail closed without opening protected content."""

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/security/check_public_repository.py"
SPEC = importlib.util.spec_from_file_location("publication_check", MODULE_PATH)
security = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(security)


class PublicationCheckTest(unittest.TestCase):
    def test_sensitive_and_locked_paths_are_rejected_before_read(self):
        paths = [
            ".aws/credentials", ".env.production", "local/private.pem", ".ssh/id_ed25519",
            "data/splits/chichewa_corpus_v0.1/test/combined.txt",
            "data/splits/chichewa_corpus_v0.1/metadata/test_documents.jsonl",
            "data/research/morphology_benchmark_v0.1/locked/holdout_payload.sealed.json",
            "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/evaluation/test_metrics.json",
        ]
        def forbidden_read(path):
            self.fail(f"Protected path was read: {path}")
        issues, scanned = security.check_paths(paths, forbidden_read, [])
        self.assertEqual(len(issues), len(paths))
        self.assertEqual(scanned, 0)

    def test_public_lock_notices_and_templates_are_allowed(self):
        for path in [".env.example", "tests/test_lm_baselines.py", "README.md",
                     "data/research/morphology_benchmark_v0.1/locked/README.md",
                     "data/research/morphology_benchmark_v0.1/locked/RELEASE_BLOCKED"]:
            self.assertIsNone(security.path_issue(path), path)

    def test_credential_value_is_never_returned(self):
        fabricated = "hf_" + "A" * 32
        issues, scanned = security.check_paths(
            ["example.py"], lambda _: fabricated.encode(), security.load_plugins()
        )
        self.assertEqual(scanned, 1)
        self.assertTrue(issues)
        self.assertNotIn(fabricated, "\n".join(issues))

    def test_expected_hash_and_platform_metadata_is_allowed(self):
        text = '"sha256": "' + "abcdef0123456789" * 4 + '", "platform": "Linux-6.6.87.2"'
        self.assertEqual(security.credential_findings(text, security.load_plugins()), [])


if __name__ == "__main__":
    unittest.main()
