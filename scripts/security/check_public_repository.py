#!/usr/bin/env python3
"""Reject credentials/protected artifacts in the public index without logging values."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
SENSITIVE_DIRS = {".aws", ".ssh", ".azure"}
SENSITIVE_NAMES = {".netrc", ".npmrc", ".pypirc", ".git-credentials", "credentials",
                   "secrets.json", "secrets.yaml", "secrets.yml"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".model",
                   ".pt", ".pth", ".bin", ".safetensors", ".woff", ".woff2"}
PATTERNS = {
    "Hugging Face token": re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    "Anthropic token": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    "OpenAI token": re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}"),
    "Bearer token": re.compile(r"(?i)\bBearer\s+([A-Za-z0-9._~+/=-]{16,})"),
    "Credential URL": re.compile(
        r"(?i)\b(?:https?|postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqps?)"
        r"://[^\s/:@]+:[^\s/@]+@[^\s]+"
    ),
}


def path_issue(path: str) -> str | None:
    p = PurePosixPath(path)
    parts = p.parts
    name = p.name.lower()
    if set(parts) & SENSITIVE_DIRS or ".config/gcloud/" in path:
        return "credential-store directory"
    if (name in SENSITIVE_NAMES or name.startswith("credentials.")
            or name.startswith(("id_rsa", "id_ed25519"))
            or (name.startswith(".env") and name != ".env.example")
            or p.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".keystore"}
            or (name.endswith(".json") and re.search(r"service[-_]account", name))):
        return "credential filename"
    if path.startswith("data/splits/") and (
        "test" in parts or ("metadata" in parts and name == "test_documents.jsonl")
    ):
        return "locked LM-test artifact"
    if path.startswith("data/tokenizers/") and name == "test_metrics.json":
        return "test-evaluation artifact"
    if (path.startswith("data/research/morphology_benchmark_") and "locked" in parts
            and name not in {"readme.md", "release_blocked"}):
        return "locked morphology-holdout artifact"
    return None


def load_plugins():
    try:
        from detect_secrets.settings import default_settings, get_plugins
    except ImportError as exc:
        raise RuntimeError("Install requirements-security.txt before committing.") from exc
    with default_settings() as settings:
        settings.disable_plugins("HexHighEntropyString", "Base64HighEntropyString", "IPPublicDetector")
        return list(get_plugins())


def credential_findings(text: str, plugins) -> list[tuple[int, str]]:
    findings: set[tuple[int, str]] = set()
    for plugin in plugins:
        # analyze_string does not call provider verification APIs.
        for value in plugin.analyze_string(text):
            if value:
                offset = text.find(value)
                findings.add((text.count("\n", 0, offset) + 1, plugin.secret_type))
    for name, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            findings.add((text.count("\n", 0, match.start()) + 1, name))
    return sorted(findings)


def indexed_paths(staged: bool) -> list[str]:
    args = (["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"] if staged
            else ["ls-files", "-z"])
    output = subprocess.check_output(["git", *args], cwd=ROOT)
    return sorted(set(p for p in output.decode("utf-8").split("\0") if p))


def check_paths(paths, read_blob, plugins) -> tuple[list[str], int]:
    issues = []
    scanned = 0
    for path in paths:
        reason = path_issue(path)
        if reason:
            issues.append(f"{path}: {reason}; remove from the index, retain privately")
            continue  # Never read a protected file or credential-store file.
        if PurePosixPath(path).suffix.lower() in BINARY_SUFFIXES:
            continue
        blob = read_blob(path)
        if b"\0" in blob:
            continue
        scanned += 1
        text = blob.decode("utf-8", errors="replace")
        for line, kind in credential_findings(text, plugins):
            issues.append(f"{path}:{line}: {kind} [value redacted]")
    return issues, scanned


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Check added/modified staged blobs only")
    args = parser.parse_args()
    try:
        plugins = load_plugins()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    paths = indexed_paths(args.staged)
    def read_blob(path):
        return subprocess.check_output(["git", "show", f":{path}"], cwd=ROOT)
    issues, scanned = check_paths(paths, read_blob, plugins)
    for issue in issues:
        print(issue, file=sys.stderr)
    print(f"Publication check: {scanned} indexed text files scanned; {len(issues)} findings.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
