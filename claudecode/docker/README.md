# claudecode base image

Ubuntu 24.04 base image for the Olares `claudecode` app with common language
runtimes, build toolchains, database clients, and extra dev headers pre-installed.

## What it ships

**Shell / tooling:** `ca-certificates`, `curl`, `wget`, `git`, `git-lfs`,
`openssh-client`, `jq`, `yq` (kislyuk YAML CLI), `less`, `procps`, `tzdata`,
`unzip`, `zip`, `vim-tiny`, `xz-utils`, `pigz`, `file`, `rsync`, `patch`,
`tmux`, `htop`, `dnsutils`, `iproute2`, `netcat-openbsd`, `socat`, `xmlstarlet`,
`shellcheck`, `graphviz`, `moreutils`, `locales` (C.UTF-8 pre-generated).

**Build:** `build-essential`, `pkg-config`, `cmake`, `ninja-build`, `clang`,
`clang-format`, `clang-tidy`, common `-dev` headers (SSL, FFI, zlib, bz2,
readline, sqlite, lzma, xml, xslt, yaml, jpeg, png, **curl**, **ICU**, **LDAP**,
**libpq**, **default-libmysqlclient-dev**), `gettext`, `protobuf-compiler`,
`libprotobuf-dev`, `gfortran`.

**Runtimes (distro):** Python 3 (`python3`, `pip`, `venv`, `pipx`), Node.js +
`npm`, Go (`golang-go`), Rust (`rustc`, `cargo`), Ruby + `bundler`, OpenJDK 21
(headless JDK), `maven`, **Gradle**, PHP 8.3 CLI + extensions (`curl`, `intl`,
`mysql`, `pgsql`, `sqlite3`, `mbstring`, `xml`, `zip`) + `composer`, `lua5.4`,
`sqlite3`, `perl`.

**Database clients:** `postgresql-client`, `default-mysql-client`,
`redis-tools`.

**User:** non-root `claude` (UID 1000), `HOME=/opt/data`, `PATH` prepends
`/opt/data/.local/bin`. `JAVA_HOME` points at OpenJDK 21.
`PIP_BREAK_SYSTEM_PACKAGES=1` so `pip install` into the distro Python is
allowed when needed.

**Olares integration (baked at build time):** `olares-cli` at `/usr/local/bin/olares-cli`
(vendor binary from `@olares/cli`, same as clawdbot). Olares skill pack under
`/skills-staging`; `init-skills` flattens into `$HOME/.claude/skills` on the PVC
(Claude Code user skills; agent flag `claude-code` via `npx skills add`).

**Not included:** the `claude` CLI binary (installed at runtime by
`init-install-claude` into the shared PVC). `ripgrep` is omitted on purpose:
Claude Code bundles its own.

## Build & push

```bash
# Single-arch (local dev)
docker build -t beclab/harveyff-claudecode-base:0.2.0 .

# Multi-arch release (recommended, matches chart supportArch)
docker buildx create --use --name claudecode-builder || true
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t beclab/harveyff-claudecode-base:0.5.3 \
  --push .
```

## Bumping the image

When bumping apt dependencies or base Ubuntu:

1. Increment the tag (e.g. `0.5.2 -> 0.5.3`).
2. Update both references in `claudecode/templates/deployment.yaml`
   (initContainer + main container).
3. Bump `version` in `claudecode/Chart.yaml` and `metadata.version` in
   `OlaresManifest.yaml`.

The `claude` binary itself (v2.1.117 etc.) is controlled separately by
`appVersion` in `Chart.yaml` and `metadata.version` / `spec.versionName` in
`OlaresManifest.yaml`; it is pulled fresh by the init container whenever
`$HOME/.install-state/install-complete` is missing, regardless of base image tag.
