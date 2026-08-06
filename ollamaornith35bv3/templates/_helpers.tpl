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
{{- /* ollamaornith35bv3.engineArgs: merge clone ENGINE_ARGS with chart defaults.
       OLLAMA_KEEP_ALIVE=-1 (forever in VRAM) on the ollama daemon unless set.
       llm-init ENGINE_ARGS strips this key (see engineArgsForLlminit). CPU mode
       adds OLLAMA_NUM_GPU=0 unless set.
       Usage: {{ include "ollamaornith35bv3.engineArgs" (dict "Args" ($oe.ENGINE_ARGS | default "") "IsCpu" $isCpuMode) }} */ -}}
{{- define "ollamaornith35bv3.engineArgs" -}}
{{- $in := . -}}
{{- $args := trim ($in.Args | default "") -}}
{{- $isCpu := $in.IsCpu | default false -}}
{{- if not (contains "OLLAMA_KEEP_ALIVE" $args) -}}
{{- if $args -}}
{{- $args = printf "%s OLLAMA_KEEP_ALIVE=-1" $args -}}
{{- else -}}
{{- $args = "OLLAMA_KEEP_ALIVE=-1" -}}
{{- end -}}
{{- end -}}
{{- if and $isCpu (not (contains "OLLAMA_NUM_GPU" $args)) -}}
{{- if $args -}}
{{- $args = printf "%s OLLAMA_NUM_GPU=0" $args -}}
{{- else -}}
{{- $args = "OLLAMA_NUM_GPU=0" -}}
{{- end -}}
{{- end -}}
{{- $args -}}
{{- end -}}
{{- /* ollamaornith35bv3.engineArgsForLlminit: user ENGINE_ARGS for llm-init only.
       Never inject OLLAMA_KEEP_ALIVE (llm-init forwards it on /api/chat as "-1").
       Strip if user set it; CPU mode adds OLLAMA_NUM_GPU=0 unless set.
       Usage: {{ include "ollamaornith35bv3.engineArgsForLlminit" (dict "Args" ($oe.ENGINE_ARGS | default "") "IsCpu" $isCpuMode) }} */ -}}
{{- define "ollamaornith35bv3.engineArgsForLlminit" -}}
{{- $in := . -}}
{{- $args := trim ($in.Args | default "") -}}
{{- $isCpu := $in.IsCpu | default false -}}
{{- $args = regexReplaceAll ` ?OLLAMA_KEEP_ALIVE=[^ ]+` "" $args -}}
{{- $args = regexReplaceAll ` +` " " $args -}}
{{- $args = trim $args -}}
{{- if and $isCpu (not (contains "OLLAMA_NUM_GPU" $args)) -}}
{{- if $args -}}
{{- $args = printf "%s OLLAMA_NUM_GPU=0" $args -}}
{{- else -}}
{{- $args = "OLLAMA_NUM_GPU=0" -}}
{{- end -}}
{{- end -}}
{{- $args -}}
{{- end -}}
