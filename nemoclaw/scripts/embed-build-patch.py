#!/usr/bin/env python3
"""Re-embed files/patch-nemoclaw-dockerfile.py into templates/configmap-build-patch.yaml.

Olares chart hydration does not support Helm's .Files.Get — inline the script under
data.patch-nemoclaw-dockerfile.py (YAML | block, 4-space indent per line).

Run from repo root:
  python3 scripts/embed-build-patch.py
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = root / "files" / "patch-nemoclaw-dockerfile.py"
    cm_path = root / "templates" / "configmap-build-patch.yaml"
    if not src.is_file():
        print(f"missing {src}", file=sys.stderr)
        return 1
    canon = src.read_text(encoding="utf-8")
    if not canon.endswith("\n"):
        canon += "\n"

    header = """# Patches the cloned NemoClaw Dockerfile before `nemoclaw onboard --from`.
# Script is embedded inline (Olares hydration has no Helm .Files.Get).
# Canonical: files/patch-nemoclaw-dockerfile.py — run scripts/embed-build-patch.py after edits.
apiVersion: v1
kind: ConfigMap
metadata:
  name: nemoclaw-build-patch
  namespace: "{{ .Release.Namespace }}"
  labels:
    io.kompose.service: nemoclaw
data:
  patch-nemoclaw-dockerfile.py: |
"""
    indented = "".join("    " + (ln if ln.endswith("\n") else ln + "\n") for ln in canon.splitlines(True))
    cm_path.write_text(header + indented, encoding="utf-8")
    print(f"updated {cm_path} from {src} ({len(canon.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
