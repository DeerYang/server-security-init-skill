#!/usr/bin/env python3
"""Validate the server-security-init skill package before publishing."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "server-security-init"

REQUIRED_FILES = [
    SKILL_DIR / "SKILL.md",
    SKILL_DIR / "agents" / "openai.yaml",
    SKILL_DIR / "references" / "ubuntu-openssh-ufw-fail2ban.md",
    SKILL_DIR / "references" / "verification-checklist.md",
    ROOT / "README.md",
    ROOT / "README.zh-CN.md",
    ROOT / "LICENSE",
    ROOT / "SECURITY.md",
]

SECRET_PATTERNS = {
    "private key block": re.compile(r"-----BEGIN (?:OPENSSH|RSA|DSA|EC) PRIVATE KEY-----"),
    "ssh private key path marker": re.compile(r"\bIdentityFile\s+.*(?:Users\\|/home/)[^\s]+", re.IGNORECASE),
    "public ssh key material": re.compile(r"\bssh-ed25519\s+AAAA[0-9A-Za-z+/=]+"),
    "password assignment": re.compile(r"\b(?:password|passwd)\s*[:=]\s*\S+", re.IGNORECASE),
    "api token assignment": re.compile(r"\b(?:api[_-]?key|token|secret)\s*[:=]\s*\S+", re.IGNORECASE),
}

PERSONAL_PATTERNS = {
    "personal username": re.compile(r"\brunsing\b", re.IGNORECASE),
    "personal domain": re.compile(r"\bdeerstack\.com\b", re.IGNORECASE),
    "example server alias": re.compile(r"\b(?:Georgia|DigitalFyre|Novix|Dmit|AaITR|Tencent)\b", re.IGNORECASE),
    "personal port": re.compile(r"\b28936\b"),
    "public IPv4 address": re.compile(
        r"\b(?!(?:127|10|192\.168|172\.(?:1[6-9]|2\d|3[0-1]))\.)"
        r"(?:\d{1,3}\.){3}\d{1,3}\b"
    ),
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_required_files() -> None:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))


def validate_frontmatter() -> None:
    text = read_text(SKILL_DIR / "SKILL.md")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        fail("SKILL.md must start with YAML frontmatter")

    lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    keys = [line.split(":", 1)[0] for line in lines if ":" in line]
    if keys != ["name", "description"]:
        fail(f"SKILL.md frontmatter must contain only name and description; got {keys}")

    frontmatter = match.group(1)
    if "name: server-security-init" not in frontmatter:
        fail("SKILL.md name must be server-security-init")
    if "Use when" not in frontmatter:
        fail("SKILL.md description should include a clear 'Use when' trigger")


def iter_text_files() -> list[Path]:
    ignored_dirs = {".git", "__pycache__"}
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.is_dir():
            continue
        if any(part in ignored_dirs for part in path.parts):
            continue
        if path.suffix.lower() in {".md", ".yaml", ".yml", ".py", ".txt", ".gitignore"} or path.name in {
            "LICENSE"
        }:
            files.append(path)
    return files


def validate_sensitive_patterns() -> None:
    violations: list[str] = []
    for path in iter_text_files():
        rel = path.relative_to(ROOT)
        text = read_text(path)
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                violations.append(f"{rel}: possible {label}")
        for label, pattern in PERSONAL_PATTERNS.items():
            for match in pattern.finditer(text):
                value = match.group(0)
                if value in {"127.0.0.1", "0.0.0.0"}:
                    continue
                if rel == Path("scripts/validate_skill.py"):
                    continue
                violations.append(f"{rel}: possible {label}: {value}")
    if violations:
        fail("sensitive-pattern check failed:\n" + "\n".join(f"- {item}" for item in violations))


def validate_reference_links() -> None:
    text = read_text(SKILL_DIR / "SKILL.md")
    for ref in [
        "references/ubuntu-openssh-ufw-fail2ban.md",
        "references/verification-checklist.md",
    ]:
        if ref not in text:
            fail(f"SKILL.md does not mention {ref}")


def main() -> int:
    validate_required_files()
    validate_frontmatter()
    validate_reference_links()
    validate_sensitive_patterns()
    print("server-security-init skill package validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
