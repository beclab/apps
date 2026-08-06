{{- define "GPU.getGPUInfo" -}}
{{- $gpuModel := "" -}}
{{- $gpuModelName := "" -}}
{{- $isSparkDGX := "false" -}}
{{- if .Values.nodes -}}
  {{- range $nodeIndex, $node := .Values.nodes -}}
    {{- if eq $nodeIndex 0 -}}
      {{- with $node -}}
        {{- if .GPUS -}}
          {{- range $gpuIndex, $gpu := .GPUS -}}
            {{- if eq $gpuIndex 0 -}}
              {{- with $gpu -}}
                {{- $gpuModel = .Model -}}
                {{- $gpuModelName = .ModelName -}}
                {{- if eq (upper .Model) "GB10" -}}
                  {{- $isSparkDGX = "true" -}}
                {{- end -}}
              {{- end -}}
            {{- end -}}
          {{- end -}}
        {{- end -}}
      {{- end -}}
    {{- end -}}
  {{- end -}}
{{- end -}}
{{- dict "gpuModel" $gpuModel "gpuModelName" $gpuModelName "isSparkDGX" $isSparkDGX | toJson -}}
{{- end -}}