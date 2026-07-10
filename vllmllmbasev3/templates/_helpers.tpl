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
{{- /* vllmllmbasev3.engineArgs: pass ENGINE_ARGS through unchanged.
       Usage: {{ include "vllmllmbasev3.engineArgs" (dict "Args" $engineArgs) }} */ -}}
{{- define "vllmllmbasev3.engineArgs" -}}
{{- $in := . -}}
{{- trim ($in.Args | default "") -}}
{{- end -}}
{{- /* Olares GPU mode at install: nvidia | nvidia-gb10 (from .Values.gpu / .Values.GPU.Type). */ -}}
{{- define "llmbase.gpuType" -}}
{{- $gpuObj := .Values.GPU | default dict -}}
{{- $gpuType := .Values.gpu | default "" -}}
{{- if not $gpuType -}}
{{- $gpuType = $gpuObj.Type | default "nvidia" -}}
{{- end -}}
{{- $gpuType -}}
{{- end -}}
{{- /* Host CPU arch for per-arch image tags: amd64 (default) | arm64. */ -}}
{{- define "llmbase.hostArch" -}}
{{- $arch := lower (toString (.Values.arch | default "")) -}}
{{- if not $arch -}}
{{- $arch = lower (toString (.Values.Arch | default "")) -}}
{{- end -}}
{{- if or (eq $arch "arm64") (eq $arch "aarch64") -}}
arm64
{{- else if or (eq $arch "amd64") (eq $arch "x86_64") -}}
amd64
{{- else if eq (include "llmbase.gpuType" .) "nvidia-gb10" -}}
arm64
{{- else if eq (include "llmbase.isGb10" .) "true" -}}
arm64
{{- else -}}
amd64
{{- end -}}
{{- end -}}
{{- /* vLLM engine image by accelerator — see terminus-apps-docs/vllmllmbasev3/VLLM_OFFICIAL_IMAGES.md */ -}}
{{- define "vllmllmbasev3.engineImage" -}}
{{- $gpuType := include "llmbase.gpuType" . -}}
{{- $isGb10 := or (eq $gpuType "nvidia-gb10") (eq (include "llmbase.isGb10" .) "true") -}}
{{- $arch := include "llmbase.hostArch" . -}}
{{- $img := .Values.engine.images | default dict -}}
{{- if $isGb10 -}}
{{- $img.nvidiaGb10 | default "docker.io/vllm/vllm-openai:latest-aarch64-cu130" -}}
{{- else if eq $arch "arm64" -}}
{{- $img.nvidiaArm64 | default "docker.io/vllm/vllm-openai:v0.24.0-aarch64-cu129" -}}
{{- else -}}
{{- $img.nvidia | default "docker.io/vllm/vllm-openai:v0.24.0-cu129" -}}
{{- end -}}
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
