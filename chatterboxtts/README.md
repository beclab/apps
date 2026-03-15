# Chatterbox TTS for Olares

This package deploys the published image:

- `ghcr.io/progress44/rpi-system-chatterbox-tts:latest`

The app expects an NVIDIA-capable `amd64` Olares node and uses the configured
public image directly.

## API

Base service inside the cluster:

- `http://chatterboxtts-svc:8000`

Endpoints:

- `GET /`
  - Service metadata and docs path.
- `GET /health`
  - Health status, CUDA visibility, and GPU count.
- `GET /v1/models`
  - Available model ids.
- `POST /tts`
  - Native JSON synthesis endpoint.
- `POST /v1/audio/speech`
  - OpenAI-compatible speech endpoint.
- `POST /v1/audio/speech/upload`
  - Multipart endpoint with uploaded reference audio.

## Request examples

Native JSON request:

```bash
curl -X POST http://chatterboxtts-svc:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Olares","audio_format":"wav"}' \
  --output speech.wav
```

OpenAI-style request:

```bash
curl -X POST http://chatterboxtts-svc:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"turbo","input":"This is a CUDA-backed speech request.","response_format":"wav"}' \
  --output speech.wav
```

OpenAI-style multilingual request:

```bash
curl -X POST http://chatterboxtts-svc:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"multilingual","input":"Hej fran Olares","language":"sv","response_format":"wav"}' \
  --output speech-sv.wav
```

Reference voice upload:

```bash
curl -X POST http://chatterboxtts-svc:8000/v1/audio/speech/upload \
  -F "input=Hej från Olares" \
  -F "language=sv" \
  -F "reference_audio=@./reference.wav" \
  --output speech.wav
```

## Notes

- `/v1/audio/speech` respects the request `model` value and can switch between
  `turbo`, `english`, and `multilingual` within the same deployment.
- `CHATTERBOX_MODEL` remains the default model for endpoints that do not accept
  a `model` field.
- `language` only applies when the selected model is multilingual.
- `reference_voice` in JSON requests must refer to a file already present in
  `/data/reference-voices`.
- The first synthesis request downloads model files and warms the runtime.

## Registry auth

The published GHCR image is public, so this package does not require registry
credentials or image pull secrets during installation.

For Hugging Face downloads, the chart maps Olares system env values
`OLARES_USER_HUGGINGFACE_SERVICE` and `OLARES_USER_HUGGINGFACE_TOKEN` into the
container as `HF_ENDPOINT` and `HF_TOKEN`.

The container is configured to run as a non-root user so it can satisfy
Olares admission policy for public registries.

On Olares, the pod runs as UID/GID `1000` so the mounted `userspace.appData`
paths remain writable without a privileged init container.

Recommended sizing for this package:

- CPU: 4
- RAM: 12Gi
- VRAM: 12Gi to 16Gi

The runtime also disables numba JIT caching to avoid a known `librosa/numba`
startup failure in this containerized deployment.

The image also pins `numba==0.61.2` and `llvmlite==0.44.0` so the Chatterbox
import path stays compatible with the deployed Python stack.

The chart keeps `reference-voices`, Hugging Face cache, and Torch cache under
`userspace.appData` for persistence.

On Olares with HAMI, the chart now requests one GPU and sets
`nvidia.com/gpumem: 12288` for both requests and limits.

## Operational logging

Every request now includes an `X-Request-Id` response header. Use that id to
correlate client failures with pod logs.

Tail logs:

```bash
kubectl logs -n chatterboxtts-progress44 deploy/chatterboxtts -f
```

The service logs:

- request start and completion
- synthesis success with endpoint, model family, language, format, text length,
  reference source, output bytes, and duration
- synthesis failures with request id and traceback
- startup configuration, including model, device, CUDA visibility, and cache
  directories

The service logs metadata only and does not log full request text.
