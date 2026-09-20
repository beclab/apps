{{- /* dotsocr.gpuMiB: normalize GPU memory to bare MiB int for nvidia.com/gpumem. */ -}}
{{- define "dotsocr.gpuMiB" -}}
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

{{- define "dotsocr.llmInitTag" -}}v1.7.21{{- end -}}
{{- define "dotsocr.ocrAdapterImage" -}}docker.io/beclab/ocr-adapter:v0.0.9{{- end -}}
{{- define "dotsocr.llamacppImage" -}}docker.io/beclab/ggml-org-llama.cpp:server-cuda12-b10143{{- end -}}

{{- /* Q8-only pair: comma dual-source, each one --include (single-file hf path).
       Avoids one hf:// with two --include, which can leave snapshot without main GGUF. */ -}}
{{- define "dotsocr.modelSource" -}}
hf://ggml-org/dots.ocr-GGUF --include dots.ocr-Q8_0.gguf,hf://ggml-org/dots.ocr-GGUF --include mmproj-dots.ocr-Q8_0.gguf
{{- end -}}

{{- define "dotsocr.modelName" -}}dots{{- end -}}

{{- /* Redis URL from Olares middleware (.Values.redis). */ -}}
{{- define "dotsocr.redisURL" -}}
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
