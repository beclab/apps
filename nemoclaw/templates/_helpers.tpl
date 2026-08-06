{{/*
Browser origin for OpenClaw web UI allowlist (CHAT_UI_URL).
Olares sets domain per entrance name (see OlaresManifest entrances[].name). Web UI entrance is "webtui"
→ Values.domain.webtui (comma-separated hosts, first wins). Legacy: domain.nemoclaw.
*/}}
{{- define "nemoclaw.chatUiUrl" -}}
{{- if .Values.olaresEnv.CHAT_UI_URL -}}
{{- .Values.olaresEnv.CHAT_UI_URL -}}
{{- else if and .Values.domain .Values.domain.webtui -}}
{{- $hosts := splitList "," .Values.domain.webtui -}}
{{- if gt (len $hosts) 0 -}}
{{- $h := trim (index $hosts 0) -}}
{{- if ne $h "" -}}
https://{{ $h }}
{{- end -}}
{{- end -}}
{{- else if and .Values.domain .Values.domain.nemoclaw -}}
{{- $hosts := splitList "," .Values.domain.nemoclaw -}}
{{- if gt (len $hosts) 0 -}}
{{- $h := trim (index $hosts 0) -}}
{{- if ne $h "" -}}
https://{{ $h }}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Resolve the gog keyring password with three-tier precedence:
  1. Olares env GOG_KEYRING_PASSWORD — user pin. Highest priority.
  2. Existing `nemoclaw-gog-keyring` Secret — preserves value across
     `helm upgrade` so already-encrypted keyring files stay readable.
  3. Fresh `randAlphaNum 8` — first install only.
Returned verbatim (unquoted); callers must quote or b64enc as needed.
*/}}
{{- define "nemoclaw.gogKeyringPassword" -}}
{{- $pinned := "" -}}
{{- with .Values.olaresEnv -}}{{- $pinned = (.GOG_KEYRING_PASSWORD | default "") -}}{{- end -}}
{{- if $pinned -}}
{{- $pinned -}}
{{- else -}}
{{- $existing := lookup "v1" "Secret" .Release.Namespace "nemoclaw-gog-keyring" -}}
{{- if and $existing $existing.data (index $existing.data "password") -}}
{{- index $existing.data "password" | b64dec -}}
{{- else -}}
{{- randAlphaNum 8 -}}
{{- end -}}
{{- end -}}
{{- end -}}
