# LLMFit 1.1.16 Olares image

This directory contains the Dockerfile and source patch used for the image in this chart, so market reviewers do not need access to a separate fork to inspect the changes.

- Upstream: https://github.com/AlexsJones/llmfit
- Upstream tag: v1.1.16
- Upstream commit: `2ac77f5e0d13221c7e2a2414769fe62f660d225c`
- Tested patched source: `ca68e8f396a69ca716a896d88a4e9305cfdc95ff`
- Source image: `ghcr.io/harveyff/llmfit:1.1.16-olares`
- Chart image: `beclab/harveyff-llmfit:1.1.16-olares`
- Successful native amd64/arm64 build: https://github.com/harveyff/llmfit/actions/runs/36378010987

## Changes

`olares-api.patch` preserves the previous image's `LLMFIT_ALLOW_REMOTE` opt-in for planning, downloads, and download status. Loopback is always allowed; non-loopback requests require `1`, `true`, or `yes` (case-insensitive). The chart already sets this variable and retains its private Olares entrance.

The patch includes access-gate tests and replaces an upstream test's exact JSON floating-point comparison with a tolerance. It does not change production sizing calculations. The Dockerfile runs all 14 HTTP API unit tests before building the release binary, embeds the Web UI, and runs as UID 1000.

## Build from upstream

Run these commands in a POSIX shell. Set `BUILD_FILES` to the absolute path of this directory in your chart checkout. Use a new destination directory for the upstream clone.

```sh
BUILD_FILES=/absolute/path/to/terminus-apps/llmfit/build
git clone --branch v1.1.16 --depth 1 https://github.com/AlexsJones/llmfit.git llmfit-source
cd llmfit-source
test "$(git rev-parse HEAD)" = 2ac77f5e0d13221c7e2a2414769fe62f660d225c
git apply --check "$BUILD_FILES/olares-api.patch"
git apply "$BUILD_FILES/olares-api.patch"
cp "$BUILD_FILES/Dockerfile" Dockerfile
cp "$BUILD_FILES/.dockerignore" .dockerignore
docker build -t llmfit:1.1.16-olares .
docker run --rm llmfit:1.1.16-olares --version
```

The build context must be the patched upstream source, not the chart directory. To publish both architectures, run the same Dockerfile on native amd64 and arm64 builders, push separate architecture tags to your registry, then combine them with `docker buildx imagetools create`. Native builders avoid the upstream Rust/QEMU failures documented in the Dockerfile. Do not overwrite the tested release tag for a changed build.

The recipe reproduces the source and build steps, not a bit-identical image: base image tags and OS package repositories are not digest-pinned. This build directory is excluded from Helm packaging and has no effect on deployed resources.
