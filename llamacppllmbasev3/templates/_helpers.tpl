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
{{- /* llamacppllmbasev3.engineArgs: pass ENGINE_ARGS through unchanged.
       Usage: {{ include "llamacppllmbasev3.engineArgs" (dict "Args" $engineArgs) }} */ -}}
{{- define "llamacppllmbasev3.engineArgs" -}}
{{- $in := . -}}
{{- trim ($in.Args | default "") -}}
{{- end -}}
{{- /* Olares GPU mode at install: nvidia | nvidia-gb10 | amd-gpu | intel | intel-gpu. */ -}}
{{- define "llmbase.gpuType" -}}
{{- $gpuObj := .Values.GPU | default dict -}}
{{- $gpuType := .Values.gpu | default "" -}}
{{- if not $gpuType -}}
{{- $gpuType = $gpuObj.Type | default "nvidia" -}}
{{- end -}}
{{- $gpuType -}}
{{- end -}}
{{- /* llama.cpp engine image by accelerator. NVIDIA/Spark CUDA b10752; amd-gpu ROCm b10731; intel-gpu SYCL b10752. */ -}}
{{- define "llamacppllmbasev3.engineImage" -}}
{{- $gpuType := include "llmbase.gpuType" . -}}
{{- $isGb10 := or (eq $gpuType "nvidia-gb10") (eq (include "llmbase.isGb10" .) "true") -}}
{{- $img := .Values.engine.images | default dict -}}
{{- if eq $gpuType "amd-gpu" -}}
{{- $img.amdGpu | default "docker.io/beclab/ggml-org-llama.cpp:server-rocm-b10731" -}}
{{- else if eq $gpuType "intel-gpu" -}}
{{- $img.intelGpu | default "docker.io/beclab/ggml-org-llama.cpp:server-intel-b10752" -}}
{{- else if eq $gpuType "intel" -}}
{{- $img.intel | default "docker.io/beclab/ggml-org-llama.cpp:server-intel-b10884" -}}
{{- else if $isGb10 -}}
{{- $img.nvidiaGb10 | default "docker.io/beclab/ggml-org-llama.cpp:server-cuda12-b10969" -}}
{{- else -}}
{{- $img.nvidia | default "docker.io/beclab/ggml-org-llama.cpp:server-cuda12-b10969" -}}
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
