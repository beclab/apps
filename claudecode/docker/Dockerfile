# Claude Code base image for Olares.
#
# Scope: a thin Ubuntu 24.04 base with the minimum toolbox a Claude Code
# terminal user expects (curl / git / less / procps / vim / jq), plus a
# non-root user (UID 1000) so the runtime Pod never needs root.
#
# The claude binary itself is NOT baked into this image. It is installed
# at runtime by the init-install-claude initContainer into the shared
# /opt/data PVC (under ~/.local/bin/claude + ~/.local/share/claude/).
# That keeps base-image size small and lets us bump claude-code versions
# without rebuilding the image.
#
# Build & push:
#   docker buildx build \
#     --platform linux/amd64,linux/arm64 \
#     -t beclab/harveyff-claudecode-base:0.1.0 \
#     --push .
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Core toolbox expected by a Claude Code terminal user. ripgrep is NOT
# installed here: claude ships its own bundled copy and installing the
# system one alongside can confuse its search feature.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        jq \
        less \
        locales \
        procps \
        tzdata \
        unzip \
        vim-tiny \
        xz-utils \
 && rm -rf /var/lib/apt/lists/* \
 && locale-gen C.UTF-8 \
 && (userdel -r ubuntu 2>/dev/null || true) \
 && (groupdel ubuntu 2>/dev/null || true) \
 && useradd --create-home --uid 1000 --shell /bin/bash claude \
 && mkdir -p /opt/data \
 && chown -R 1000:1000 /opt/data

USER 1000:1000
WORKDIR /opt/data

ENV HOME=/opt/data \
    PATH=/opt/data/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    TERM=xterm-256color \
    DISABLE_AUTOUPDATER=1

CMD ["bash"]
