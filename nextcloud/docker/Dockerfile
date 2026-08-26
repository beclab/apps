# Olares Nextcloud image: official Apache tag + www-data remapped to 1000:1000.
#
# Current Market image is a full rebuild of nextcloud:31.0.4-apache with the same
# uid remap baked in (beclab/aboveos-zhangdangfang-nextcloud:31.0.4.2). This file
# is the maintainable equivalent: FROM the official image, then usermod/chown.
#
# Do not jump more than one Nextcloud major per running volume. Existing 31.0.4
# data can go to 31.0.14 or 32.x in one upgrade; 33/34 need intermediate majors.
#
# Build (pick one version):
#   docker buildx build --platform linux/amd64 \
#     --build-arg NEXTCLOUD_VERSION=31.0.14 \
#     -t beclab/harveyff-nextcloud:31.0.14.1 \
#     --push .
#
#   --build-arg NEXTCLOUD_VERSION=32.0.14
#   --build-arg NEXTCLOUD_VERSION=33.0.8
#   --build-arg NEXTCLOUD_VERSION=34.0.3
#
# Multi-arch for Market (amd64+arm64):
#   docker buildx build --platform linux/amd64,linux/arm64 \
#     --build-arg NEXTCLOUD_VERSION=31.0.14 \
#     -t beclab/harveyff-nextcloud:31.0.14.1 \
#     --push .

# syntax=docker/dockerfile:1

ARG NEXTCLOUD_VERSION=31.0.14
FROM docker.io/library/nextcloud:${NEXTCLOUD_VERSION}-apache

# Debian www-data is uid/gid 33. Olares userspace hostPath is 1000:1000.
# Capture the old ids before usermod; files keep the numeric owner until chown.
RUN set -eux; \
    old_uid="$(id -u www-data)"; \
    old_gid="$(id -g www-data)"; \
    groupmod -o --gid 1000 www-data; \
    usermod -o --uid 1000 --gid 1000 www-data; \
    for dir in /var/www /usr/src /usr/local /etc/apache2 /var/log/apache2 /var/run/apache2; do \
      [ -d "${dir}" ] || continue; \
      find "${dir}" -xdev \( -user "${old_uid}" -o -group "${old_gid}" \) \
        -exec chown -h www-data:www-data {} +; \
    done
