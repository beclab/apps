FROM docker.io/beclab/qemux-qemu@sha256:2749bcf78411752fe1bc14f68b25fff757730a84f2044ab06597fb6cec672a19
USER root
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client && rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1000 olares-vm && useradd -u 1000 -g 1000 -M -d /tmp -s /usr/sbin/nologin olares-vm
USER 1000:1000
