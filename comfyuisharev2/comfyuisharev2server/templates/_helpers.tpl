{{- define "comfyuisharev2server.GPU.isGb10" -}}
{{- $isSparkDGX := "false" -}}
{{- if .Values.nodes -}}
  {{- range $nodeIndex, $node := .Values.nodes -}}
    {{- if eq $nodeIndex 0 -}}
      {{- with $node -}}
        {{- if .GPUS -}}
          {{- range $gpuIndex, $gpu := .GPUS -}}
            {{- if eq $gpuIndex 0 -}}
              {{- with $gpu -}}
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
{{- $isSparkDGX -}}
{{- end -}}
