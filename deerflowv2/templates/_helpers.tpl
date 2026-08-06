{{/*
Resolve AUTH_JWT_SECRET with two-tier precedence:

  1. Existing `deerflowv2-auth-secret` Secret in this namespace — preserves
     the value across `helm upgrade` so previously issued JWTs (and therefore
     active user sessions) keep validating after a chart bump.
  2. Fresh `randAlphaNum 64` — first install only.

A rotating secret would invalidate every active session on every helm
upgrade, which is hostile UX for users who only see "logged out, please
sign in again" each time the operator pushes a chart fix.

Returned verbatim (unquoted); callers must quote and b64enc as needed.
*/}}
{{- define "deerflowv2.authJwtSecret" -}}
{{- $existing := lookup "v1" "Secret" .Release.Namespace "deerflowv2-auth-secret" -}}
{{- if and $existing $existing.data (index $existing.data "AUTH_JWT_SECRET") -}}
{{- index $existing.data "AUTH_JWT_SECRET" | b64dec -}}
{{- else -}}
{{- randAlphaNum 64 -}}
{{- end -}}
{{- end -}}
