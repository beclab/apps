 Pool CLI base image for Olares (aligned with claudecode toolbox).
#
# Scope: Ubuntu 24.04 with common CLI deps, language runtimes / build
# toolchains (Python / Node / Go / Rust / Java / Ruby / PHP / Lua),
# database clients, and headers for typical agent-driven dev work.
# The pool binary is baked in at /usr/local/bin/pool.
#
# Search/fs helpers included: ripgrep (rg), fd-find (fd), fzf, bat (batcat).
#
# Build & push:
#   docker buildx build \
#     --platform linux/amd64,linux/arm64 \
#     -t beclab/harveyff-pool:v1.0.6 \
#     --push .
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        git-lfs \
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
        nodejs \
        npm \
        golang-go \
        rustc \
        cargo \
        ruby \
        ruby-dev \
        ruby-bundler \
        openjdk-21-jdk-headless \
        maven \
        gradle \
        php8.3-cli \
        php8.3-curl \
        php8.3-intl \
        php8.3-mbstring \
        php8.3-mysql \
        php8.3-pgsql \
        php8.3-sqlite3 \
        php8.3-xml \
        php8.3-zip \
        composer \
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
        netcat-openbsd \
        socat \
        xmlstarlet \
        shellcheck \
        graphviz \
        moreutils \
        ripgrep \
        fd-find \
        fzf \
        bat \
 && ln -sfn "/usr/lib/jvm/java-21-openjdk-$(dpkg --print-architecture)" /usr/lib/jvm/java-21-openjdk-current \
 && ln -sf "$(command -v fdfind)" /usr/local/bin/fd \
 && ln -sf "$(command -v batcat)" /usr/local/bin/bat \
 && rm -rf /var/lib/apt/lists/* \
 && locale-gen C.UTF-8 \
 && (userdel -r ubuntu 2>/dev/null || true) \
 && (groupdel ubuntu 2>/dev/null || true) \
 && useradd --create-home --uid 1000 --shell /bin/bash pool \
 && mkdir -p /opt/data/work /opt/data/.config/poolside /opt/data/.local/bin \
 && chown -R 1000:1000 /opt/data

ARG POOL_VERSION=v1.0.4
ARG TARGETARCH=amd64

RUN set -eux; \
    base="https://downloads.poolside.ai/pool"; \
    version="${POOL_VERSION}"; \
    if [ "${version}" = "latest" ]; then \
        version="$(curl -fsSL "${base}/pool-latest-version.txt" | tr -d '[:space:]')"; \
    elif [ "${version#v}" = "${version}" ]; then \
        version="v${version}"; \
    fi; \
    archive="pool-linux-${TARGETARCH}.tar.gz"; \
    curl -fsSL -o "/tmp/${archive}" "${base}/${version}/${archive}"; \
    curl -fsSL -o /tmp/checksums.txt "${base}/${version}/checksums.txt"; \
    cd /tmp; \
    grep "${archive}" checksums.txt | sha256sum -c -; \
    tar -xzf "/tmp/${archive}" -C /tmp; \
    install -m 0755 "/tmp/pool-linux-${TARGETARCH}" /usr/local/bin/pool; \
    rm -rf "/tmp/${archive}" /tmp/checksums.txt "/tmp/pool-linux-${TARGETARCH}"

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-current

USER 1000:1000
WORKDIR /opt/data/work

ENV HOME=/opt/data \
    PATH=/opt/data/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    TERM=xterm-256color \
    PIP_BREAK_SYSTEM_PACKAGES=1

CMD ["sleep", "infinity"]
