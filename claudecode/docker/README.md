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
`mysql`, `pgsql`, `sqlite3`, `mbstring`, `xml`, `zip`) + Composer 2.10.3, `lua5.4`,
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
(Claude Code user skills; exported offline by `olares-cli skills install`).
**`certbot`** (Let's Encrypt) via apt, same role as opencode / clawdbot brew-base.

**Not included:** the `claude` CLI binary (installed at runtime by
`init-install-claude` into the shared PVC). `ripgrep` is omitted on purpose:
Claude Code bundles its own.

## Build & push

```bash
# Single-arch (local dev)
docker build -t beclab/harveyff-claudecode-base:0.5.9 .

# Multi-arch release (recommended, matches chart supportArch)
docker buildx create --use --name claudecode-builder || true
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t beclab/harveyff-claudecode-base:0.5.9 \
  --push .
```

## Bumping the image

When bumping apt dependencies or base Ubuntu:

1. Increment the tag (e.g. `0.5.5 -> 0.5.6`).
2. Update every base-image reference in `claudecode/templates/deployment.yaml`
   (initContainer + main container).
3. Bump `version` in `claudecode/Chart.yaml` and `metadata.version` in
   `OlaresManifest.yaml`.

The `claude` binary version is controlled separately by `appVersion` in
`Chart.yaml` and `spec.versionName` in `OlaresManifest.yaml`. The init container
checks the actual binary even when an installation marker exists.
`metadata.version` identifies the Chart revision.

## Dependency refresh (2026-10-23)

- `@olares/cli` is fixed at `1.12.7-cli.10`; the native vendor binary is copied and its version command must succeed during the build.
- PHP CLI and all listed PHP extensions use Ubuntu package revision `8.3.6-0ubuntu0.24.04.13`. This includes Ubuntu's security backports; `php --version` still reports 8.3.6, so verify the complete version with `dpkg-query`.
- Composer 2.10.3 is downloaded from its fixed upstream release URL and checked against SHA256 `7a2d379d5b8ffdaa028580ef26494c36d2feef4b178d3dd1473a4dbc5e17c8d6` before execution. The older Ubuntu Composer package is no longer installed.
- The base image tag is `0.5.9`. The application binary remains controlled by the Chart's fixed installer version.

Sources: [Olares CLI npm release](https://www.npmjs.com/package/@olares/cli/v/1.12.7-cli.10), [Ubuntu PHP advisory](https://ubuntu.com/security/notices/USN-8948-1), [Composer stable release](https://getcomposer.org/download/).

The native CLI reports base version `1.12.7`; the npm revision is verified by its archive checksum and the installed binary SHA256. Skills are exported offline from that same binary.

Workspace backups are keyed by application and Chart revision, so an image-only update makes a new backup while retaining prior archives. npm provenance is available at `/usr/local/share/olares-cli/package.json` and `checksums.txt`.
