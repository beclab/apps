# Preserve the tested CUDA 12.8 runtime and Olares defaults while applying
# every upstream source change between v1.0.7 and v1.0.8.
FROM beclab/harveyff-whisper-webui@sha256:68d2eb0456940f4594e7ccfaf7a6d67d8e9954750b5f0a86bb3de01892883dde
ARG UPSTREAM_COMMIT=4b65d5cfc3cec880926d5b5de0a7bec3f6bcd7dc
RUN python -c "import importlib.metadata as m; assert m.version('torchaudio').split('+')[0] == '2.8.0'" \
    && curl -fsSL "https://github.com/jhj0517/Whisper-WebUI/archive/${UPSTREAM_COMMIT}.tar.gz" -o /tmp/whisper-upstream.tar.gz \
    && mkdir /tmp/whisper-upstream \
    && tar -xzf /tmp/whisper-upstream.tar.gz -C /tmp/whisper-upstream --strip-components=1 \
    && cp /tmp/whisper-upstream/app.py /Whisper-WebUI/app.py \
    && cp /tmp/whisper-upstream/modules/utils/files_manager.py /Whisper-WebUI/modules/utils/files_manager.py \
    && cp /tmp/whisper-upstream/requirements.txt /Whisper-WebUI/requirements.txt \
    && cp /tmp/whisper-upstream/configs/translation.yaml /Whisper-WebUI/configs_default/translation.yaml \
    && printf '1.0.8\n' > /Whisper-WebUI/VERSION \
    && printf '%s\n' "${UPSTREAM_COMMIT}" > /Whisper-WebUI/UPSTREAM_REVISION \
    && chown 1000:1000 /Whisper-WebUI \
    && rm -rf /tmp/whisper-upstream /tmp/whisper-upstream.tar.gz
ENV HOME=/tmp PYTHONUSERBASE=/tmp/python-packages
USER 1000:1000
LABEL org.opencontainers.image.version="1.0.8" \
      org.opencontainers.image.source="https://github.com/jhj0517/Whisper-WebUI"
