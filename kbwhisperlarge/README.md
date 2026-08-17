# KB Whisper Large for Olares

This package deploys the published image:

- `ghcr.io/progress44/rpi-system-kb-whisper-large:latest`

The app exposes OpenAI-compatible transcription with
`KBLab/kb-whisper-large` at:

- `http://kbwhisperlarge-svc:8000`

## Endpoints

- `GET /`
- `GET /health`
- `GET /v1/models`
- `POST /v1/audio/transcriptions`
- `POST /transcribe`

## Request example

```bash
curl -X POST http://kbwhisperlarge-svc:8000/v1/audio/transcriptions \
  -F "model=KBLab/kb-whisper-large" \
  -F "file=@./sample.wav" \
  -F "language=sv" \
  -F "response_format=json"
```

## Notes

- The first request may be slower while the model downloads and caches.
- Hugging Face cache persists under `userspace.appData`.
- Use Olares env variables `OLARES_USER_HUGGINGFACE_TOKEN` and
  `OLARES_USER_HUGGINGFACE_SERVICE` if needed for your environment.
