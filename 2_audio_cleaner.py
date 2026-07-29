#!/usr/bin/env python3
"""
2_audio_cleaner.py — Memisahkan Vokal dari BGM menggunakan Demucs v4 (HTDemucs).
Input : downloads/audio_original.wav
Output: downloads/vocals.wav  (vokal bersih)
        downloads/bgm.wav     (background music / instrument)
"""

import argparse
import logging
import shutil
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning, module="demucs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("audio_cleaner")

OUTPUT_DIR = Path("downloads")
DEMUCS_OUTPUT_DIR = Path("separated")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def separate_vocals(input_wav: Path, output_dir: Path) -> tuple[Path, Path]:
    """
    Gunakan Demucs HTDemucs untuk memisahkan vokal dan bgm.
    Returns (vocals_path, bgm_path).
    """
    log.info("Memuat model Demucs (HTDemucs) — first load mungkin perlu waktu...")

    # Import inside function agar error handling lebih baik
    try:
        from demucs import separate
        from demucs.apply import BagOfModels
        from demucs.pretrained import get_model
    except ImportError as e:
        log.error("Demucs tidak terinstall dengan benar: %s", e)
        raise

    # Demucs secara default menyimpan hasil di folder "separated/htdemucs/<filename>/"
    # Kita panggil via CLI agar konsisten
    log.info("Memproses pemisahan audio: %s", input_wav.name)
    import subprocess

    import torch

    # Deteksi device: prioritaskan CUDA
    demucs_device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info("Demucs device: %s", demucs_device)

    cmd = [
        sys.executable, "-m", "demucs",
        "--two-stems", "vocals",       # pisahkan vocals vs no_vocals
        "--device", demucs_device,      # paksa CUDA/CPU eksplisit
        "-o", str(DEMUCS_OUTPUT_DIR),
        str(input_wav),
    ]
    log.info("CMD: %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        log.error("Demucs gagal: %s", e.stderr)
        raise

    # Demucs output: separated/htdemucs/audio_original/vocals.wav
    stem_dir = DEMUCS_OUTPUT_DIR / "htdemucs" / input_wav.stem
    vocals_source = stem_dir / "vocals.wav"
    no_vocals_source = stem_dir / "no_vocals.wav"

    if not vocals_source.exists():
        raise FileNotFoundError(f"Hasil vokal tidak ditemukan: {vocals_source}")
    if not no_vocals_source.exists():
        raise FileNotFoundError(f"Hasil BGM tidak ditemukan: {no_vocals_source}")

    # Salin ke output
    vocals_dest = output_dir / "vocals.wav"
    bgm_dest = output_dir / "bgm.wav"

    shutil.copy2(vocals_source, vocals_dest)
    shutil.copy2(no_vocals_source, bgm_dest)

    log.info("Vokal → %s  (%d MB)", vocals_dest, vocals_dest.stat().st_size // 1024 // 1024)
    log.info("BGM   → %s  (%d MB)", bgm_dest, bgm_dest.stat().st_size // 1024 // 1024)

    return vocals_dest, bgm_dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Pisahkan vokal dari BGM menggunakan Demucs.")
    parser.add_argument("--input", default=str(OUTPUT_DIR / "audio_original.wav"),
                        help="Path ke audio input (default: downloads/audio_original.wav)")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR),
                        help="Direktori output (default: downloads/)")
    args = parser.parse_args()

    input_wav = Path(args.input)
    if not input_wav.exists():
        log.error("File input tidak ditemukan: %s", input_wav)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    try:
        separate_vocals(input_wav, output_dir)
    except Exception as e:
        log.error("Pemisahan audio gagal: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
