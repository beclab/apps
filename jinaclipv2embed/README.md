# jinaclipv2embed

Olares app for [beclab/jina-clip-v2-split](https://huggingface.co/beclab/jina-clip-v2-split)
served by [IREmbeddingServer](https://github.com/beclab/IREmbeddingServer) via llm-init `ENGINE_KIND=clipembed`.

Replaces the legacy `jinaclipv2` stack (custom images + `/api/text/embed`). This app follows the same pattern as `embeddinggemmav3` and is aligned with `integration_test_clipembed.sh`.

## Workloads

| Deployment | Role |
|------------|------|
| `{{ Release.Name }}` (= `jinaclipv2embed`) | embed-server engine（内部 `http://clipembed:8080`） |
| `llminit` | llm-init（`ENGINE_KIND=clipembed`）：下载 + API 代理（8090） |

## API 路径

| 入口 | 目标 | 说明 |
|------|------|------|
| clipclient / clipapi / shared entrance | `download-svc:8090` | llm-init 代理 `/v1/embeddings` 等到 embed-server |
| 集群内直连引擎 | `embedserver:8080` 或 `clipembed:8080` | 仅内部/debug；外部应走 llm-init |

OpenAI-compatible endpoints:

- `POST /v1/embeddings` — text (`input` string) or image (`input` object + base64 data URL)
- `GET /v1/models` — model id `jina-clip-v2`

## Accelerator → image mapping

| Mode | Docker image | `MODEL_ID` | `EMBED_DEVICE` | HF subdir |
|------|--------------|------------|----------------|-----------|
| `intel` | `beclab/embed-server:v0.1.2-ov-intel` | `jina-clip-v2-split-ov` | `igpu` | `openvino/` |
| `cpu` | `beclab/embed-server:v0.1.2-onnx-cpu` | `jina-clip-v2-split-onnx` | `cpu` | `onnx/` |
| `nvidia` | `beclab/embed-server:v0.1.2-onnx-cuda12` or `*-cuda13` | `jina-clip-v2-split-onnx` | `cuda` | `onnx/` |
| `nvidia-gb10` | `beclab/embed-server:v0.1.2-onnx-cuda13-gb10-arm64` | `jina-clip-v2-split-onnx` | `cuda` | `onnx/` |

## Model source (llm-init)

Unified repo: https://huggingface.co/beclab/jina-clip-v2-split

- Intel: `hf://beclab/jina-clip-v2-split --revision main --exclude onnx/** --subdir openvino`
- Others: `hf://beclab/jina-clip-v2-split --revision main --exclude openvino/** --subdir onnx`

`MODEL_NAME=jina-clip-v2` (logical id for `/v1/models` and proxy rewrite).

## Images

| Component | Image |
|-----------|-------|
| embed-server | `beclab/embed-server:v0.1.2-*` |
| llm-init | `beclab/llm-init:v1.3.5` |

## Device mounts

- **intel:** `/dev/dri`, `/sys/class/drm` (+ privileged)
- **nvidia / nvidia-gb10:** Olares `gpu-inject` annotation

## Local integration test

```bash
bash /var/wangzhong/local-dev/llminit/integration_test_clipembed.sh
```

Uses the same `MODEL_SOURCE` / `MODEL_ID` / `ENGINE_KIND=clipembed` defaults as this chart.

## Resource profiling

```bash
bash /var/wangzhong/local-dev/llminit/integration_test_clipembed_resources.sh
```

Measured peaks (2026-08-10): see  
[`/var/wangzhong/local-dev/llminit/clipembed_resource_reports/Jina-CLIP-v2-资源画像.md`](/var/wangzhong/local-dev/llminit/clipembed_resource_reports/Jina-CLIP-v2-资源画像.md).

Summary: embed-server RAM ~**2.8 GiB** (OpenVINO) / ~**2.2 GiB** host RAM (NVIDIA steady); VRAM ~**9589 MiB**. Chart uses **3Gi/6Gi** pod memory and **`nvidia.com/gpumem: 10240`** on `nvidia`; **`nvidia-gb10`** uses unified memory (**10Gi/14Gi** embed-server, OlaresManifest **12Gi/16Gi**, no standalone GPU fields).

## Verify runtime device

```bash
curl -s http://<pod>:8080/v1/capabilities | jq '{configured_device_kind, inference_backend, cpu_fallback}'
```
