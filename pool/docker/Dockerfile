# Security update of the existing Olares toolbox; preserve its toolchain.
ARG BASE_IMAGE=beclab/harveyff-pool@sha256:2ab5c6760325d3f6bb2dbd04d0bbf448f081f71ec10d76346e66d55941dd2200
FROM ${BASE_IMAGE}
USER 0
ARG POOL_VERSION=v1.0.16
ARG TARGETARCH
ARG PHP_MIN_VERSION=8.3.6-0ubuntu0.24.04.13
RUN set -eu; \
    apt-get update; \
    packages="$(dpkg-query -W -f='${binary:Package} ${db:Status-Status}\n' 'php8.3-*' | awk '$2 == "installed" {print $1}')"; \
    test -n "$packages"; \
    apt-get install -y --no-install-recommends --only-upgrade $packages; \
    for p in $packages; do \
      installed="$(dpkg-query -W -f='${Version}' "$p")"; \
      dpkg --compare-versions "$installed" ge "$PHP_MIN_VERSION"; \
    done; \
    printf '%s\n' 'session.upload_progress.enabled=0' > /etc/php/8.3/cli/conf.d/99-olares-security.ini; \
    rm -rf /var/lib/apt/lists/*
RUN set -eu; \
    base="https://downloads.poolside.ai/pool/${POOL_VERSION}"; \
    archive="pool-linux-${TARGETARCH}.tar.gz"; \
    curl -fsSL "$base/$archive" -o "/tmp/$archive"; \
    curl -fsSL "$base/checksums.txt" -o /tmp/pool-checksums.txt; \
    cd /tmp; grep "  $archive$" pool-checksums.txt | sha256sum -c -; \
    tar -xzf "$archive"; \
    install -m 0755 "pool-linux-${TARGETARCH}" /usr/local/bin/pool; \
    rm -f "$archive" pool-checksums.txt "pool-linux-${TARGETARCH}"; \
    /usr/local/bin/pool --version
USER 1000:1000
WORKDIR /opt/data/work
CMD ["sleep", "infinity"]
