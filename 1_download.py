#!/usr/bin/env python3
"""
1_download.py — Mengunduh Video & Audio dari YouTube menggunakan yt-dlp.

Output:
  - downloads/video_original.mp4
  - downloads/audio_original.wav

Jika terdapat file cookies.txt di folder project,
yt-dlp akan otomatis menggunakannya.

Persyaratan:
  - Node.js 22+
  - yt-dlp
  - yt-dlp-ejs
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger("download")

OUTPUT_DIR = Path("downloads")
COOKIES_FILE = Path("cookies.txt")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_common_args(url: str) -> list[str]:
    args = [
        "--no-playlist",
        "--no-overwrites",

        # Gunakan Node untuk menyelesaikan YouTube JS Challenge
        "--js-runtimes",
        "node",

        # Ambil komponen challenge solver terbaru
        "--remote-components",
        "ejs:github",

        # Gunakan client Android agar lebih stabil
    ]

    if COOKIES_FILE.exists():
        log.info("Menggunakan cookies: %s", COOKIES_FILE)
        args.extend([
            "--cookies",
            str(COOKIES_FILE),
        ])
    else:
        log.warning(
            "cookies.txt tidak ditemukan. "
            "Jika YouTube meminta login ('Sign in to confirm you're not a bot'), "
            "tambahkan cookies.txt ke folder project."
        )

    args.append(url)
    return args


def download_youtube(url: str, output_dir: Path) -> tuple[Path, Path]:
    video_path = output_dir / "video_original.mp4"
    audio_path = output_dir / "audio_original.wav"

    log.info("Mengunduh video dari: %s", url)

    video_cmd = [
        "yt-dlp",
        "-f",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        str(video_path),
        "--progress",
    ]

    video_cmd.extend(build_common_args(url))

    log.info("CMD: %s", " ".join(video_cmd))

    try:
        subprocess.run(video_cmd, check=True)
    except subprocess.CalledProcessError as e:
        log.error("Gagal mengunduh video: %s", e)
        raise

    if not video_path.exists():
        raise FileNotFoundError(f"Video tidak ditemukan: {video_path}")

    log.info("Mengekstrak audio WAV...")

    audio_template = output_dir / "audio_original.%(ext)s"

    audio_cmd = [
        "yt-dlp",
        "-x",
        "--audio-format",
        "wav",
        "-o",
        str(audio_template),
    ]

    audio_cmd.extend(build_common_args(url))

    log.info("CMD: %s", " ".join(audio_cmd))

    try:
        subprocess.run(audio_cmd, check=True)
    except subprocess.CalledProcessError as e:
        log.error("Gagal mengekstrak audio: %s", e)
        raise

    if not audio_path.exists():
        candidates = sorted(output_dir.glob("audio_original*.wav"))
        if candidates:
            candidates[0].rename(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio tidak ditemukan: {audio_path}")

    log.info(
        "Video  → %s (%d MB)",
        video_path,
        video_path.stat().st_size // 1024 // 1024,
    )

    log.info(
        "Audio  → %s (%d MB)",
        audio_path,
        audio_path.stat().st_size // 1024 // 1024,
    )

    return video_path, audio_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unduh video YouTube untuk pipeline movie recap."
    )

    parser.add_argument(
        "url",
        help="URL video YouTube",
    )

    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Direktori output (default: downloads/)",
    )

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