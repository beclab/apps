{{- /* Olares accelerator mode: nvidia only (v3). */ -}}
{{- define "paddleocrv3.gpuType" -}}
{{- $gpuObj := .Values.GPU | default dict -}}
{{- $gpuType := .Values.gpu | default "" -}}
{{- if not $gpuType -}}
{{- $gpuType = $gpuObj.Type | default "nvidia" -}}
{{- end -}}
{{- $gpuType -}}
{{- end -}}

{{- /* Olares v3: .Values.nodes may arrive as either []api.NodeInfo (raw Go
       structs) or []map[string]interface{} (JSON-round-tripped) depending on
       the app-service code path (install vs upgrade / dry-run). We normalize
       each entry via toJson|fromJson so field access always uses the JSON
       tag names: gpus[] with .arch / .modelName / .vendor. */ -}}
{{- define "paddleocrv3.isBlackwell" -}}
{{- $is := "false" -}}
{{- range $node := (.Values.nodes | default (list)) -}}
  {{- $nodeMap := (toJson $node) | fromJson -}}
  {{- range $gpu := ((index $nodeMap "gpus") | default (list)) -}}
    {{- if eq (upper (toString (index $gpu "arch"))) "BLACKWELL" -}}
      {{- $is = "true" -}}
    {{- end -}}
  {{- end -}}
{{- end -}}
{{- $is -}}
{{- end -}}

{{- /* Normalize GPU memory to bare MiB for HAMi nvidia.com/gpumem. */ -}}
{{- define "paddleocrv3.gpuMiB" -}}
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

{{- define "paddleocrv3.engineImage" -}}
{{- if eq (include "paddleocrv3.isBlackwell" .) "true" -}}
docker.io/beclab/bleachzou-paddleocr3.4-nividia-gpu-sm120-offline:0.0.1
{{- else -}}
docker.io/beclab/bleachzou-paddleocr3.4-nividia-gpu-offline:0.0.1
{{- end -}}
{{- end -}}
