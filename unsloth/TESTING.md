# Unsloth 0.0.7 runtime regression

Tested on 2026-10-20 with Olares 1.12.7, amd64, an NVIDIA RTX 5090 Laptop GPU
(24 GiB, TimeSlice), and `unsloth/unsloth:nightly-2026.10.10`. The application and
all dependency installation tests run as UID/GID 1000. The image is unchanged.

## Changes under test

- uv and pip caches use app-private node-local Cache storage.
- uv's `[pip].target` configuration and `PIP_TARGET` install dynamic packages into
  `Data/unsloth/studio/runtime-packages/<image-tag>`. Studio and its children load
  that directory through `PYTHONPATH`. A new image tag gets a separate directory
  for compiled Python/PyTorch/CUDA extensions.
- `HF_HUB_DISABLE_XET=1` is set before the backend and workers start.
- A small, checked backport terminates and reaps the training worker's descendants
  before finalizing forced cancellation. The existing job identity guard,
  cooperative stop/save and history finalization remain unchanged. Cancellation
  escalates after 15 seconds; process cleanup and finalization can add time.
- An init container prepares the patched module in an ephemeral volume. The main
  container mounts it read-only. Unexpected source layouts fail initialization.
  The Pod template includes the patch checksum so patch changes trigger rollout.

The backport is specific to the pinned Studio image. Review/remove it when an
upstream image includes equivalent descendant cleanup; do not carry it across an
image upgrade without running the regression tests.

## Final inline-package retest

The complete device suite was rerun after moving the compatibility code into
`runtime-configmap.yaml`, against runtime commit
`5767d401dc5366c1bd37d5e8878b613cb774511c`. The tested 0.0.7 package SHA256 is
`49dbf18ee7ad2828b08e94ff00660c15c6125f24d370ebbeabca0558a130cb8f`.
The backport regression used the script extracted from this package. The deployed
ConfigMap and generated backend module were checked, and the package contains no
standalone Python files. All results below describe this fresh run.

## Results

| Check | Result |
| --- | --- |
| Olares chart lint, owner and non-owner render scenarios | Pass |
| Baseline 0.0.5 install, upgrade to candidate | Pass |
| UID 1000 offline uv and pip installations into the configured directory | Pass |
| Real `causal-conv1d` installation and fresh-process CUDA extension import | Pass |
| Dependency persistence and fresh-process CUDA import after a full app restart | Pass |
| Fresh-cache HTTP download of an Xet-backed official Hub weight | Pass |
| Backport regression, including a real installer ignoring SIGTERM, baseline orphan reproduction, and superseded-worker guard | 5 passed |
| Upstream stop watchdog, terminal state, start idempotency, and shutdown/save tests | 112 passed |
| Browser after restart: cancel during model loading, reload twice | Pass; stopped state remained stable, configuration page restored without a stop dialog or worker |
| Qwen3.5-2B two-step QLoRA through Studio API, adapter saved | Pass; step 2/2, final loss 1.302319 |
| Configured Hub mirror, fresh-cache HTTP weight download | Pass with a 60-second transfer timeout in the test process |
| Jupyter authenticated login and kernelspec API | Pass |
| Final candidate: cancel while preparing/importing, terminal stability | Pass; stopped about 16 seconds after cancel, no remaining training workers |
| Final candidate: cancel after a real optimizer step, terminal stability | Pass; stopped about 2 seconds after cancel, output directory cleared; no final adapter saved |

The HTTP test downloaded `hf-internal-testing/tiny-random-LlamaForCausalLM` /
`model.safetensors` into a new temporary cache. Xet metadata was present; the test
forbids calling `xet_get` and verifies `http_get` was called. The result was
4,131,280 bytes with SHA256
`49c20f32c6c597480fcaec5df2f86c645eabea765cbea1e67886dbae45e5c992`.
The device's configured Hub mirror does not return Xet metadata, so the
Xet-specific assertion was tested against `https://huggingface.co` in the test
process only.
The mirror initially hit the library's default transfer timeout. Retesting with
`HF_HUB_DOWNLOAD_TIMEOUT=60` in the test process succeeded with the same SHA256;
the application's configured Hub endpoint and timeout were not changed. The
download fixture is pinned to revision `9fb191250dd56d0ba7ec9785a025ed29c03d5998`.

The completed training saved a 21,851,336-byte `adapter_model.safetensors`, also verified after the full app restart. The real CUDA wheel was reinstalled with uv using the configured writable target; no pip fallback was used.
The image logged torch.compile eager-fallback warnings during the first run;
training completed and the adapter was saved. The completed GPU worker used the
existing upstream post-completion retirement watchdog before a subsequent run
could start. The test harness waits for that exit; the chart changes the
cancel-without-save timeout, not the post-completion timeout.

The upstream tests need the actual training module preloaded because the
watchdog test's import stubs otherwise mask `utils.paths.storage_roots` during
collection. No upstream test files were changed. The final run produced 112
passes with existing dependency deprecation/syntax warnings.

## Validation setup

The disposable verification scripts are kept locally and are not included in
this PR. The cancellation compatibility code is embedded in the ConfigMap; the
init container reads it as `/runtime-config/prepare-runtime.py`.

The training validation used `Qwen/Qwen3.5-2B`, 32 rows from
`mlabonne/FineTome-100k`, QLoRA, sequence length 128, batch size 1, LoRA rank 8,
and two steps for completion. Cancellation cases used a longer run. The checks
verified a nonempty adapter and stable terminal state after cancellation and
page reload.

For the upstream suite, preload `core.training.training` with the backend source
directory on `sys.path`, then run pytest on:

- `tests/test_training_stop_watchdog.py`
- `tests/test_training_status_terminal.py`
- `tests/test_training_start_idempotency.py`
- `tests/test_training_shutdown_stop.py`

Use a writable pytest cache such as `/tmp/unsloth-pytest-cache`.
