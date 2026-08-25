{{/*
Nginx reverse proxy config for giteaproxy (clientproxy).
Referenced by clientproxy.yaml; checksum in Deployment triggers rollout on change.
*/}}
{{- define "gitea.nginx.conf" -}}
server {
    listen 8080;
    access_log /usr/local/openresty/nginx/logs/access.log;
    error_log /usr/local/openresty/nginx/logs/error.log;

    # Official OpenResty defaults to 1m; Gitea docs recommend 512M
    # so web uploads, git HTTP push, and typical LFS objects are not 413'd.
    client_max_body_size 512m;

    proxy_connect_timeout 30s;
    proxy_send_timeout 60s;
    proxy_read_timeout 300s;
    proxy_set_header host $host;
    proxy_set_header x-forwarded-host $http_host;
    proxy_http_version 1.1;
    proxy_set_header upgrade $http_upgrade;
    proxy_set_header connection "upgrade";

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
        proxy_pass http://gitea-svc:3000;
    }
}
{{- end -}}
