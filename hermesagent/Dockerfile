# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Thin overlay on the official Hermes Agent image.
#
# Purpose: remap the baked `hermes` user/group to UID/GID 1000 so the runtime
# identity matches Olares user-data ownership (appData + Home/External host
# mounts are owned 1000:1000).
#
# Why re-bake instead of just setting HERMES_UID=1000 at runtime:
#   Upstream bakes hermes at UID 10000 and owns the build trees
#   (/opt/hermes/.venv, ui-tui, gateway, node_modules — ~47k files) as 10000.
#   Running as 1000 makes the s6 stage2 hook chown all of them on EVERY boot;
#   on overlayfs that forces a full per-file copy-up and the container hangs
#   during cont-init. Re-owning to 1000 in this layer makes stage2's
#   `venv_owner != hermes_uid` probe false, so its chown is skipped (no runtime
#   copy-up) and the process can write Olares' 1000-owned mounts.
#
# Trade-off: the chown below copies the re-owned files into this new image
# layer, so the result is larger than upstream by ~the size of the build trees.
# Boot is fast; image pull/disk is bigger.
#
# Build (all args optional; defaults shown):
#   docker buildx build \
#     --build-arg HERMES_VERSION=v2026.6.5 \
#     --build-arg TARGET_UID=1000 \
#     --build-arg TARGET_GID=1000 \
#     --platform linux/amd64 \
#     -t harveyff/hermes-agent:v2026.6.5-uid1000 --push .
#
# Upgrades: just pass a newer --build-arg HERMES_VERSION and rebuild.
# ---------------------------------------------------------------------------

# Global ARG consumed by FROM. Must be declared before the first FROM.
ARG HERMES_VERSION=v2026.6.5
FROM nousresearch/hermes-agent:${HERMES_VERSION}

# Re-declare after FROM to make these usable inside RUN below.
ARG TARGET_UID=1000
ARG TARGET_GID=1000

USER root

RUN set -eu; \
    # Capture the upstream-baked UID/GID instead of hardcoding 10000, so the
    # sweep still works if upstream ever changes its default.
    OLD_UID="$(id -u hermes)"; \
    OLD_GID="$(id -g hermes)"; \
    if [ "$OLD_UID" != "$TARGET_UID" ] || [ "$OLD_GID" != "$TARGET_GID" ]; then \
        groupmod -g "$TARGET_GID" hermes; \
        usermod -u "$TARGET_UID" -g "$TARGET_GID" hermes; \
        # usermod -u only re-owns the home dir; re-own everything the upstream
        # build left at the old UID/GID under the install dir in one sweep.
        # (/opt/data is a runtime hostPath mount + declared VOLUME, so skip it.)
        # -h so symlinks themselves are re-owned (chown without -h dereferences
        # and would leave the link node still owned by the old UID, e.g.
        # node_modules/.bin/* shims). It behaves as a normal chown on real files.
        find /opt/hermes -xdev \( -uid "$OLD_UID" -o -gid "$OLD_GID" \) \
            -exec chown -h "$TARGET_UID:$TARGET_GID" {} +; \
        # Fail the build if anything is still owned by the old identity.
        remaining="$(find /opt/hermes -xdev \( -uid "$OLD_UID" -o -gid "$OLD_GID" \) | head -n1)"; \
        [ -z "$remaining" ] || { echo "ERROR: still owned by $OLD_UID:$OLD_GID: $remaining"; exit 1; }; \
    fi

# Identity (now TARGET_UID:TARGET_GID), ENTRYPOINT (/init + main-wrapper) and
# CMD are inherited from the base image — no other behavior changes.
