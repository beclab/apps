{{/*
通用命名与标签。所有模板共用。
*/}}
{{- define "mindwtr.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "mindwtr.fullname" -}}
{{- printf "%s" .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "mindwtr.labels" -}}
app: {{ include "mindwtr.name" . }}
app.kubernetes.io/name: {{ include "mindwtr.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "mindwtr.selectorLabels" -}}
app: {{ include "mindwtr.name" . }}
{{- end -}}

{{/*
Service 名字。Olares 的 entrance.host 必须与它完全一致，
所以默认取 {{ .Release.Name }}-svc（与官方 beclab/apps 里的写法一致）。
*/}}
{{- define "mindwtr.serviceName" -}}
{{- printf "%s-svc" (include "mindwtr.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
