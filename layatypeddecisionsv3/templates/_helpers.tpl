{{- define "layatypeddecisionsv3.engineImage" -}}
{{- if eq (.Values.gpu | default "cpu") "nvidia" -}}
docker.io/beclab/systemone-engine:v0.2.2-laya-cuda12.8-amd64
{{- else -}}
docker.io/beclab/systemone-engine:v0.1.0-laya-cpu-amd64
{{- end -}}
{{- end -}}
{{- define "layatypeddecisionsv3.llmInitImage" -}}docker.io/beclab/llm-init:v1.7.23{{- end -}}
{{- define "layatypeddecisionsv3.modelName" -}}laya-typed-decisions{{- end -}}
{{- define "layatypeddecisionsv3.modelRepo" -}}convaiinnovations/laya-typed-decisions{{- end -}}
{{- define "layatypeddecisionsv3.modelRevision" -}}f9ab0b228f0fc0f14d873dbc99038f135c2da1b2{{- end -}}
{{- define "layatypeddecisionsv3.runtimeRevision" -}}6a5819129eb220570792e417e49723d697efd76f{{- end -}}
{{- define "layatypeddecisionsv3.runStatePath" -}}{{ printf "%s/llm-init-run/%s" .Values.userspace.appCache .Release.Name }}{{- end -}}
