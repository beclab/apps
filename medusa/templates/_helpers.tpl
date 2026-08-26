{{/*
Nginx reverse proxy config for the medusa sidecar.
Referenced by deployment.yaml; checksum in Deployment triggers rollout on change.
*/}}
{{- define "medusa.nginx.conf" -}}
server {

  listen 8080;

  absolute_redirect off;

  access_log /usr/local/openresty/nginx/logs/access.log;
  error_log /usr/local/openresty/nginx/logs/error.log;

  # Official OpenResty defaults to 1m; product image uploads need more.
  client_max_body_size 100m;

  proxy_connect_timeout 30s;
  proxy_send_timeout 60s;
  proxy_read_timeout 300s;
  proxy_set_header host $host;
  proxy_set_header x-forwarded-host $http_host;
  proxy_http_version 1.1;
  proxy_set_header upgrade $http_upgrade;
  proxy_set_header connection "upgrade";

  location = / {
    return 302 /app/;
  }

  location / {
    proxy_hide_header Access-Control-Allow-Origin;
    proxy_hide_header Access-Control-Allow-Methods;
    proxy_hide_header Access-Control-Allow-Headers;
    add_header Access-Control-Allow-Origin *;
    add_header Access-Control-Allow-Methods GET,POST,PUT,DELETE,OPTIONS;

    proxy_pass http://localhost:9000;
  }
}
{{- end -}}
