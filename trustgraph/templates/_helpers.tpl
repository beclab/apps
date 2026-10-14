{{- define "trustgraph.llmBaseURL" -}}
{{- $oe := .Values.olaresEnv | default dict -}}
{{- index $oe "LLM_BASE_URL" | default (printf "https://router.%s/v1" .Values.user.zone) -}}
{{- end -}}

{{- define "trustgraph.llmApiKey" -}}
{{- $oe := .Values.olaresEnv | default dict -}}
{{- index $oe "LLM_API_KEY" | default "not-required" -}}
{{- end -}}
