# ============================================================
# Dockerfile — Movie Recap Pipeline
# Production-ready image dengan model AI di-download saat runtime
# ============================================================
ARG BASE_IMAGE=pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.title="Movie Recap Pipeline"
LABEL org.opencontainers.image.description="AI-powered YouTube video recap automation pipeline"
LABEL org.opencontainers.image.source="https://github.com/k2-fsa/OmniVoice"

# ── Hindari interaktif ──────────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ── System dependencies ─────────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        curl \
        ca-certificates \
        libsndfile1 \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ── Model cache directories ─────────────────────────────────
ENV HF_HOME=/models/huggingface
ENV HUGGINGFACE_HUB_CACHE=/models/huggingface/hub
ENV TRANSFORMERS_CACHE=/models/huggingface
ENV TORCH_HOME=/models/torch
ENV XDG_CACHE_HOME=/models/cache
ENV DEMUCS_CACHE=/models/demucs
ENV WHISPER_CACHE=/models/whisper

RUN mkdir -p /models/huggingface/hub \
             /models/torch \
             /models/cache \
             /models/demucs \
             /models/whisper \
             /app/downloads \
             /app/output

# ── Install Python dependencies dengan cache layer optimal ──
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt

# ── Copy source code ────────────────────────────────────────
COPY 1_download.py \
     2_audio_cleaner.py \
     3_transcribe.py \
     4_script_writer.py \
     5_tts.py \
     6_video_editor.py \
     run_pipeline.sh \
     entrypoint.sh \
     /app/

RUN chmod +x /app/run_pipeline.sh /app/entrypoint.sh

# ── Setup symlink untuk Demucs agar pake cache kita ────────
RUN ln -s /models/torch /root/.cache/torch 2>/dev/null || true

# ── Working directory ───────────────────────────────────────
WORKDIR /app

# ── Entrypoint ──────────────────────────────────────────────
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["--help"]
