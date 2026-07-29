#!/usr/bin/env python3
"""
3_transcribe.py — Mentranskripsi audio vokal menggunakan Faster-Whisper Large-v3.
Input : downloads/vocals.wav
Output: downloads/transcript.json  (teks + timestamp per segmen)
"""

import argparse
import json
import logging
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("transcribe")

OUTPUT_DIR = Path("downloads")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def format_timestamp(seconds: float) -> str:
    """Konversi detik ke format HH:MM:SS.mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def transcribe_audio(
    audio_path: Path,
    model_name: str = "Systran/faster-whisper-large-v3",
    device: str = "cuda",
    compute_type: str = "float16",
    language: str = "id",
) -> list[dict]:
    """
    Transkripsi audio vokal menggunakan Faster-Whisper.
    Returns list of segments: [{start, end, text}, ...]
    """
    import torch

    # ── CUDA/CPU fallback logic ─────────────────────────────
    if device == "cuda" and not torch.cuda.is_available():
        log.warning("CUDA tidak tersedia, fallback ke CPU dengan compute_type=int8")
        device = "cpu"
        compute_type = "int8"
    elif device == "cpu" and compute_type == "float16":
        log.warning("compute_type=float16 tidak didukung di CPU, fallback ke int8")
        compute_type = "int8"

    log.info("Memuat model Faster-Whisper: %s", model_name)
    log.info("Device: %s | Compute: %s | Language: %s", device, compute_type, language)

    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        log.error("faster-whisper tidak terinstall: %s", e)
        raise

    model = WhisperModel(model_name, device=device, compute_type=compute_type)

    log.info("Memulai transkripsi: %s", audio_path)
    start_time = time.time()

    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=500,
            threshold=0.5,
        ),
    )

    result = []
    segment_count = 0
    for seg in segments:
        segment_count += 1
        entry = {
            "id": seg.id,
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "start_str": format_timestamp(seg.start),
            "end_str": format_timestamp(seg.end),
            "text": seg.text.strip(),
        }
        result.append(entry)
        if segment_count <= 3 or segment_count % 50 == 0:
            log.info("  Seg %3d: [%s → %s] %s",
                     seg.id, entry["start_str"], entry["end_str"],
                     entry["text"][:80])

    elapsed = time.time() - start_time
    log.info("Transkripsi selesai dalam %.1f detik — %d segmen.", elapsed, len(result))

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Transkripsi audio vokal dengan Faster-Whisper.")
    parser.add_argument("--input", default=str(OUTPUT_DIR / "vocals.wav"),
                        help="Path ke audio vokal (default: downloads/vocals.wav)")
    parser.add_argument("--output", default=str(OUTPUT_DIR / "transcript.json"),
                        help="Path output transcript JSON (default: downloads/transcript.json)")
    parser.add_argument("--model", default="Systran/faster-whisper-large-v3",
                        help="Nama model Faster-Whisper")
    parser.add_argument("--device", default="cuda", help="Device: cuda atau cpu")
    parser.add_argument("--compute-type", default="float16", help="Compute type: float16, int8_float16, dll.")
    parser.add_argument("--language", default="id", help="Kode bahasa (default: id untuk Bahasa Indonesia)")
    args = parser.parse_args()

    audio_path = Path(args.input)
    if not audio_path.exists():
        log.error("File audio tidak ditemukan: %s", audio_path)
        sys.exit(1)

    output_path = Path(args.output)
    ensure_dir(output_path.parent)

    try:
        segments = transcribe_audio(
            audio_path,
            model_name=args.model,
            device=args.device,
            compute_type=args.compute_type,
            language=args.language,
        )

        # Simpan transcript.json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)
        log.info("Transcript tersimpan di: %s (%d segmen)", output_path, len(segments))

    except Exception as e:
        log.error("Transkripsi gagal: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
