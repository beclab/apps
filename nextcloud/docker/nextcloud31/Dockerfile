FROM docker.io/beclab/harveyff-nextcloud:31.0.14.3
USER root
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client-17 \
    && rm -rf /var/lib/apt/lists/*
USER 1000:1000
