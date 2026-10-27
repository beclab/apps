{{/* Pin the release so saved image values cannot retain an older runtime on upgrade. */}}
{{- define "unsloth.imageTag" -}}nightly-2026.10.26{{- end -}}
{{- define "unsloth.image" -}}docker.io/unsloth/unsloth:{{ include "unsloth.imageTag" . }}{{- end -}}
