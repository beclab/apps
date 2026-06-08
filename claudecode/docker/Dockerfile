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
#     -t beclab/harveyff-claudecode-base:0.2.0 \
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
 && ln -sfn "/usr/lib/jvm/java-21-openjdk-$(dpkg --print-architecture)" /usr/lib/jvm/java-21-openjdk-current \
 && rm -rf /var/lib/apt/lists/* \
 && locale-gen C.UTF-8 \
 && (userdel -r ubuntu 2>/dev/null || true) \
 && (groupdel ubuntu 2>/dev/null || true) \
 && useradd --create-home --uid 1000 --shell /bin/bash claude \
 && mkdir -p /opt/data \
 && chown -R 1000:1000 /opt/data

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-current

USER 1000:1000
WORKDIR /opt/data

ENV HOME=/opt/data \
    PATH=/opt/data/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    TERM=xterm-256color \
    DISABLE_AUTOUPDATER=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1

CMD ["bash"]
