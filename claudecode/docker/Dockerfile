# Claude Code base image for Olares.
#
# Scope: Ubuntu 24.04 with common CLI deps, language runtimes / build
# toolchains (Python / Node / Go / Rust / Java / Ruby / PHP / Lua),
# database clients, protobuf, Gradle, and extra -dev headers for
# typical agent-driven dev work. Non-root user (UID 1000) runs the Pod.
#
# The claude binary itself is NOT baked into this image. It is installed
# at runtime by the init-install-claude initContainer into the shared
# /opt/data PVC (under ~/.local/bin/claude + ~/.local/share/claude/).
#
# ripgrep is NOT installed here: claude ships its own bundled copy and
# installing the system one alongside can confuse its search feature.
#
# Build & push:
#   docker buildx build \
#     --platform linux/amd64,linux/arm64 \
#     -t beclab/harveyff-claudecode-base:0.5.9 \
#     --push .
# syntax=docker/dockerfile:1.7

# Debian/Ubuntu mirrors can briefly serve InRelease metadata that is "not valid yet"
# during sync; relax validity checks and retry update (see apt exit 100 on bookworm-security).
# ---- Stage 1: olares-cli binary + Olares skills (Claude Code layout) ----
# @olares/cli postinstall downloads the Go binary; copy vendor binary (not JS
# wrapper) so the full verb set and its matching embedded skill suite are available.
FROM node:24-bookworm-slim AS olares-assets
ARG OLARES_CLI_NPM_VERSION=1.12.7-cli.10

RUN set -eux; \
    for i in 1 2 3 4 5; do \
      apt-get -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false update && break; \
      sleep $((i * 5)); \
    done; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      git ca-certificates; \
    rm -rf /var/lib/apt/lists/*

RUN npm install -g --allow-scripts=@olares/cli @olares/cli@${OLARES_CLI_NPM_VERSION} \
 && install -D "$(npm root -g)/@olares/cli/vendor/olares-cli" /out/bin/olares-cli \
 && mkdir -p /out/share/olares-cli \
 && cp "$(npm root -g)/@olares/cli/package.json" "$(npm root -g)/@olares/cli/checksums.txt" /out/share/olares-cli/ \
 && /out/bin/olares-cli --version

WORKDIR /skills-build
RUN HOME=/skills-build /out/bin/olares-cli skills install \
 && test -f /skills-build/.agents/skills/olares-shared/SKILL.md \
 && mkdir -p /out/skills \
 && cp -a /skills-build/.agents/skills/. /out/skills/ \
 && ls -la /out/skills

# ---- Stage 2: Ubuntu runtime and language toolchains ----
FROM ubuntu:24.04

# Keep PHP and its ABI-coupled extensions on the same Ubuntu security revision.
ARG PHP_PACKAGE_VERSION=8.3.6-0ubuntu0.24.04.13
ARG COMPOSER_VERSION=2.10.3
ARG COMPOSER_SHA256=7a2d379d5b8ffdaa028580ef26494c36d2feef4b178d3dd1473a4dbc5e17c8d6

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN set -eux; \
    for i in 1 2 3 4 5; do \
      apt-get -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false update && break; \
      sleep $((i * 5)); \
    done; \
    apt-get install -y --no-install-recommends ca-certificates curl \
 && mkdir -p -m 755 /etc/apt/keyrings \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
 && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
 && apt-get -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false update \
 && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        git-lfs \
        gh \
        openssh-client \
        jq \
        yq \
        less \
        locales \
        procps \
        tzdata \
        unzip \
        zip \
        vim-tiny \
        wget \
        xz-utils \
        pigz \
        file \
        rsync \
        patch \
        pkg-config \
        build-essential \
        cmake \
        ninja-build \
        clang \
        clang-format \
        clang-tidy \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        pipx \
        golang-go \
        rustc \
        cargo \
        ruby \
        ruby-dev \
        ruby-bundler \
        openjdk-21-jdk-headless \
        maven \
        gradle \
        "php8.3-cli=${PHP_PACKAGE_VERSION}" \
        "php8.3-curl=${PHP_PACKAGE_VERSION}" \
        "php8.3-intl=${PHP_PACKAGE_VERSION}" \
        "php8.3-mbstring=${PHP_PACKAGE_VERSION}" \
        "php8.3-mysql=${PHP_PACKAGE_VERSION}" \
        "php8.3-pgsql=${PHP_PACKAGE_VERSION}" \
        "php8.3-sqlite3=${PHP_PACKAGE_VERSION}" \
        "php8.3-xml=${PHP_PACKAGE_VERSION}" \
        "php8.3-zip=${PHP_PACKAGE_VERSION}" \
        lua5.4 \
        sqlite3 \
        gfortran \
        postgresql-client \
        default-mysql-client \
        redis-tools \
        protobuf-compiler \
        libprotobuf-dev \
        libssl-dev \
        libffi-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        liblzma-dev \
        libxml2-dev \
        libxslt1-dev \
        libyaml-dev \
        libjpeg-turbo8-dev \
        libpng-dev \
        libcurl4-openssl-dev \
        libicu-dev \
        libldap2-dev \
        libpq-dev \
        default-libmysqlclient-dev \
        gettext \
        perl \
        tmux \
        htop \
        dnsutils \
        iproute2 \
        iputils-ping \
        lsof \
        net-tools \
        traceroute \
        whois \
        inetutils-telnet \
        tcpdump \
        netcat-openbsd \
        socat \
        xmlstarlet \
        shellcheck \
        graphviz \
        moreutils \
        tree \
        nano \
        lrzsz \
        zstd \
        bzip2 \
        bash-completion \
        man-db \
        strace \
        ncdu \
        parallel \
        time \
        gdb \
        ltrace \
        valgrind \
        mtr-tiny \
        expect \
        aria2 \
        httpie \
        certbot \
        python3-certbot \
 && ln -sfn "/usr/lib/jvm/java-21-openjdk-$(dpkg --print-architecture)" /usr/lib/jvm/java-21-openjdk-current \
 && rm -rf /var/lib/apt/lists/* \
 && locale-gen C.UTF-8 \
 && (userdel -r ubuntu 2>/dev/null || true) \
 && (groupdel ubuntu 2>/dev/null || true) \
 && useradd --create-home --uid 1000 --shell /bin/bash claude \
 && mkdir -p /opt/data \
 && chown -R 1000:1000 /opt/data

# Composer is pinned to the upstream stable PHAR and verified before execution.
RUN curl -fsSL --retry 3 "https://getcomposer.org/download/${COMPOSER_VERSION}/composer.phar" \
      -o /usr/local/bin/composer \
 && echo "${COMPOSER_SHA256}  /usr/local/bin/composer" | sha256sum -c - \
 && chmod 755 /usr/local/bin/composer \
 && php --version \
 && composer --no-ansi --version

# Node 20 LTS via NodeSource. Ubuntu 24.04's nodejs is v18.19.1, which is
# too old for some CLIs (e.g. @larksuite/cli needs node >= 20.12.0). This
# ships node + npm under /usr/local, replacing the distro packages above.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/* \
 && node --version && npm --version

COPY --from=olares-assets /out/bin/olares-cli /usr/local/bin/olares-cli
COPY --from=olares-assets /out/share/olares-cli /usr/local/share/olares-cli
RUN chmod 755 /usr/local/bin/olares-cli \
 && /usr/local/bin/olares-cli --version

# Baked skills; init-skills copies into $HOME/.claude/skills on the PVC.
COPY --from=olares-assets /out/skills /skills-staging
RUN chown -R 1000:1000 /skills-staging

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-current

USER 1000:1000
WORKDIR /opt/data

ENV HOME=/opt/data \
    PATH=/opt/data/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    TERM=xterm-256color \
    DISABLE_AUTOUPDATER=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    NPM_CONFIG_PREFIX=/opt/data/.local \
    NPM_CONFIG_CACHE=/opt/data/.npm

CMD ["bash"]
