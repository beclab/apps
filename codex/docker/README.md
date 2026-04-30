# codex base image

A thin Ubuntu 24.04 base image for the Olares `codex` app.

## What it ships

- `ca-certificates`, `curl`, `git`, `jq`, `less`, `procps`, `tzdata`,
  `unzip`, `vim-tiny`, `xz-utils`, `locales` (C.UTF-8 pre-generated).
- A non-root user `codex` (UID 1000) with `HOME=/opt/data` and
  `PATH` prepending `/opt/data/.local/bin`.
- No `codex` binary. The binary is installed at runtime by the
  `init-install-codex` initContainer into the shared PVC so bumping
  codex versions does not require rebuilding this image.

## Build & push

```bash
# Single-arch (local dev)
docker build -t beclab/harveyff-codex-base:0.1.0 .

# Multi-arch release (recommended, matches chart supportArch)
docker buildx create --use --name codex-builder || true
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t beclab/harveyff-codex-base:0.1.0 \
  --push .
```

## Bumping the image

When bumping apt dependencies or base Ubuntu:

1. Increment the tag: `0.1.0 -> 0.1.1` (or major if breaking).
2. Update both references in
   `codex/templates/deployment.yaml` (initContainer + main container).
3. Bump `version` in `codex/Chart.yaml`.

The `codex` binary itself (rust-v0.125.0 etc.) is controlled separately
by `appVersion` in `Chart.yaml` and `metadata.version` /
`spec.versionName` in `OlaresManifest.yaml`; it is pulled fresh from
the matching GitHub Release tarball whenever
`$HOME/.install-state/codex-<version>` is missing, regardless of base
image tag.
