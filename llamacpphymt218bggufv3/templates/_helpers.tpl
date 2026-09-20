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
{{- /* llamacpphymt218bggufv3.presetArgs: resolve the speed preset for an install
       whose stored ENGINE_ARGS predates it. Both the engine container and
       llm-init must call this: llm-init's value becomes the model card, and
       Router derives admission width from that card, so an engine given more
       slots than the card declares gets refused traffic it could serve.
       $stale* match the whole previous presets rather than a lone "-np N",
       which would also catch -np 16, and which would override a hand-tuned value.
       Keep $preset byte-identical to ENGINE_ARGS.default in OlaresManifest.yaml.
       Usage: {{ include "llamacpphymt218bggufv3.presetArgs" ($oe.ENGINE_ARGS | default "") }} */ -}}
{{- define "llamacpphymt218bggufv3.presetArgs" -}}
{{- $args := trim (. | default "") -}}
{{- $preset := "-c 65536 -ngl all -fa on -ctk q4_0 -ctv q4_0 --jinja -np 16 -kvu" -}}
{{- $stale := "-c 32768 -ngl all -fa on -ctk q4_0 -ctv q4_0 --jinja -np 1" -}}
{{- $stale6 := "-c 32768 -ngl all -fa on -ctk q4_0 -ctv q4_0 --jinja -np 6" -}}
{{- $stale8 := "-c 32768 -ngl all -fa on -ctk q4_0 -ctv q4_0 --jinja -np 8" -}}
{{- if or (eq $args "") (contains "-c 8192" $args) (contains "-c 131072" $args) (eq $args $stale) (eq $args $stale6) (eq $args $stale8) -}}
{{- $preset -}}
{{- else -}}
{{- $args -}}
{{- end -}}
{{- end -}}
{{- /* llamacpphymt218bggufv3.engineArgs: CPU mode auto-adds -ngl 0 unless user set -ngl.
       Usage: {{ include "llamacpphymt218bggufv3.engineArgs" (dict "Args" $engineArgs "IsCpu" $isCpuMode) }} */ -}}
{{- define "llamacpphymt218bggufv3.engineArgs" -}}
{{- $in := . -}}
{{- $args := trim ($in.Args | default "") -}}
{{- $isCpu := $in.IsCpu | default false -}}
{{- if and $isCpu (not (contains "-ngl" $args)) -}}
{{- if $args -}}
{{- $args = printf "%s -ngl 0" $args -}}
{{- else -}}
{{- $args = "-ngl 0" -}}
{{- end -}}
{{- end -}}
{{- $args -}}
{{- end -}}
