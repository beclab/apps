{{/*
Nginx reverse proxy config for nextcloudweb (clientproxy).
Referenced by nginx-configmap.yaml; checksum in Deployment triggers rollout on change.
*/}}
{{- define "nextcloud.nginx.conf" -}}
server {
    listen 8080;
    access_log /dev/stdout;
    error_log /dev/stderr;

    client_body_temp_path /tmp/client_body;
    proxy_temp_path /tmp/proxy;
    fastcgi_temp_path /tmp/fastcgi;
    uwsgi_temp_path /tmp/uwsgi;
    scgi_temp_path /tmp/scgi;

    client_max_body_size 512m;

    proxy_connect_timeout 30s;
    proxy_send_timeout 60s;
    proxy_read_timeout 300s;
    proxy_set_header host $host;
    proxy_set_header x-forwarded-host $http_host;

    proxy_http_version 1.1;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header upgrade $http_upgrade;
    proxy_set_header connection "upgrade";

    location = /healthz {
        access_log off;
        return 200 'ok\n';
        add_header Content-Type text/plain;
    }

    location ~ ^/(remote\.php|public\.php|ocs|ocm-provider|ocs-provider|dav) {
        proxy_pass http://nextcloud-svc:80;
    }

    location / {
        proxy_hide_header Access-Control-Allow-Origin;
        proxy_hide_header Access-Control-Allow-Methods;
        proxy_hide_header Access-Control-Allow-Headers;
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods GET,POST,PUT,DELETE,OPTIONS;
        add_header Access-Control-Allow-Headers "deviceType,token, authorization, content-type,x-csrftoken";
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods GET,POST,PUT,DELETE,OPTIONS;
            add_header Access-Control-Allow-Headers "deviceType,token, authorization, content-type,x-csrftoken";
            return 204;
        }
        proxy_pass http://nextcloud-svc:80;
    }
}
{{- end -}}
