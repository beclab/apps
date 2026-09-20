{{/*
Nginx config for ticket-web (clientproxy).
Referenced by nginx-configmap.yaml; checksum in web-deployment.yaml triggers rollout on change.
*/}}
{{- define "ticket.nginx.conf" -}}
server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    client_max_body_size 256m;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript application/xml image/svg+xml font/woff2;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location = /healthz {
        access_log off;
        add_header Content-Type text/plain;
        return 200 "ok\n";
    }

    # Ticket API lives on the server-side host (cross-host, public URL).
    location /v1/ {
        proxy_pass {{ .Values.olaresEnv.SERVER_API_URL }};
        proxy_http_version 1.1;
        proxy_ssl_server_name on;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 5m;
        proxy_send_timeout 5m;
    }

    # User-side backend (BFF): bridges the SPA to the local olaresd.
    location /bff/ {
        proxy_pass http://ticket-bff-svc:4200;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Cookie $http_cookie;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 10m;
        proxy_send_timeout 10m;
    }

    # Hashed build assets are immutable; cache hard.
    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        try_files $uri =404;
    }

    # SPA fallback. HTML is rewritten by Olares BFL (terminus-language meta);
    # no-store so refresh always gets a 200 body instead of a stale 304.
    location / {
        add_header Cache-Control "no-store";
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        try_files $uri $uri/ /index.html;
    }
}
{{- end -}}
