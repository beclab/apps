# syntax=docker/dockerfile:1

ARG NEXTCLOUD_VERSION=33.0.10
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

ADD --checksum=sha256:c746c726ddc7faeddc402c00a4c326bfa2395602c510d3e8807a1efdebaece77 https://github.com/Euro-Office/eurooffice-nextcloud/releases/download/v11.0.6/eurooffice.tar.gz /tmp/eurooffice.tar.gz
RUN tar -xzf /tmp/eurooffice.tar.gz -C /usr/src/nextcloud/custom_apps/ && rm /tmp/eurooffice.tar.gz
RUN chown -R 1000:1000 /usr/src/nextcloud/custom_apps/eurooffice \
    && mkdir -p /var/run/apache2 /var/lock/apache2 \
    && chown -R 1000:1000 /var/run/apache2 /var/lock/apache2
RUN sed -i 's/Listen 80/Listen 8080/' /etc/apache2/ports.conf && sed -i 's/\*:80/\*:8080/g' /etc/apache2/sites-available/*.conf
RUN printf 'ServerName localhost\n' > /etc/apache2/conf-available/servername.conf && a2enconf servername
USER 1000:1000
