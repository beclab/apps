# Keep the intermediate Nextcloud code and entrypoint, but replace its obsolete
# PHP runtime with the patched PHP 8.4 runtime supported by Nextcloud 31.
FROM docker.io/library/nextcloud:31.0.14-apache AS nextcloud-source
FROM docker.io/library/nextcloud:33.0.10-apache

ENV NEXTCLOUD_VERSION=31.0.14
RUN rm -rf /usr/src/nextcloud
COPY --from=nextcloud-source /usr/src/nextcloud /usr/src/nextcloud
COPY --from=nextcloud-source /entrypoint.sh /entrypoint.sh
COPY --from=nextcloud-source /cron.sh /cron.sh

RUN set -eux; \
    old_uid="$(id -u www-data)"; \
    old_gid="$(id -g www-data)"; \
    groupmod -o --gid 1000 www-data; \
    usermod -o --uid 1000 --gid 1000 www-data; \
    for dir in /var/www /usr/src /usr/local /etc/apache2 /var/log/apache2 /var/run/apache2; do \
      [ -d "${dir}" ] || continue; \
      find "${dir}" -xdev \( -user "${old_uid}" -o -group "${old_gid}" \) \
        -exec chown -h www-data:www-data {} +; \
    done; \
    apt-get update; \
    apt-get install -y --no-install-recommends postgresql-client-17; \
    rm -rf /var/lib/apt/lists/*
RUN sed -i 's/Listen 80/Listen 8080/' /etc/apache2/ports.conf \
    && sed -i 's/\*:80/\*:8080/g' /etc/apache2/sites-available/*.conf
USER 1000:1000
