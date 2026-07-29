#!/usr/bin/env python3
"""
5_tts.py — Mengubah skrip narasi menjadi audio WAV menggunakan OmniVoice.
Input : downloads/narration_script.txt
Output: downloads/narration.wav
"""

import argparse
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
log = logging.getLogger("tts")

OUTPUT_DIR = Path("downloads")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def generate_tts(
    script_path: Path,
    output_path: Path,
    model_name: str = "k2-fsa/OmniVoice",
    voice: str = "default",
    device: str = "cuda",
) -> Path:
    """
    Generate audio narasi dari teks skrip menggunakan OmniVoice.
    OmniVoice menggunakan parameter device_map=, bukan device=.
    """
    import torch

    # ── CUDA/CPU fallback logic ─────────────────────────────
    if device == "cuda" and not torch.cuda.is_available():
        log.warning("CUDA tidak tersedia, fallback ke CPU")
        device = "cpu"

    # OmniVoice menerima device_map, bukan device
    # "cuda" → "cuda:0" , "cpu" → "cpu"
    device_map = f"{device}:0" if device == "cuda" else device

    # Baca skrip
    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read().strip()

    if not script_text:
        raise ValueError("Skrip narasi kosong!")

    word_count = len(script_text.split())
    log.info("Memproses TTS untuk %d kata...", word_count)
    log.info("Model: %s | Voice: %s | Device: %s", model_name, voice, device_map)

    try:
        from omnivoice import OmniVoice
    except ImportError as e:
        log.error("OmniVoice tidak terinstall: %s", e)
        raise

    # Muat model
    log.info("Memuat model OmniVoice...")
    load_start = time.time()
    tts = OmniVoice.from_pretrained(model_name, device_map=device_map)
    log.info("Model dimuat dalam %.1f dtk", time.time() - load_start)

    # Generate audio
    log.info("Mengenerate audio narasi... (ini akan memakan waktu proporsional dengan panjang teks)")
    gen_start = time.time()

    # OmniVoice biasanya mengembalikan audio sebagai numpy array (sample_rate, audio_data)
    audio_output = tts.generate(script_text, voice=voice)

    # Simpan sebagai WAV
    import soundfile as sf

    if isinstance(audio_output, tuple):
        # (audio_data, sample_rate) atau (sample_rate, audio_data)
        if len(audio_output) == 2:
            if isinstance(audio_output[0], int):
                sample_rate = audio_output[0]
                audio_data = audio_output[1]
            else:
                audio_data = audio_output[0]
                sample_rate = audio_output[1]
        else:
            raise ValueError(f"Format output OmniVoice tidak dikenal: {type(audio_output)}")
    elif hasattr(audio_output, "sample_rate"):
        sample_rate = audio_output.sample_rate
        audio_data = audio_output.audio
    else:
        # Fallback: asumsikan audio_data dengan sample rate default 24000
        audio_data = audio_output
        sample_rate = 24000
        log.warning("Menggunakan sample rate default 24000 Hz")

    sf.write(str(output_path), audio_data, sample_rate)
    elapsed = time.time() - gen_start

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    duration_sec = len(audio_data) / sample_rate if hasattr(audio_data, '__len__') else 0
    log.info("Audio narasi selesai dalam %.1f dtk", elapsed)
    log.info("Output  → %s (%.1f MB, ~%.1f dtk, %d Hz)",
             output_path, file_size_mb, duration_sec, sample_rate)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TTS narasi dari skrip.")
    parser.add_argument("--script", default=str(OUTPUT_DIR / "narration_script.txt"),
                        help="Path ke skrip narasi (default: downloads/narration_script.txt)")
    parser.add_argument("--output", default=str(OUTPUT_DIR / "narration.wav"),
                        help="Path output audio WAV (default: downloads/narration.wav)")
    parser.add_argument("--model", default="k2-fsa/OmniVoice", help="Nama/model OmniVoice")
    parser.add_argument("--voice", default="default", help="Voice ID (default: default)")
    parser.add_argument("--device", default="cuda", help="Device: cuda atau cpu")
    args = parser.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        log.error("File skrip tidak ditemukan: %s", script_path)
        sys.exit(1)

    output_path = Path(args.output)
    ensure_dir(output_path.parent)

    try:
        generate_tts(
            script_path=script_path,
            output_path=output_path,
            model_name=args.model,
            voice=args.voice,
            device=args.device,
        )
    except Exception as e:
        log.error("TTS gagal: %s", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
