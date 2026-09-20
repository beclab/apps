{{- define "surya2ocr.gpuMiB" -}}
{{- $g := trim . -}}
{{- if hasSuffix "Gi" $g -}}
{{- mul (int (trimSuffix "Gi" $g)) 1024 -}}
{{- else if hasSuffix "G" $g -}}
{{- mul (int (trimSuffix "G" $g)) 1024 -}}
{{- else if hasSuffix "Mi" $g -}}
{{- int (trimSuffix "Mi" $g) -}}
{{- else if hasSuffix "M" $g -}}
{{- int (trimSuffix "M" $g) -}}
{{- else -}}
{{- int $g -}}
{{- end -}}
{{- end -}}

{{- define "surya2ocr.llmInitTag" -}}v1.7.21{{- end -}}
{{- define "surya2ocr.ocrAdapterImage" -}}docker.io/beclab/ocr-adapter:v0.0.9{{- end -}}
{{- define "surya2ocr.llamacppImage" -}}docker.io/beclab/ggml-org-llama.cpp:server-cuda12-b10143{{- end -}}

{{- /* Separate downloads ensure both the model and vision projector are cached. */ -}}
{{- define "surya2ocr.modelSource" -}}
hf://datalab-to/surya-ocr-2-gguf --include surya-2.gguf,hf://datalab-to/surya-ocr-2-gguf --include surya-2-mmproj.gguf
{{- end -}}

{{- define "surya2ocr.modelName" -}}surya2{{- end -}}

{{- define "surya2ocr.redisURL" -}}
{{- $r := .Values.redis | default dict -}}
{{- $host := $r.host | default "redis" -}}
{{- $port := $r.port | default "6379" -}}
{{- $pass := $r.password | default "" -}}
{{- if $pass -}}
redis://:{{ $pass }}@{{ $host }}:{{ $port }}/0
{{- else -}}
redis://{{ $host }}:{{ $port }}/0
{{- end -}}
{{- end -}}
