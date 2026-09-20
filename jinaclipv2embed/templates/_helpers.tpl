{{- /* jinaclipv2embed.gpuMiB: normalize GPU memory to bare MiB for HAMi gpumem. */ -}}
{{- define "jinaclipv2embed.gpuMiB" -}}
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

{{- /* Olares GPU mode: cpu | intel | nvidia | nvidia-gb10 */ -}}
{{- define "jinaclipv2embed.gpuType" -}}
{{- $gpuObj := .Values.GPU | default dict -}}
{{- $gpuType := .Values.gpu | default "" -}}
{{- if not $gpuType -}}
{{- $gpuType = $gpuObj.Type | default "cpu" -}}
{{- end -}}
{{- $gpuType -}}
{{- end -}}

{{- define "jinaclipv2embed.embedTag" -}}v0.1.9{{- end -}}
{{- define "jinaclipv2embed.llmInitTag" -}}v1.7.21{{- end -}}
{{- define "jinaclipv2embed.unifiedRepo" -}}beclab/jina-clip-v2-split{{- end -}}
{{- define "jinaclipv2embed.modelRevision" -}}main{{- end -}}
{{- define "jinaclipv2embed.logicalModelName" -}}jina-clip-v2{{- end -}}

{{- /* intel → OpenVINO subdir; all other modes → ONNX subdir */ -}}
{{- define "jinaclipv2embed.useOpenVino" -}}
{{- eq (include "jinaclipv2embed.gpuType" .) "intel" -}}
{{- end -}}

{{- define "jinaclipv2embed.modelId" -}}
{{- if eq (include "jinaclipv2embed.useOpenVino" .) "true" -}}
jina-clip-v2-split-ov
{{- else -}}
jina-clip-v2-split-onnx
{{- end -}}
{{- end -}}

{{- define "jinaclipv2embed.modelSource" -}}
{{- $repo := include "jinaclipv2embed.unifiedRepo" . -}}
{{- $rev := include "jinaclipv2embed.modelRevision" . -}}
{{- if eq (include "jinaclipv2embed.useOpenVino" .) "true" -}}
hf://{{ $repo }} --revision {{ $rev }} --exclude onnx/** --subdir openvino
{{- else -}}
hf://{{ $repo }} --revision {{ $rev }} --exclude openvino/** --subdir onnx
{{- end -}}
{{- end -}}
