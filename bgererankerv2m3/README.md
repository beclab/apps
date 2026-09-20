# bgererankerv2m3

Olares app for [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)
served by [rerank-server](https://github.com/beclab/rerank) + llm-init (`ENGINE_KIND=rerank`).

Resource sizing from `/var/wangzhong/local-dev/llminit/rerank_resource_reports/rerank-resource-report-20260907.md`.

## Workloads

| Deployment | Role |
|------------|------|
| `{{ Release.Name }}` (= `bgererankerv2m3`) | rerank-server engine（内部 `http://rerank:8080`） |
| `llminit` | llm-init（`ENGINE_KIND=rerank`）：下载 + API 代理（8090） |

## API 路径

| 入口 | 目标 | 说明 |
|------|------|------|
| rerankclient / rerankapi / shared entrance | `download-svc:8090` | llm-init 代理 `/v1/rerank`、`/v1/models` 等到 rerank-server |
| 集群内直连引擎 | `rerankserver:8080` 或 `rerank:8080` | 仅内部/debug；外部应走 llm-init |

## Accelerator → image mapping

| Mode | Docker image | `ACCELERATOR` | `RERANK_RUNTIME` | HF subdir |
|------|--------------|---------------|------------------|-----------|
| `intel` (integrated) | `beclab/rerank-server:v0.0.1-ov-intel-amd64` | `intel` | `openvino` | `openvino/` |
| `intel-gpu` (discrete) | `beclab/rerank-server:v0.0.1-ov-intel-amd64` | `intel-gpu` | `openvino` | `openvino/` |
| `cpu` | `beclab/rerank-server:v0.0.1-onnx-cpu` | `cpu` | `onnx` | `onnx/` |
| `nvidia` | `beclab/rerank-server:v0.0.1-onnx-cuda12` or `*-cuda13` | `nvidia` | `onnx` | `onnx/` |
| `nvidia-gb10` | `beclab/rerank-server:v0.0.1-onnx-cuda13-gb10-arm64` | `nvidia-gb10` | `onnx` | `onnx/` |

## Naming contract

- llm-init: `MODEL_NAME` = `MODEL_ID` = `bge-reranker-v2-m3`
- rerank-server: `MODEL_ID` only

## Model source (llm-init)

Unified repo: https://huggingface.co/beclab/bge-reranker-v2-m3

- Intel integrated and discrete: `hf://beclab/bge-reranker-v2-m3 --revision main --exclude onnx/** --subdir openvino`
- Others: `hf://beclab/bge-reranker-v2-m3 --revision main --exclude openvino/** --subdir onnx`

## Images

| Component | Image |
|-----------|-------|
| rerank-server | `beclab/rerank-server:v0.0.1-*` |
| llm-init | `beclab/llm-init:v1.7.21` |

## Resource profile (steady-state inference)

| Mode | Engine RAM | GPU VRAM | CPU (inference) |
|------|------------|----------|-----------------|
| cpu | ~1.4 GiB | — | ~1 core |
| nvidia | ~0.7 GiB | ~3.2 GiB | low |
| intel | ~0.75 GiB* | iGPU shared | low* |

\*OpenVINO compile may spike RAM ~3.2 GiB and CPU ~2.7 cores on first start.

## Device mounts

- **intel / intel-gpu:** `/dev/dri`, `/sys/class/drm` (+ privileged)
- **nvidia / nvidia-gb10:** Olares `gpu-inject` annotation

## Smoke test

```bash
curl -s http://<llm-init>:8090/v1/models
curl -s http://<llm-init>:8090/v1/rerank \
  -H 'Content-Type: application/json' \
  -d '{"model":"bge-reranker-v2-m3","query":"what is a panda?","documents":["the giant panda lives in China","quantum computing"]}'
```

## Intel discrete GPU deployment

- Select Olares compute mode `intel-gpu` for a discrete Intel GPU, or `intel` for an integrated GPU. Both use the OpenVINO image and model; the engine receives the exact selected mode.
- The engine image must contain the hardware-selection refactor: `intel` requires an Intel `INTEGRATED` device and `intel-gpu` requires an Intel `DISCRETE` device. Missing matching devices must fail startup, rather than falling back to another GPU type or CPU. Verify the deployed image digest; a reused tag or cached old image is not evidence of compatibility.
- Discrete mode adds the deployment `gpu-inject` annotation and pod `gpu.bytetrade.io/required-gpu-memory` / `limited-gpu-memory` annotations, matching the existing Intel discrete convention in `llamacppllmbasev3`. It does not request NVIDIA resources.
- Initial discrete VRAM budget: 4096Mi required / 6144Mi limit. This is a starting deployment budget, not a measured Intel dGPU peak or a guarantee of hardware-enforced memory isolation. Validate against the target card, driver, Olares version and request sizes.
- Both Intel modes retain the existing `/dev/dri`, `/sys/class/drm` mounts and privileged execution. All mounted devices may be visible; the runtime enforces the requested device type. This does not implement exclusive per-card assignment or multi-GPU load balancing.
- This chart change does not publish a new engine image. Target-host acceptance must verify OpenVINO detects a DISCRETE device, the engine becomes ready, and `/v1/rerank` through llm-init returns valid scores. Hardware and image compatibility require a real Intel dGPU test.
