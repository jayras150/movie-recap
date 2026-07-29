#!/usr/bin/env python3
"""
1_download.py — Mengunduh Video & Audio dari YouTube menggunakan yt-dlp.
Output:
  - downloads/video_original.mp4   (video + audio)
  - downloads/audio_original.wav   (audio stream saja)
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# ── Konfigurasi Logger ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("download")

OUTPUT_DIR = Path("downloads")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_youtube(url: str, output_dir: Path) -> tuple[Path, Path]:
    """
    Unduh video dan audio dari YouTube.
    Returns (video_path, audio_path).
    """
    video_path = output_dir / "video_original.mp4"
    audio_path = output_dir / "audio_original.wav"

    # ── Step 1: Download video (best quality) ──────────────
    log.info("Mengunduh video dari: %s", url)
    video_cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", str(video_path),
        "--progress",
        "--no-playlist",
        "--no-overwrites",
        url,
    ]
    log.info("CMD: %s", " ".join(video_cmd))
    try:
        subprocess.run(video_cmd, check=True)
    except subprocess.CalledProcessError as e:
        log.error("Gagal mengunduh video: %s", e)
        raise

    # ── Step 2: Ekstrak audio WAV ──────────────────────────
    if not audio_path.exists():
        log.info("Mengekstrak audio ke WAV...")
        audio_cmd = [
            "yt-dlp",
            "-x", "--audio-format", "wav",
            "-o", str(audio_path.with_suffix(".%(ext)s")),
            "--no-playlist",
            "--no-overwrites",
            url,
        ]
        log.info("CMD: %s", " ".join(audio_cmd))
        try:
            subprocess.run(audio_cmd, check=True)
        except subprocess.CalledProcessError as e:
            log.error("Gagal mengekstrak audio: %s", e)
            raise
    else:
        log.info("Audio sudah ada, lewati ekstraksi.")

    # Rename jika yt-dlp memberi nama berbeda
    expected_audio = audio_path
    if not expected_audio.exists():
        for f in output_dir.glob("*.wav"):
            if "audio_original" not in f.name:
                f.rename(expected_audio)
                break

    # Verifikasi file
    if not video_path.exists():
        raise FileNotFoundError(f"Video tidak ditemukan: {video_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio tidak ditemukan: {audio_path}")

    log.info("Video  → %s  (%d MB)", video_path, video_path.stat().st_size // 1024 // 1024)
    log.info("Audio  → %s  (%d MB)", audio_path, audio_path.stat().st_size // 1024 // 1024)
    return video_path, audio_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Unduh video YouTube untuk pipeline movie recap.")
    parser.add_argument("url", help="URL video YouTube")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="Direktori output (default: downloads/)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    try:
        download_youtube(args.url, output_dir)
    except Exception as e:
        log.error("Download gagal: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
