{{- define "GPU.getGPUInfo" -}}
{{- $gpuModel := "" -}}
{{- $gpuModelName := "" -}}
{{- $is50Series := "false" -}}
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
                {{- $modelUpper := upper .Model -}}
                {{- $modelNameUpper := upper .ModelName -}}
                {{- $isRTX50XX := and (hasPrefix "50" $modelUpper) (not (hasPrefix "500" $modelUpper)) (ne "50" $modelUpper) -}}
                {{- $isRTX50XX = or $isRTX50XX (and (contains "RTX 50" $modelNameUpper) (not (contains "RTX 5000" $modelNameUpper)) (not (contains "QUADRO" $modelNameUpper))) -}}
                {{- if $isRTX50XX -}}
                  {{- $is50Series = "true" -}}
                {{- end -}}
              {{- end -}}
            {{- end -}}
          {{- end -}}
        {{- end -}}
      {{- end -}}
    {{- end -}}
  {{- end -}}
{{- end -}}
{{- dict "gpuModel" $gpuModel "gpuModelName" $gpuModelName "is50Series" $is50Series | toJson -}}
{{- end -}}