{{/*
Nginx reverse proxy config for onlyofficeproxy.
Referenced by onlyofficeproxy.yaml; checksum in Deployment triggers rollout on change.
*/}}
{{- define "onlyofficev3.nginx.conf" -}}
server {
  client_body_temp_path /tmp/client_body;
  proxy_temp_path /tmp/proxy;
  fastcgi_temp_path /tmp/fastcgi;
  uwsgi_temp_path /tmp/uwsgi;
  scgi_temp_path /tmp/scgi;
  listen 8080;
  access_log /dev/stdout;
  error_log /dev/stderr;

  # Official OpenResty defaults to 1m; office document uploads need more.
  client_max_body_size 100m;

  proxy_connect_timeout 30s;
  proxy_send_timeout 60s;
  proxy_read_timeout 300s;

  proxy_set_header host $host;
  proxy_set_header x-forwarded-host $http_host;
  proxy_http_version 1.1;
  proxy_set_header upgrade $http_upgrade;
  proxy_set_header connection "upgrade";

  proxy_set_header X-BFL-USER {{ .Values.bfl.username }};
  proxy_set_header Cookie $http_cookie;
  proxy_set_header X-Authorization $http_x_authorization;

  location /coauthoring/CommandService.ashx {
    add_header X-Frame-Options "";
    proxy_pass http://onlyoffice-svc.{{ .Release.Namespace }}.svc.cluster.local:80/coauthoring/CommandService.ashx;
  }

  location /ConvertService.ashx {
    add_header X-Frame-Options "";
    proxy_pass http://onlyoffice-svc.{{ .Release.Namespace }}.svc.cluster.local:80/ConvertService.ashx;
  }

  location /coauthoring/ {
    add_header X-Frame-Options "";
    proxy_pass http://onlyoffice-svc.{{ .Release.Namespace }}.svc.cluster.local:80/coauthoring/;
  }

  location /web-apps {
    add_header X-Frame-Options "";
    proxy_pass http://onlyoffice-svc.{{ .Release.Namespace }}.svc.cluster.local:80/web-apps;
  }

  location ~ ^/9.2.0 {
    add_header X-Frame-Options "";
    proxy_pass http://onlyoffice-svc.{{ .Release.Namespace }}.svc.cluster.local:80;
  }

  location /cache {
    add_header X-Frame-Options "";
    proxy_pass http://onlyoffice-svc.{{ .Release.Namespace }}.svc.cluster.local:80/cache;
  }

  location / {
    add_header X-Frame-Options "";
    proxy_pass http://onlyofficeclient.{{ .Release.Namespace }}.svc.cluster.local:3000;
  }
}
{{- end -}}
