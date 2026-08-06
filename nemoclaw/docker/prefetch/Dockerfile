# Nemoclaw init-prefetch image — contents under /prefetch/ are copied at pod start to
# /workspace/.nemoclaw-prefetch/ on the nemoclaw workspace PVC (see deployment init-prefetch).
# skill-env then installs each known artifact from /workspace/.nemoclaw-prefetch/ into
# the sandbox. Per-arch ELF/toolchain (micro/rg/fd/go/olares-cli/homebrew) — build one
# image per platform, then publish a multi-arch manifest under a single tag.
#
# Build amd64 (from repo copy with amd ARG defaults below):
#   docker build --platform linux/amd64 \
#     -t beclab/harveyff-nemoclaw-prefetch:2026.5.10-olares-cli-amd \
#     -f docker/prefetch/Dockerfile docker/prefetch
# Build arm64 (use arm ARGs — see Desktop/log Dockerfile or swap MICRO_ARCH/RG_TRIPLE/…):
#   docker build --platform linux/arm64 \
#     -t beclab/harveyff-nemoclaw-prefetch:2026.5.10-olares-cli-arm \
#     -f docker/prefetch/Dockerfile docker/prefetch
# Publish manifest (chart pins the unified tag without -amd/-arm suffix):
#   docker buildx imagetools create -t beclab/harveyff-nemoclaw-prefetch:2026.5.10-olares-cli \
#     beclab/harveyff-nemoclaw-prefetch:2026.5.10-olares-cli-amd \
#     beclab/harveyff-nemoclaw-prefetch:2026.5.10-olares-cli-arm
#
# Image ref is pinned in templates/deployment.yaml (init-prefetch). Rebuild, push manifest, bump tag there.

# Versions for the static-binary fetch stage
ARG MICRO_VERSION=2.0.13
ARG MICRO_ARCH=linux64-static
ARG RG_VERSION=14.1.1
ARG RG_TRIPLE=x86_64-unknown-linux-musl
ARG FD_VERSION=10.2.0
ARG FD_TRIPLE=x86_64-unknown-linux-musl
# Go toolchain. linux-amd64 = glibc build from go.dev (sandbox base is
# debian-bookworm-slim / glibc). Bump GO_VERSION when you want a newer
# toolchain; the image gets rebuilt and the tag bumped in deployment.yaml
# init-prefetch.
ARG GO_VERSION=1.23.4
ARG GO_ARCH=linux-amd64
# Olares CLI. Single-binary tarball published on cdn.olares.com; the
# tarball contains a top-level `olares-cli` ELF. skill-env then installs
# this binary into the sandbox at /usr/local/bin/olares-cli so `olares`
# workflows inside the assistant can call it directly.
ARG OLARES_CLI_URL=https://cdn.olares.com/olares-cli-v1.12.7-20260510_linux_amd64.8705e94.tar.gz
ARG OLARES_CLI_VERSION=1.12.7-20260510-8705e94

# ----------------------------------------------------------------------------
# Stage 1: static binaries (busybox/micro/rg/fd) — unchanged from prior image.
# ----------------------------------------------------------------------------
FROM alpine:3.20 AS unpack
ARG MICRO_VERSION
ARG MICRO_ARCH
ARG RG_VERSION
ARG RG_TRIPLE
ARG FD_VERSION
ARG FD_TRIPLE
ARG GO_VERSION
ARG GO_ARCH
ARG OLARES_CLI_URL
ARG OLARES_CLI_VERSION
RUN apk add --no-cache curl ca-certificates tar gzip \
  && mkdir -p /prefetch \
  # busybox provides static `vi` (skill-env wraps it with a 2-line shim).
  && install -m0755 /bin/busybox /prefetch/busybox \
  # micro editor.
  && curl -fsSL -o /tmp/micro.tgz \
       "https://github.com/zyedidia/micro/releases/download/v${MICRO_VERSION}/micro-${MICRO_VERSION}-${MICRO_ARCH}.tar.gz" \
  && tar -xzf /tmp/micro.tgz -C /tmp \
  && m=$(find /tmp -maxdepth 4 -type f -name micro 2>/dev/null | head -1) \
  && test -n "$m" \
  && install -m0755 "$m" /prefetch/micro \
  && test -x /prefetch/micro \
  # ripgrep.
  && curl -fsSL -o /tmp/rg.tgz \
       "https://github.com/BurntSushi/ripgrep/releases/download/${RG_VERSION}/ripgrep-${RG_VERSION}-${RG_TRIPLE}.tar.gz" \
  && tar -xzf /tmp/rg.tgz -C /tmp \
  && rg=$(find /tmp -maxdepth 4 -type f -name rg 2>/dev/null | head -1) \
  && test -n "$rg" \
  && install -m0755 "$rg" /prefetch/rg \
  && test -x /prefetch/rg \
  # fd.
  && curl -fsSL -o /tmp/fd.tgz \
       "https://github.com/sharkdp/fd/releases/download/v${FD_VERSION}/fd-v${FD_VERSION}-${FD_TRIPLE}.tar.gz" \
  && tar -xzf /tmp/fd.tgz -C /tmp \
  && fd=$(find /tmp -maxdepth 4 -type f -name fd 2>/dev/null | head -1) \
  && test -n "$fd" \
  && install -m0755 "$fd" /prefetch/fd \
  && test -x /prefetch/fd \
  # Go toolchain. Download the official tarball from go.dev, verify the `go`
  # binary is present, then repackage as /prefetch/go.tar.gz so skill-env can
  # stream-install via `tar -xzf - -C /sandbox/.local` in one kubectl-exec hop.
  # We keep the original layout (top-level `go/` dir containing bin/src/pkg),
  # so `GOROOT=/sandbox/.local/go` and `PATH=$GOROOT/bin:...` just work.
  && curl -fsSL -o /tmp/go.tgz \
       "https://go.dev/dl/go${GO_VERSION}.${GO_ARCH}.tar.gz" \
  && mkdir -p /prefetch/_go-stage \
  && tar -xzf /tmp/go.tgz -C /prefetch/_go-stage \
  && test -x /prefetch/_go-stage/go/bin/go \
  && tar -C /prefetch/_go-stage -czf /prefetch/go.tar.gz go \
  && rm -rf /prefetch/_go-stage /tmp/go.tgz \
  && printf "%s\n" "${GO_VERSION}" > /prefetch/go.version \
  && ls -la /prefetch/go.tar.gz /prefetch/go.version \
  # Olares CLI. The CDN tarball unpacks to a single top-level `olares-cli`
  # ELF (no intermediate directory). We `find` for it instead of hard-coding
  # the filename so future URL revs that include a version suffix (e.g.
  # `olares-cli-1.13.0`) keep working without a Dockerfile edit.
  && curl -fsSL -o /tmp/olares-cli.tgz "${OLARES_CLI_URL}" \
  && mkdir -p /prefetch/_olares-stage \
  && tar -xzf /tmp/olares-cli.tgz -C /prefetch/_olares-stage \
  && _cli=$(find /prefetch/_olares-stage -maxdepth 4 -type f \( -name 'olares-cli' -o -name 'olares-cli-*' \) 2>/dev/null | head -1) \
  && test -n "$_cli" \
  && install -m0755 "$_cli" /prefetch/olares-cli \
  && test -x /prefetch/olares-cli \
  && printf "%s\n" "${OLARES_CLI_VERSION}" > /prefetch/olares-cli.version \
  && rm -rf /prefetch/_olares-stage /tmp/olares-cli.tgz \
  && ls -la /prefetch/olares-cli /prefetch/olares-cli.version

# ----------------------------------------------------------------------------
# Stage 2: Homebrew tree with portable-ruby pre-vendored.
#
# brew refuses to run as uid 0 (security check is in Library/Homebrew/utils/permissions.rb
# and not configurable), so we add a non-root `brewuser` to the build context. This stage
# clones the latest Homebrew core repo (shallow) and runs `brew vendor-install ruby`,
# which lands a portable-ruby-X.Y.Z/ tree under Library/Homebrew/vendor/portable-ruby/
# plus a `current` symlink. Both are required for any source-build formula in the
# sandbox (the actual gog binary is built separately in Stage 3, so the sandbox only
# uses Homebrew for binary maintenance — ruby satisfies brew's own runtime needs).
#
# The whole ~120MB Homebrew tree is then tar+gzip'd into a single artifact so the
# bridge can stream it into the sandbox in one kubectl exec hop instead of N kubectl cp.
# ----------------------------------------------------------------------------
FROM debian:bookworm-slim AS brewbuilder
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
       git curl ca-certificates procps file coreutils tar gzip \
  && rm -rf /var/lib/apt/lists/*
RUN useradd -ms /bin/bash brewuser
USER brewuser
WORKDIR /home/brewuser
ENV HOMEBREW_NO_AUTO_UPDATE=1 \
    HOMEBREW_NO_ANALYTICS=1 \
    HOMEBREW_NO_INSTALL_FROM_API=1 \
    HOMEBREW_NO_ENV_HINTS=1 \
    PATH=/home/brewuser/.linuxbrew/Homebrew/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
RUN git clone --depth=1 https://github.com/Homebrew/brew.git .linuxbrew/Homebrew \
  && /home/brewuser/.linuxbrew/Homebrew/bin/brew vendor-install ruby \
  && ls /home/brewuser/.linuxbrew/Homebrew/Library/Homebrew/vendor/portable-ruby/current/bin/ruby
USER root
RUN cd /home/brewuser/.linuxbrew \
  && tar -czf /tmp/homebrew.tar.gz Homebrew \
  && ls -la /tmp/homebrew.tar.gz \
  && du -sh /tmp/homebrew.tar.gz

# ----------------------------------------------------------------------------
# Stage 3: assemble the prefetch image. busybox final stage so the chart's
# `sh -c` init-prefetch args (cp/chmod/ls) work without needing a bigger base.
# ----------------------------------------------------------------------------
FROM busybox:1.36
COPY --from=unpack       /prefetch              /prefetch
COPY --from=brewbuilder  /tmp/homebrew.tar.gz   /prefetch/homebrew.tar.gz
RUN ls -la /prefetch/
