{{/* The app's own image: repository:tag, plus @digest once the multi-arch index is pushed and pinned in values. */}}
{{- define "agentj.image" -}}
{{- $i := .Values.image -}}
{{- if $i.digest -}}
{{ printf "%s:%s@%s" $i.repository $i.tag $i.digest | quote }}
{{- else -}}
{{ printf "%s:%s" $i.repository $i.tag | quote }}
{{- end -}}
{{- end -}}
