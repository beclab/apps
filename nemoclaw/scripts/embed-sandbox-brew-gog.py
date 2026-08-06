#!/usr/bin/env python3
"""Embed brew-local-wrapper.sh and patch-openclaw-gog-skill.py into configmap-sandbox-bridge.yaml."""
from __future__ import annotations

import sys
from pathlib import Path

EMBED = (
    ("brew-local-wrapper.sh", "  # Brew wrapper: steipete/tap/gogcli -> openclaw/tap/gogcli for openclaw skills.\n"),
    ("patch-openclaw-gog-skill.py", "  # Patch bundled gog SKILL.md after openclaw npm install.\n"),
)

MARKER = "  gog-shim-reconcile.sh: |"


def embed_file(cm_path: Path, key: str, header: str, body: str) -> None:
    lines = cm_path.read_text(encoding="utf-8").splitlines(keepends=True)
    needle = "  " + key + ": |"
    start = end = None
    for i, ln in enumerate(lines):
        if ln.rstrip("\n") == needle:
            start = i
        if start is not None and i > start and ln.startswith("  ") and not ln.startswith("    ") and ln.rstrip() != needle:
            end = i
            break
    if start is None:
        # insert before gog-shim marker
        for i, ln in enumerate(lines):
            if ln.rstrip("\n") == MARKER:
                indented = "".join(
                    "    " + (ln if ln.endswith("\n") else ln + "\n") for ln in body.splitlines(True)
                )
                block = header + "  " + key + ": |\n" + indented
                lines.insert(i, block)
                cm_path.write_text("".join(lines), encoding="utf-8")
                print("inserted " + key + " before gog-shim-reconcile.sh")
                return
        print("could not find insert point for " + key, file=sys.stderr)
        sys.exit(1)
    indented = "".join("    " + (ln if ln.endswith("\n") else ln + "\n") for ln in body.splitlines(True))
    new_block = header + "  " + key + ": |\n" + indented
    out = "".join(lines[:start]) + new_block + "".join(lines[end if end is not None else len(lines) :])
    cm_path.write_text(out, encoding="utf-8")
    print("updated " + key)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    cm_path = root / "templates" / "configmap-sandbox-bridge.yaml"
    for fname, header in EMBED:
        src = root / "files" / fname
        body = src.read_text(encoding="utf-8")
        if not body.endswith("\n"):
            body += "\n"
        embed_file(cm_path, fname, header, body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
