{{- define "oraki.name" -}}{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}{{- end -}}
{{- define "oraki.fullname" -}}{{- printf "%s-%s" .Release.Namespace (default (include "oraki.name" .) .Values.fullnameOverride) | trunc 63 | trimSuffix "-" -}}{{- end -}}
{{- define "oraki.image" -}}{{- printf "%s:%s" .repository .tag -}}{{- end -}}
