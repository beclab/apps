{{- /* embeddinggemmav3.gpuMiB: normalize GPU memory to bare MiB for HAMi gpumem. */ -}}
{{- define "embeddinggemmav3.gpuMiB" -}}
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
{{- define "embeddinggemmav3.gpuType" -}}
{{- $gpuObj := .Values.GPU | default dict -}}
{{- $gpuType := .Values.gpu | default "" -}}
{{- if not $gpuType -}}
{{- $gpuType = $gpuObj.Type | default "cpu" -}}
{{- end -}}
{{- $gpuType -}}
{{- end -}}

{{- define "embeddinggemmav3.embedTag" -}}v0.1.0{{- end -}}
{{- define "embeddinggemmav3.llmInitTag" -}}v1.3.0{{- end -}}
{{- define "embeddinggemmav3.unifiedRepo" -}}beclab/embeddinggemma-300m{{- end -}}
{{- define "embeddinggemmav3.modelRevision" -}}main{{- end -}}
{{- define "embeddinggemmav3.logicalModelName" -}}embeddinggemma-300m{{- end -}}

{{- /* intel → OpenVINO subdir; all other modes → ONNX subdir */ -}}
{{- define "embeddinggemmav3.useOpenVino" -}}
{{- eq (include "embeddinggemmav3.gpuType" .) "intel" -}}
{{- end -}}

{{- define "embeddinggemmav3.modelId" -}}
{{- if eq (include "embeddinggemmav3.useOpenVino" .) "true" -}}
embeddinggemma-300m-ov
{{- else -}}
embeddinggemma-300m-onnx
{{- end -}}
{{- end -}}

{{- define "embeddinggemmav3.modelSource" -}}
{{- $repo := include "embeddinggemmav3.unifiedRepo" . -}}
{{- $rev := include "embeddinggemmav3.modelRevision" . -}}
{{- if eq (include "embeddinggemmav3.useOpenVino" .) "true" -}}
hf://{{ $repo }} --revision {{ $rev }} --exclude onnx/** --subdir openvino
{{- else -}}
hf://{{ $repo }} --revision {{ $rev }} --exclude openvino/** --subdir onnx
{{- end -}}
{{- end -}}
