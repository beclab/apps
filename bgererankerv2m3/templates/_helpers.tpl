{{- /* bgererankerv2m3.gpuMiB: normalize GPU memory to bare MiB for HAMi gpumem. */ -}}
{{- define "bgererankerv2m3.gpuMiB" -}}
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

{{- /* Olares GPU mode: cpu | intel | intel-gpu | nvidia | nvidia-gb10 */ -}}
{{- define "bgererankerv2m3.gpuType" -}}
{{- $gpuObj := .Values.GPU | default dict -}}
{{- $gpuType := .Values.gpu | default "" -}}
{{- if not $gpuType -}}
{{- $gpuType = $gpuObj.Type | default "cpu" -}}
{{- end -}}
{{- $gpuType -}}
{{- end -}}

{{- define "bgererankerv2m3.rerankTag" -}}v0.0.4{{- end -}}
{{- define "bgererankerv2m3.llmInitTag" -}}v1.7.21{{- end -}}
{{- /* RuntimeQueue serializes scoring through exactly one active permit. */ -}}
{{- define "bgererankerv2m3.maxConcurrency" -}}1{{- end -}}
{{- define "bgererankerv2m3.unifiedRepo" -}}beclab/bge-reranker-v2-m3{{- end -}}
{{- define "bgererankerv2m3.modelRevision" -}}main{{- end -}}
{{- define "bgererankerv2m3.logicalModelName" -}}bge-reranker-v2-m3{{- end -}}

{{- /* intel / intel-gpu → OpenVINO subdir; all other modes → ONNX subdir */ -}}
{{- define "bgererankerv2m3.useOpenVino" -}}
{{- $mode := include "bgererankerv2m3.gpuType" . -}}
{{- or (eq $mode "intel") (eq $mode "intel-gpu") -}}
{{- end -}}

{{- /* rerank-server: MODEL_NAME == MODEL_ID (no -ov/-onnx suffix). */ -}}
{{- define "bgererankerv2m3.modelId" -}}
{{- include "bgererankerv2m3.logicalModelName" . -}}
{{- end -}}

{{- define "bgererankerv2m3.modelSource" -}}
{{- $repo := include "bgererankerv2m3.unifiedRepo" . -}}
{{- $rev := include "bgererankerv2m3.modelRevision" . -}}
{{- if eq (include "bgererankerv2m3.useOpenVino" .) "true" -}}
hf://{{ $repo }} --revision {{ $rev }} --exclude onnx/** --subdir openvino
{{- else -}}
hf://{{ $repo }} --revision {{ $rev }} --exclude openvino/** --subdir onnx
{{- end -}}
{{- end -}}
