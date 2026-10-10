FROM beclab/euro-office-documentserver:sha256-889e681923d2dcc8bdfb92fe128d10e185fcff880d302b6a0c0c7bf339499290
USER root
RUN usermod -d /home/ds ds && groupmod -o -g 1000 ds && usermod -o -u 1000 -g 1000 ds \
    && chown -R 1000:1000 /var/lib/euro-office /var/log/euro-office /etc/euro-office /home/ds \
    && mkdir -p /var/cache/nginx /var/lib/nginx /var/log/nginx /run/nginx \
    && chown -R 1000:1000 /var/cache/nginx /var/lib/nginx /var/log/nginx /run/nginx /etc/nginx \
    && sed -i '/^user /d; s@pid /run/nginx.pid;@pid /tmp/nginx.pid;@' /etc/nginx/nginx.conf \
    && find /etc/nginx -type f -exec sed -i 's/listen 0.0.0.0:80;/listen 0.0.0.0:8080;/g; s/listen \[::\]:80/listen [::]:8080/g' {} +
ENV HOME=/home/ds NODE_ENV=production-linux NODE_CONFIG_DIR=/etc/euro-office/documentserver APPLICATION_NAME=euro-office
RUN sed -i 's/0.0.0.0:80/0.0.0.0:8080/; s/\[::\]:80/[::]:8080/' /etc/euro-office/documentserver/nginx/ds.conf
RUN /usr/bin/documentserver-generate-allfonts.sh true true \
    && test -s /var/www/euro-office/documentserver/sdkjs/common/AllFonts.js \
    && test -s /var/www/euro-office/documentserver/server/FileConverter/bin/font_selection.bin
USER 1000:1000
ENTRYPOINT ["/bin/bash", "/olares/start.sh"]
