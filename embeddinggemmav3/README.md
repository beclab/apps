# embeddinggemmav3

Olares app for [google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m)
served by [IREmbeddingServer](https://github.com/beclab/IREmbeddingServer).

## Workloads

| Deployment | Role |
|------------|------|
| `{{ Release.Name }}` (= `embeddinggemmav3`) | embed-server engine（内部 `http://embed:8080`） |
| `llminit` | llm-init（`ENGINE_KIND=embed`）：下载 + API 代理（8090） |

## API 路径

| 入口 | 目标 | 说明 |
|------|------|------|
| embedclient / embedapi / shared entrance | `download-svc:8090` | llm-init 代理 `/v1/embeddings` 等到 embed-server |
| 集群内直连引擎 | `embedserver:8080` 或 `embed:8080` | 仅内部/debug；外部应走 llm-init |

## Accelerator → image mapping

| Mode | Docker image | `MODEL_ID` | `EMBED_DEVICE` | HF subdir |
|------|--------------|------------|----------------|-----------|
| `intel` | `beclab/embed-server:v0.1.0-ov-intel` | `embeddinggemma-300m-ov` | `igpu` | `openvino/` |
| `cpu` | `beclab/embed-server:v0.1.0-onnx-cpu` | `embeddinggemma-300m-onnx` | `cpu` | `onnx/` |
| `nvidia` | `beclab/embed-server:v0.1.0-onnx-cuda12` or `*-cuda13` | `embeddinggemma-300m-onnx` | `cuda` | `onnx/` |
| `nvidia-gb10` | `beclab/embed-server:v0.1.0-onnx-cuda13-gb10-arm64` | `embeddinggemma-300m-onnx` | `cuda` | `onnx/` |

## Model source (llm-init)

Unified repo: https://huggingface.co/beclab/embeddinggemma-300m

- Intel: `hf://beclab/embeddinggemma-300m --revision main --exclude onnx/** --subdir openvino`
- Others: `hf://beclab/embeddinggemma-300m --revision main --exclude openvino/** --subdir onnx`

## Images

| Component | Image |
|-----------|-------|
| embed-server | `beclab/embed-server:v0.1.0-*` |
| llm-init | `beclab/llm-init:test_v1` |

## Device mounts

- **intel:** `/dev/dri`, `/sys/class/drm` (+ privileged)
- **nvidia / nvidia-gb10:** Olares `gpu-inject` annotation

## Verify runtime device

```bash
curl -s http://<pod>:8080/v1/capabilities | jq '{configured_device_kind, inference_backend, cpu_fallback}'
```

## Upgrade notes

See [UPGRADE-v0.1.0.md](./UPGRADE-v0.1.0.md).
