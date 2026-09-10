# Open Design on Olares, based on upstream open-design-v0.22.1 deploy/Dockerfile.
# Build context: this chart directory; source is fetched in a separate stage.
# Adds pinned OpenCode and request-scoped support for user-configured providers.
# docker buildx build --platform linux/amd64,linux/arm64 -t <registry>/opendesign:<new-tag> --load .
# Smoke-test both architectures before pushing the new tag.

ARG NODE_IMAGE=docker.io/library/node:24-alpine
ARG RUNTIME_IMAGE=docker.io/library/node:24-alpine

ARG OD_GIT_REF=open-design-v0.22.1

# Source files are architecture-independent; fetch once on the build host.
FROM --platform=$BUILDPLATFORM ${NODE_IMAGE} AS source
ARG OD_GIT_REF
RUN apk add --no-cache git
WORKDIR /src
RUN git clone --depth 1 --branch "${OD_GIT_REF}" https://github.com/nexu-io/open-design.git .

FROM ${NODE_IMAGE} AS build

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG http_proxy
ARG https_proxy
ARG no_proxy
ARG NO_PROXY

ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV http_proxy=${http_proxy}
ENV https_proxy=${https_proxy}
ENV no_proxy=${no_proxy}
ENV NO_PROXY=${NO_PROXY}
ENV CI=true

RUN apk add --no-cache python3 make g++

WORKDIR /app
COPY --from=source /src/package.json /src/pnpm-lock.yaml /src/pnpm-workspace.yaml ./
COPY --from=source /src/scripts/postinstall.mjs ./scripts/postinstall.mjs
COPY --from=source /src/packages ./packages
COPY --from=source /src/tools ./tools
COPY --from=source /src/apps/daemon/package.json ./apps/daemon/package.json
COPY --from=source /src/apps/web/package.json ./apps/web/package.json
COPY --from=source /src/e2e/package.json ./e2e/package.json
# This Olares app does not request a GPU; keep ONNX CPU binaries and skip
# downloading the optional CUDA provider during dependency installation.
RUN corepack enable && \
    corepack prepare pnpm@10.33.2 --activate && \
    ONNXRUNTIME_NODE_INSTALL_CUDA=skip pnpm install --frozen-lockfile

COPY --from=source /src/apps ./apps
COPY patches/apply-provider-hosts.mjs /tmp/apply-provider-hosts.mjs
RUN node /tmp/apply-provider-hosts.mjs /app
RUN pnpm --filter @open-design/daemon build && \
    pnpm --filter @open-design/web build && \
    pnpm --filter @open-design/daemon deploy --legacy --prod /app/deploy/daemon && \
    pnpm store prune && \
    rm -rf \
      /root/.cache \
      /root/.local/share/pnpm/store \
      /app/deploy/daemon/node_modules/.cache \
      /app/deploy/daemon/node_modules/@types \
      /app/deploy/daemon/node_modules/.pnpm/@types+* \
      /app/deploy/daemon/node_modules/.pnpm/better-sqlite3@*/node_modules/better-sqlite3/deps \
      /app/deploy/daemon/node_modules/.pnpm/better-sqlite3@*/node_modules/better-sqlite3/src && \
    find /app/deploy/daemon/node_modules -type d \( \
      -name test -o \
      -name tests -o \
      -name "__tests__" -o \
      -name docs -o \
      -name doc -o \
      -name example -o \
      -name examples -o \
      -name ".github" \
    \) -prune -exec rm -rf '{}' + && \
    find /app/deploy/daemon/node_modules -type f \( \
      -name "*.md" -o \
      -name "*.markdown" -o \
      -name "*.d.ts" -o \
      -name "*.d.cts" -o \
      -name "*.d.mts" -o \
      -name "*.map" -o \
      -name "*.tsbuildinfo" -o \
      -name "binding.gyp" \
    \) -delete

# Stage-2 assets — copied into the build stage so the runtime stage
# can pull them via --from=build instead of reaching back into the
# build context.  This lets the Dockerfile work when the build context
# differs from the repo root (Railway, CI runners with a subdirectory
# context, etc.).
COPY --from=source /src/skills ./skills
COPY --from=source /src/design-systems ./design-systems
COPY --from=source /src/craft ./craft
COPY --from=source /src/prompt-templates ./prompt-templates
COPY --from=source /src/assets ./assets
# `data/plugin-previews/manifest.json` is committed by the bake pipeline and is
# what `resolvePluginPreviewsDir()` looks for at runtime. Without it in the
# image, `loadManifest()` returns `{}` and every plugin silently falls back to
# the live-iframe preview path — the exact cost the bakes exist to avoid.
COPY --from=source /src/data ./data
COPY --from=source /src/plugins/_official ./plugins/_official

FROM ${RUNTIME_IMAGE}

# node:24-alpine already supplies node with UID/GID 1000.
ARG OPENCODE_VERSION=1.18.30
RUN apk add --no-cache tini poppler-utils bash git && \
    test "$(id -u node)" = 1000 && test "$(id -g node)" = 1000 && \
    npm install --global --prefix /opt/opencode "opencode-ai@${OPENCODE_VERSION}" && \
    npm cache clean --force

# New npm versions may skip dependency lifecycle scripts. OpenCode ships a
# placeholder until its pinned postinstall selects and verifies the native binary.
RUN node /opt/opencode/lib/node_modules/opencode-ai/postinstall.mjs

WORKDIR /app
COPY --from=build --chown=node:node /app/deploy/daemon ./apps/daemon
COPY --from=build --chown=node:node /app/apps/web/out ./apps/web/out
COPY --from=build --chown=node:node /app/skills ./skills
COPY --from=build --chown=node:node /app/design-systems ./design-systems
COPY --from=build --chown=node:node /app/craft ./craft
COPY --from=build --chown=node:node /app/prompt-templates ./prompt-templates
COPY --from=build --chown=node:node /app/data ./data
COPY --from=build --chown=node:node /app/assets/frames ./assets/frames
COPY --from=build --chown=node:node /app/assets/community-pets ./assets/community-pets
# Plan §3.J4 / spec §23.3.5 — bundled atom plugins registered on
# daemon boot. The directory contains `plugins/_official/atoms/<atom>/`
# pairs (SKILL.md + open-design.json); registerBundledPlugins() walks
# it on startup so the container ships with first-party atoms reachable
# via the same registry path third-party plugins use.
COPY --from=build --chown=node:node /app/plugins/_official ./plugins/_official

RUN mkdir -p /app/.od && \
    chown -R node:node /app

ENV NODE_ENV=production
ENV NODE_OPTIONS=--max-old-space-size=192
ENV OD_BIND_HOST=0.0.0.0
ENV OD_PORT=7456

EXPOSE 7456

ENV HOME=/app/.od
ENV PATH=/opt/opencode/bin:$PATH
ENV OD_DATA_DIR=/app/.od

USER node
# Verify the selected native binary works as the actual non-root runtime user.
RUN opencode --version
COPY --chown=node:node patches/provider-hosts.test.mjs /tmp/provider-hosts.test.mjs
RUN node --test /tmp/provider-hosts.test.mjs
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "apps/daemon/dist/cli.js", "--no-open"]
