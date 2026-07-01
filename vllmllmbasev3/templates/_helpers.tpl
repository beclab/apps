{{- /* llmbase.gpuMiB: normalize a GPU-memory quantity to a BARE MiB integer for
       HAMi's nvidia.com/gpumem. Its base unit is MiB and the value MUST be a
       plain integer — a Mi/Gi suffix is misread by the scheduler (e.g. "6144Mi"
       -> 6442450944). Accepts 8Gi / 8G / 8192Mi / 8192M / 8192 and returns MiB.
       Usage: {{ include "llmbase.gpuMiB" ($oe.X_REQUIRED_GPU_MEMORY | default "4096") }} */ -}}
{{- define "llmbase.gpuMiB" -}}
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
{{- /* vllmllmbasev3.engineArgs: CPU mode auto-adds --device cpu unless already set.
       Usage: {{ include "vllmllmbasev3.engineArgs" (dict "Args" $engineArgs "IsCpu" $isCpuMode) }} */ -}}
{{- define "vllmllmbasev3.engineArgs" -}}
{{- $in := . -}}
{{- $args := trim ($in.Args | default "") -}}
{{- $isCpu := $in.IsCpu | default false -}}
{{- if and $isCpu (not (contains "--device" $args)) -}}
{{- if $args -}}
{{- $args = printf "%s --device cpu" $args -}}
{{- else -}}
{{- $args = "--device cpu" -}}
{{- end -}}
{{- end -}}
{{- $args -}}
{{- end -}}
{{- /* Spark/GB10: detect from GPU.Type or node hardware (install-time .Values.nodes). */ -}}
{{- define "llmbase.isGb10" -}}
{{- $isGb10 := "false" -}}
{{- if .Values.nodes -}}
  {{- range $nodeIndex, $node := .Values.nodes -}}
    {{- if eq $nodeIndex 0 -}}
      {{- with $node -}}
        {{- if .GPUS -}}
          {{- range $gpuIndex, $gpu := .GPUS -}}
            {{- if eq $gpuIndex 0 -}}
              {{- with $gpu -}}
                {{- if eq (upper .Model) "GB10" -}}
                  {{- $isGb10 = "true" -}}
                {{- end -}}
              {{- end -}}
            {{- end -}}
          {{- end -}}
        {{- end -}}
      {{- end -}}
    {{- end -}}
  {{- end -}}
{{- end -}}
{{- $isGb10 -}}
{{- end -}}
