# embeddinggemmav3

Olares app for [google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m)
served by [IREmbeddingServer](https://github.com/beclab/IREmbeddingServer).

## Workloads

| Deployment | Role |
|------------|------|
| `{{ Release.Name }}` (= `embeddinggemmav3`) | embed-server engine |
| `llminit` | llm-init download-only sidecar |
| `embedconsole` | Web Console (nginx + React SPA, `console` entrance) |

## Accelerator → image mapping

| Mode | Docker image | `MODEL_ID` | `EMBED_DEVICE` |
|------|--------------|------------|----------------|
| `cpu` | `beclab/embed-server:v0.1.0-ov-intel` | `embeddinggemma-300m-ov` | `auto` |
| `nvidia` | `beclab/embed-server:v0.1.0-onnx-cuda12` or `*-cuda13` | `embeddinggemma-300m-onnx` | `cuda` |
| `nvidia-gb10` | `beclab/embed-server:v0.1.0-onnx-cuda13` | `embeddinggemma-300m-onnx` | `cuda` |
| `strix-halo` | `beclab/embed-server:v0.1.0-onnx-rocm-amd64` | `embeddinggemma-300m-onnx` | `rocm` |

## Model sources (llm-init)

- https://huggingface.co/wangzhong/embeddinggemma-300m-ov
- https://huggingface.co/wangzhong/embeddinggemma-300m-onnx-export

## Device mounts

- **cpu (ov-intel):** `/dev/dri`, `/sys/class/drm`
- **strix-halo:** `/dev/dri`, `/sys/class/drm`, `/dev/kfd` (+ privileged)
- **nvidia / nvidia-gb10:** Olares `gpu-inject` annotation

## Verify runtime device

```bash
curl -s http://<pod>:8080/v1/capabilities | jq '{configured_device_kind, inference_backend, cpu_fallback}'
```
