{{- /* Olares accelerator mode picked at install. app-service injects both
       .Values.gpu and .Values.GPU.Type from the selected resource mode;
       nvidia is the only mode OlaresManifest declares today. */ -}}
{{- define "flowstudio.gpuType" -}}
{{- $t := .Values.gpu | default "" -}}
{{- if not $t -}}
{{- $t = (.Values.GPU | default dict).Type | default "nvidia" -}}
{{- end -}}
{{- $t -}}
{{- end -}}

{{- /* ComfyUI engine image for the selected accelerator. This is the single
       source of truth: both the engine Deployment (which puts the image in
       the install-time pre-pull list) and the API's ENGINE_IMAGE read it, so
       what gets pulled and what EngineManager launches cannot drift. */ -}}
{{- define "flowstudio.engineImage" -}}
{{- $img := (.Values.engine | default dict).images | default dict -}}
{{- if eq (include "flowstudio.gpuType" .) "amd" -}}
{{- $img.amdGpu | default "docker.io/beclab/flowstudio:engine-1.0.6-rocm" -}}
{{- else -}}
{{- $img.nvidia | default "docker.io/beclab/flowstudio:engine-1.0.7" -}}
{{- end -}}
{{- end -}}
