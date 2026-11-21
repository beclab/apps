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

{{- define "strata.hfPath" -}}
/cache/hf/hub
{{- end -}}

{{- define "strata.runStateSubpath" -}}
{{- /* Readiness, model_path and model-spec belong to one model identity.
       Include MODEL_SOURCE (and any pinned revision) so an upgrade cannot
       inherit an old ready sentinel or model card. Keep ENGINE_ARGS out:
       tuning/restarts must preserve the user's card for the same model.
       Both Deployments share this identity; legacy migration uses it too. */ -}}
{{- $oe := .Values.olaresEnv | default dict -}}
{{- $identity := list ($oe.MODEL_NAME | default "") ($oe.MODEL_SOURCE | default "") | toJson | sha256sum | trunc 20 -}}
{{- printf "llm-init-run/%s/model-%s" .Release.Name $identity -}}
{{- end -}}

{{- define "strata.runStateHostPath" -}}
{{- $us := .Values.userspace | default dict -}}
{{- printf "%s/%s" ($us.appCommon | default "/olares/common") (include "strata.runStateSubpath" .) -}}
{{- end -}}
