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
{{- /* llamacppqwen3827bggufv3.presetArgs: resolve the shared-pool preset for an
       install whose stored ENGINE_ARGS matches a previous default preset.
       Both the engine container and llm-init must call this: llm-init's value
       becomes the model card, and Router derives admission width from that
       card. Match complete old presets rather than individual flags,
       which would also catch a hand-tuned -np 12. Keep $preset byte-identical
       to ENGINE_ARGS.default in OlaresManifest.yaml.
       Usage: {{ include "llamacppqwen3827bggufv3.presetArgs" ($oe.ENGINE_ARGS | default "") }} */ -}}
{{- define "llamacppqwen3827bggufv3.presetArgs" -}}
{{- $args := trim (. | default "") -}}
{{- $preset := "-c 104448 -ngl all -fa on -ctk q8_0 -ctv q8_0 --jinja -np 2 -kvu --spec-type draft-mtp --spec-draft-n-max 2" -}}
{{- $stale := "-c 104448 -ngl all -fa on -ctk q8_0 -ctv q8_0 --jinja -np 1 --spec-type draft-mtp --spec-draft-n-max 4" -}}
{{- $previous := "-c 104448 -ngl all -fa on -ctk q8_0 -ctv q8_0 --jinja -np 2 -kvu --spec-type draft-mtp --spec-draft-n-max 4" -}}
{{- if or (eq $args "") (eq $args $stale) (eq $args $previous) -}}
{{- $preset -}}
{{- else -}}
{{- $args -}}
{{- end -}}
{{- end -}}
{{- /* llamacppqwen3827bggufv3.engineArgs: pass ENGINE_ARGS through unchanged.
       Usage: {{ include "llamacppqwen3827bggufv3.engineArgs" (dict "Args" $engineArgs) }} */ -}}
{{- define "llamacppqwen3827bggufv3.engineArgs" -}}
{{- $in := . -}}
{{- trim ($in.Args | default "") -}}
{{- end -}}
