# codex base image

Ubuntu 24.04 base image for the Olares `codex` app with common language
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
`mysql`, `pgsql`, `sqlite3`, `mbstring`, `xml`, `zip`) + Composer 2.10.3, `lua5.4`,
`sqlite3`, `perl`.

**Database clients:** `postgresql-client`, `default-mysql-client`,
`redis-tools`.

**User:** non-root `codex` (UID 1000), `HOME=/opt/data`, `PATH` prepends
`/opt/data/.local/bin`. `JAVA_HOME` points at OpenJDK 21.
`PIP_BREAK_SYSTEM_PACKAGES=1` so `pip install` into the distro Python is
allowed when needed.

**Olares integration (baked at build time):** `olares-cli` at `/usr/local/bin/olares-cli`
(vendor binary from `@olares/cli`, same as claudecode). Olares skill pack under
`/skills-staging`; `init-skills` flattens into `$HOME/.codex/skills` on the PVC
(Codex user skills via `.agents/skills` at build time; `init-skills` flattens into
`$CODEX_HOME/skills` on the PVC; exported offline by `olares-cli skills install`).

**Not included:** the `codex` CLI standalone package (installed at runtime by
`init-install-codex` via OpenAI's official `install.sh` into
`/opt/data/.local/bin` and `~/.codex/packages/standalone`). `ripgrep` is
omitted from apt on purpose: Codex bundles its own.

## Build & push

```bash
# Single-arch (local dev)
docker build -t beclab/harveyff-codex-base:0.5.10 .

# Multi-arch release (recommended, matches chart supportArch)
docker buildx create --use --name codex-builder || true
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t beclab/harveyff-codex-base:0.5.10 \
  --push .
```

## Bumping the image

When bumping apt dependencies or base Ubuntu:

1. Increment the tag (e.g. `0.5.9 -> 0.5.10`).
2. Update all references in `codex/templates/deployment.yaml`
   (init-skills + init-install-codex + main container).
3. Bump `version` in `codex/Chart.yaml` and `metadata.version` in
   `OlaresManifest.yaml`.

The Codex standalone package is controlled separately by `appVersion` in
`Chart.yaml` and `spec.versionName` in `OlaresManifest.yaml`.
`metadata.version` identifies the Chart revision. `init-install-codex` runs
`https://chatgpt.com/codex/install.sh --release <appVersion>` whenever
`$HOME/.install-state/codex-standalone-<version>-<target>` is missing or the
install is binary-only (no `~/.codex/packages/standalone/current`).

## Dependency refresh (2026-10-23)

- `@olares/cli` is fixed at `1.12.7-cli.10`; the native vendor binary is copied and its version command must succeed during the build.
- PHP CLI and all listed PHP extensions use Ubuntu package revision `8.3.6-0ubuntu0.24.04.13`. This includes Ubuntu's security backports; `php --version` still reports 8.3.6, so verify the complete version with `dpkg-query`.
- Composer 2.10.3 is downloaded from its fixed upstream release URL and checked against SHA256 `7a2d379d5b8ffdaa028580ef26494c36d2feef4b178d3dd1473a4dbc5e17c8d6` before execution. The older Ubuntu Composer package is no longer installed.
- The base image tag is `0.5.10`. The application binary remains controlled by the Chart's fixed installer version.

Sources: [Olares CLI npm release](https://www.npmjs.com/package/@olares/cli/v/1.12.7-cli.10), [Ubuntu PHP advisory](https://ubuntu.com/security/notices/USN-8948-1), [Composer stable release](https://getcomposer.org/download/).

The native CLI reports base version `1.12.7`; the npm revision is verified by its archive checksum and the installed binary SHA256. Skills are exported offline from that same binary using `olares-cli skills install`.

Workspace backups are keyed by application and Chart revision, so an image-only update makes a new backup while retaining prior archives. npm provenance is available at `/usr/local/share/olares-cli/package.json` and `checksums.txt`.
