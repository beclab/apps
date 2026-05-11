#!/usr/bin/env python3
"""Re-embed files/gog-shim-reconcile.sh into templates/configmap-sandbox-bridge.yaml.

Olares chart hydration does not support Helm's .Files.Get — the gog-shim script must
live inline under data.gog-shim-reconcile.sh (YAML | block, 4-space indent per line).

Run:
  python3 scripts/embed-gog-shim.py
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = root / "files" / "gog-shim-reconcile.sh"
    cm_path = root / "templates" / "configmap-sandbox-bridge.yaml"
    if not src.is_file():
        print(f"missing {src}", file=sys.stderr)
        return 1
    canon = src.read_text(encoding="utf-8")
    if not canon.endswith("\n"):
        canon += "\n"

    lines = cm_path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = end = None
    for i, ln in enumerate(lines):
        if ln.rstrip() == "  gog-shim-reconcile.sh: |":
            start = i
        if start is not None and i > start and ln.startswith("  # Helper for cold-reset"):
            end = i
            break
    if start is None or end is None:
        print("could not find gog-shim-reconcile.sh block markers", file=sys.stderr)
        return 1

    indented = "".join("    " + (ln if ln.endswith("\n") else ln + "\n") for ln in canon.splitlines(True))
    new_block = "  gog-shim-reconcile.sh: |\n" + indented
    out = "".join(lines[:start]) + new_block + "".join(lines[end:])
    cm_path.write_text(out, encoding="utf-8")
    print(f"updated {cm_path} from {src} ({len(canon.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
