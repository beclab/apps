#!/usr/bin/env python3
"""Patch bundled gog skill formula: steipete/tap/gogcli -> openclaw/tap/gogcli.

Homebrew renamed the tap May 2026; OpenClaw <=2026.5.20 SKILL.md still lists the old name.
Run after openclaw npm install / on skill-env bootstrap so `openclaw config --section skills` works.
"""
import sys
from pathlib import Path

SEARCH_ROOTS = (
    Path("/usr/local/lib/node_modules/openclaw"),
    Path("/sandbox/.local/lib/node_modules/openclaw"),
)

# Order matters: longer / quoted forms first.
REPLACEMENTS = (
    ('""openclaw/tap/gogcli""', "openclaw/tap/gogcli"),
    ('"openclaw/tap/gogcli"', "openclaw/tap/gogcli"),
    ('""steipete/tap/gogcli""', "openclaw/tap/gogcli"),
    ('"steipete/tap/gogcli"', "openclaw/tap/gogcli"),
    ("steipete/tap/gogcli", "openclaw/tap/gogcli"),
    ('"steipete/tap"', "openclaw/tap"),
    ("steipete/tap", "openclaw/tap"),
)


def patch_skill(path):
    text = path.read_text(encoding="utf-8")
    original = text
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    if text == original:
        return False
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def main():
    for root in SEARCH_ROOTS:
        skill = root / "skills" / "gog" / "SKILL.md"
        if not skill.is_file():
            continue
        if patch_skill(skill):
            print("[patch-gog-skill] updated " + str(skill))
        else:
            print("[patch-gog-skill] already OK " + str(skill))
    return 0


if __name__ == "__main__":
    sys.exit(main())
