{{- define "levv1.engineImage" -}}docker.io/beclab/systemone-engine:v0.3.3-lev-cuda13-amd64{{- end -}}
{{- define "levv1.llmInitImage" -}}docker.io/beclab/llm-init:v1.7.23{{- end -}}
{{- define "levv1.modelName" -}}lev{{- end -}}
{{- define "levv1.adapterRepo" -}}interfaze-ai/lev{{- end -}}
{{- define "levv1.adapterRevision" -}}f8ef71157ec06a7d3b6435bc0756f9d735c33748{{- end -}}
{{- define "levv1.baseRepo" -}}Qwen/Qwen3.5-4B{{- end -}}
{{- define "levv1.baseRevision" -}}851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a{{- end -}}
{{- define "levv1.runStatePath" -}}{{ printf "%s/llm-init-run/%s" .Values.userspace.appCache .Release.Name }}{{- end -}}
