# Chart 1.0.24: unchanged legacy-key upgrade recovery

The prior 1.0.23 candidate failed on a real test-market installation because LiteLLM 1.106.2 refuses the historical public default master key. Earlier safe-key and explicit-rotation tests did not cover that unchanged-key case. This follow-up keeps LiteLLM 1.106.2 and does **not** rotate API keys automatically.

## Compatibility boundary

- Only a Helm **upgrade** whose current master-key SHA256 matches the upstream historical-default fingerprint renders `LITELLM_DANGEROUSLY_PERMIT_WEAK_OR_UNSET_MASTER_KEY=true`.
- Fresh installs, secure keys, empty keys and unset keys render the override false. Fresh install input validation requires `sk-` followed by at least 32 alphanumeric characters; an actual default-key new-install attempt was rejected with `Invalid values: LITELLM_MASTER_KEY`.
- This deliberately retains the existing public-default-key risk for affected legacy installations. It is a compatibility measure, not a security improvement. Upstream describes the override as development-only. Owners should schedule a separate voluntary key rotation, after updating callers and migrating encrypted secrets; that is not a prerequisite for this upgrade.
- Existing master/virtual keys and provider credentials are preserved. The UI environment-login toggle is independent: create/verify an independent Proxy Admin before disabling bootstrap UI login.
- The backup directory is now `appData/backups/chart-1.0.24`; earlier-version backup markers do not suppress this version's backup.

## Repeated end-to-end checks, 2026-10-22, olarestest01 / amd64

| Path | Result |
| --- | --- |
| Actual 1.103.0 / chart 1.0.22 with unchanged historical default → 1.106.2 / chart 1.0.24 | Passed, same Upload installation; no uninstall |
| Actual 1.83.3 / chart 1.0.21 with unchanged historical default → 1.106.2 / chart 1.0.24 | Passed, same Upload installation; no uninstall |
| Fresh target with random strong master key | Passed; override=false, independent-admin invitation/login and bootstrap login passed |
| Fresh target with historical default | Correctly rejected by installation input validation |

Both old-version fixtures preserved team/model IDs, virtual-key hash/model allowlist/team relationships, persistent-file SHA256, admin login and post-upgrade metadata writes. Database backups completed for both upgrades. The 1.83.3 path additionally stored a real scoped Router credential and two model configurations **before** upgrading; ordinary and streaming default-chat calls worked on the old version.

After upgrade, the original real model IDs and virtual key still worked, and the stored Router credential decrypted/forwarded successfully. Real checks passed: ordinary chat, SSE, tool calling plus tool-result continuation, strict JSON schema, Anthropic Messages, Responses-to-chat translation, a call using the unchanged legacy master key, and model-allowlist rejection (403). The default Router route was not changed.

An initial real-test harness read failed because its own checkpoint was created root-owned mode 0600 on the old image. Only that exact disposable test file was re-owned to UID/GID 1000 in the isolated test namespace; no user file or recursive ownership change was made, and this test-only step is not in the production chart. The corrected assertions then passed. Product state is stored in PostgreSQL; no direct database edits or re-encryption were used for compatibility.

The user's existing market.test instance was repaired in place by adding the authorized compatibility environment override to its Deployment, after verifying its key fingerprint. The entire key Secret was compared before/after and was unchanged. The app resumed, its existing UI credentials logged in (303), and the unchanged master key authenticated `/model/info`; the returned model list was empty, so no existing user-configured model inference is claimed for that live instance. A further app restart preserved recovery. The live instance is retained; only isolated test aliases are cleanup targets.

## Earlier 1.0.23 verification (historical record)

# LiteLLM 1.106.2 verification

Tested on 2026-10-22 with Olares 1.12.7-20260908, an amd64 node, and Chart 1.0.23. This is a test-market candidate; independent colleague smoke testing and public-market publication remain outstanding.

## Installation and upgrade paths

| Path | Result |
| --- | --- |
| Market Chart 1.0.22 / LiteLLM 1.103.0 to Chart 1.0.23 / 1.106.2, in place through Upload | Passed |
| Historical Chart 1.0.21 / LiteLLM 1.83.3 to Chart 1.0.23 / 1.106.2, in place through an isolated Upload application | Passed |
| Chart 1.0.23 / 1.106.2 in an isolated application and database | Passed |

Both upgrade paths preserved seeded team/model IDs, virtual-key model permissions and team relations, and the SHA256 of a persistent test file. Existing virtual keys remained usable and team metadata remained writable. PostgreSQL custom-format backups completed before migration; the init container checks that the dump is nonempty and that `pg_restore --list` succeeds. Full restore rehearsal and whole-database row comparisons were not performed.

The historical test alias initially had an incorrect internal proxy Service reference. Its baseline installation was corrected and its seed data recreated **before** starting the recorded in-place migration. No uninstall/reinstall was used to claim migration success.

## Real model integration

The target version was additionally tested through the existing Olares Router's `default-chat` route, which resolved to Qwen3.8-27B via llama.cpp. The default route/provider configuration was unchanged. The test credential was restricted to `default-chat` and had a one-hour expiry. Test models and credentials are runtime data and are absent from this chart.

| Check | Result |
| --- | --- |
| Non-streaming chat through a LiteLLM virtual key | Exact expected response and nonzero usage |
| Streaming chat | Content, multiple SSE chunks, final usage and `[DONE]` received |
| Function calling | Tool name/arguments returned in `choices[0]`; a second request used the supplied tool result |
| Streaming function calling | Tool-call arguments reconstructed correctly and stream completed |
| Parallel function calling | Both requested functions returned with distinct IDs |
| Strict JSON schema output | Parsed JSON matched the requested values |
| Anthropic Messages-compatible endpoint | Expected text and usage returned through Router |
| Responses-to-chat bridge | Expected final message returned; reasoning and final-message items kept separate |
| Virtual-key model allowlist | Unauthorized model returned HTTP 403 |
| Usage logging | Model calls and token totals appeared in LiteLLM SpendLogs and Router usage |
| Restart persistence | Same model IDs and virtual key worked after an application restart; stored Router credential forwarded successfully |

The bridge used a separate runtime `custom_openai/default-chat` model configuration, so a chat-only upstream could serve the Responses-compatible request through translation. It is not a claim that Router offers a native Responses provider for this model.

## Relevant newer-version behavior

- `/v1/messages/count_tokens` returned a positive token count and `litellm_count_source=local_estimate`; this is an estimate, not a claim of the provider's exact tokenizer count.
- An exhausted test key returned HTTP 422, without successful inference.
- `/v1/responses/compact` rejected an unmanaged `previous_response_id` with HTTP 403.
- `PATCH /credentials/{name}` rejected renaming with HTTP 400 when supplied with the required request fields. Dummy credentials were cleaned up.
- An isolated master-key rotation re-encrypted three stored values. Original model/key relationships still worked, and another restart with the old-key migration variable removed succeeded.
- Browser login, the new Home usage summary, command-palette search/navigation, and the redesigned Usage page were checked. A real Playground call returned the expected text and displayed token/latency information. Reasoning could be collapsed separately.

Expected authorization/budget denials appear as failed requests in the usage UI; they are intentional negative tests. Early Responses assertions incorrectly concatenated reasoning with the final message, and an early credential update omitted a required field. Corrected test requests/assertions passed; neither required a chart or application-code workaround.

## Compatibility and limits

- New installations require a strong master key. Chart 1.0.24 preserves an existing historical default during a Helm upgrade using the narrowly scoped compatibility rule documented below. Rotation is optional and separate: if an old key encrypted stored credentials, set `LITELLM_MIGRATE_FROM_MASTER_KEY` alongside the new key, verify migration success, then clear the migration field and update master-key callers as necessary.
- UI users must sign in again after the old session-format transition. stdio MCP defaults and upstream MCP credentials, cache message limits, and Responses WebSocket session limits require review for customized installations.
- The Olares CLI environment editor rejected an update because it also submitted the noneditable `SMTP_ENABLED` field. Rotation was verified using isolated test-only chart overrides; the Olares settings UI rotation workflow itself was not tested.
- Main container UID/GID 1000, actual workload image, healthy database readiness, successful migration logs, and zero restart counts were checked. An existing `trusted_proxy_ranges` warning does not block the tested workflows. The environment-credential-login warning is handled by the administrator onboarding workflow below.
- Image availability and matching source/destination config digests were checked for amd64 and arm64; runtime verification was amd64 only. No independent signature verification was performed.
- No tests claim coverage of standalone Lens/ClickHouse, Decisions providers, Bedrock-specific counting, real paid-provider pricing, OAuth, SMTP delivery, large-batch pricing, MCP servers, or long-running WebSocket behavior, since those services were not configured for this run.
- v1.103.0 is in the affected range of [GHSA-7hp6-4w63-5g45](https://github.com/BerriAI/litellm/security/advisories/GHSA-7hp6-4w63-5g45); the target includes that fix. The separate [October 21 supply-chain incident](https://docs.litellm.ai/blog/security-incident-oct-21-2026) recommends pinning 1.106.2. This verification is not a penetration test or a claim of zero remaining vulnerabilities.

Cleanup completed: the test application was uninstalled, its Upload record removed, and both inventories checked for absence. The temporary scoped Router key was disabled and its status verified. The default-chat target was unchanged. No --delete-data operation was used.


## Independent administrator login and red-banner migration

`DISABLE_ENV_CREDENTIAL_LOGIN` is a new editable Olares boolean (default `false`). It renders a real YAML boolean in `general_settings.disable_env_credential_login`. It is also mapped into the Deployment environment so an Olares Apply changes the pod template and restarts the process; a ConfigMap subPath alone would retain the old configuration until restart. Existing values without the new field render `false`.

User workflow (also included in the listing and upgrade notes in all seven supported locales):

1. Sign in with the existing `UI_USERNAME` / `UI_PASSWORD` bootstrap account.
2. Under **Internal Users**, create a separate **Proxy Admin** with an email address different from the bootstrap username. Generate/copy its invitation link, and use that link to set the account's own password. Copying the invitation link does not require SMTP delivery.
3. Verify the independent account in a private browser window, including an admin-only page. Keep bootstrap access enabled until this succeeds.
4. Open **Olares Settings → Applications → LiteLLM → Manage environment variables**. Edit `DISABLE_ENV_CREDENTIAL_LOGIN` to `true`, confirm, then **Apply**.
5. Wait for the automatic application restart and sign in with the independent account. The environment-credential red warning is no longer advertised by readiness details. The old bootstrap username/password is rejected; master API authentication remains available.
6. To recover bootstrap access if the independent account is unavailable, use the same Olares settings page to set the field back to `false` and Apply. This deliberately restores the warning as well.

The default stays `false` for both new installs and upgrades: automatically disabling the only verified login before the user creates an account would lock administrators out. Changing the Olares UI_PASSWORD field does not change an independent database account's password. Existing sessions are not asserted to be revoked by this toggle.

Follow-up validation on `olarestest01`, amd64, LiteLLM 1.106.2, isolated `litellmlogin622`:

- Created an independent Proxy Admin through `/user/new`, `/invitation/new`, and the onboarding token/claim flow; the user set its own password through the invitation API. No direct database edits or SMTP sends were used.
- Initial bootstrap and independent account login returned HTTP 303. Independent session authorized `/user/info`, and readiness details showed the environment warning.
- After disabling, the same independent account still returned 303 and authorized an admin read; bootstrap login returned 401, `show_env_credential_login_warning=false`, and master-key `/model/info` remained available.
- The Olares **settings UI**, rather than the CLI editor, successfully saved/applied the setting. The CLI editor still fails because it resubmits noneditable `SMTP_ENABLED`.
- The first draft changed only the ConfigMap and did not restart on Apply. The final Deployment mapping fixes that; UI changes between false and true produce replacement pods. Recovery to false restored bootstrap login (303) and the warning, without losing the independent administrator.

The isolated testing chart used alias-specific app/database names and random disposable bootstrap defaults; these are not included in this chart. Its test-only chart patch is 1.0.24 so the corrected Deployment could be upgraded in place; the submitted chart stays 1.0.23, the single patch above the remote baseline.

Final follow-up: a second UI Apply to `true` replaced the recovered pod, and all disabled-login assertions passed again. Browser sign-in with the independent administrator succeeded on the final configuration; Home displayed the Admin account with no environment-credential warning. The warning was not dismissed using browser storage or hidden by a UI patch. The temporary login credential file was deleted immediately after filling the browser form.

Cleanup: the follow-up test application and both Upload versions were removed, with absence verified. No persistent data/backup purge was requested or performed.
