{{/*
Expand the name of the chart.
*/}}
{{- define "opentodo.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "opentodo.fullname" -}}
{{- printf "%s" .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "opentodo.labels" -}}
app: {{ include "opentodo.name" . }}
io.kompose.service: opentodo
app.kubernetes.io/name: {{ include "opentodo.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "opentodo.selectorLabels" -}}
io.kompose.service: opentodo
{{- end -}}

{{/*
Service name - matches entrance.host
*/}}
{{- define "opentodo.serviceName" -}}
{{- printf "%s-svc" (include "opentodo.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
