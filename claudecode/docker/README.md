# claudecode base image

A thin Ubuntu 24.04 base image for the Olares `claudecode` app.

## What it ships

- `ca-certificates`, `curl`, `git`, `jq`, `less`, `procps`, `tzdata`,
  `unzip`, `vim-tiny`, `xz-utils`, `locales` (C.UTF-8 pre-generated).
- A non-root user `claude` (UID 1000) with `HOME=/opt/data` and
  `PATH` prepending `/opt/data/.local/bin`.
- No `claude` binary. The binary is installed at runtime by the
  `init-install-claude` initContainer into the shared PVC so bumping
  claude-code versions does not require rebuilding this image.

## Build & push

```bash
# Single-arch (local dev)
docker build -t beclab/harveyff-claudecode-base:0.1.0 .

# Multi-arch release (recommended, matches chart supportArch)
docker buildx create --use --name claudecode-builder || true
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t beclab/harveyff-claudecode-base:0.1.0 \
  --push .
```

## Bumping the image

When bumping apt dependencies or base Ubuntu:

1. Increment the tag: `0.1.0 -> 0.1.1` (or major if breaking).
2. Update both references in
   `claudecode/templates/deployment.yaml` (initContainer + main container).
3. Bump `version` in `claudecode/Chart.yaml`.

The `claude` binary itself (v2.1.117 etc.) is controlled separately by
`appVersion` in `Chart.yaml` and `metadata.version` /
`spec.versionName` in `OlaresManifest.yaml`; it is pulled fresh by the
init container whenever `$HOME/.install-state/install-complete` is
missing, regardless of base image tag.
