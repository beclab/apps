# Olares provider endpoint adaptation

Upstream: `nexu-io/open-design`, tag `open-design-v0.22.1`.

`apply-provider-hosts.mjs` runs before compilation. It adds the hostname from
the user-configured HTTP(S) model Base URL to a request-local allowlist. This
covers model discovery, connection checks, chat proxy requests and handoff
summaries. It neither persists hosts nor mutates the process environment, so
changing a provider URL leaves no stale global allowance behind.

The upstream URL syntax/protocol checks remain active. URLs supplied by upstream
responses, such as generated asset download links, retain their separate strict
SSRF validation and do not inherit this allowance.

Patch contexts must match exactly once; a changed upstream implementation fails
the build instead of silently omitting the adaptation. Both target images run
`provider-hosts.test.mjs` against the compiled daemon module during construction.
This checks private provider endpoints, invalid protocols and isolation from
asset-download validation. Actual model quality and generation need separate
user testing.
