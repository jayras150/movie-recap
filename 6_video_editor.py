#!/usr/bin/env python3
"""
6_video_editor.py — Menggabungkan audio narasi TTS dengan video asli.
Suara asli video dikecilkan volumenya menjadi background.

Input:
  - downloads/video_original.mp4  (video asli)
  - downloads/narration.wav       (narasi TTS)
  - downloads/bgm.wav             (BGM/instrumen asli — opsional)
Output:
  - output/final_video.mp4        (video final siap upload)
"""

import argparse
import logging
import subprocess
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
log = logging.getLogger("video_editor")

OUTPUT_DIR = Path("downloads")
FINAL_DIR = Path("output")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_ffmpeg_path() -> str:
    """Cari FFmpeg binary di system."""
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg tidak ditemukan. Install dengan: apt-get install ffmpeg")
    log.info("Menggunakan FFmpeg: %s", ffmpeg)
    return ffmpeg


def get_media_duration(file_path: Path) -> float:
    """Dapatkan durasi media dalam detik menggunakan ffprobe."""
    ffprobe = "ffprobe"
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(file_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception as e:
        log.warning("Gagal mendapat durasi: %s", e)
        return 0.0


def mix_audio_tracks(
    video_path: Path,
    narration_path: Path,
    bgm_path: Path | None,
    output_path: Path,
    ffmpeg: str,
) -> Path:
    """
    Mix audio: narasi (full volume) + video asli (latar, volume kecil) + BGM (opsional).
    """
    log.info("Mixing audio tracks...")

    # Durasi untuk referensi
    video_dur = get_media_duration(video_path)
    nar_dur = get_media_duration(narration_path)
    log.info("Video durasi: %.1f dtk | Narasi: %.1f dtk", video_dur, nar_dur)

    # ── Bangun filter complex audio ─────────────────────────
    # Stream mapping:
    #   0:v = video (original)
    #   0:a = audio original (video)
    #   1:a = narasi TTS
    #   2:a = BGM (opsional)

    filter_chains = []

    # Audio original: kecilkan volumenya jadi 15%
    filter_chains.append(
        "[0:a]volume=0.15[orig_low]"
    )

    if bgm_path and bgm_path.exists():
        # BGM: kecilkan volume jadi 10%, jangan sampai timbulkan noise
        filter_chains.append(
            "[2:a]volume=0.10[bgm_low]"
        )
        # Mix orig + bgm + narasi
        filter_chains.append(
            "[orig_low][bgm_low][1:a]amix=inputs=3:duration=first:dropout_transition=2[audio_out]"
        )
        input_files = [
            "-i", str(video_path),
            "-i", str(narration_path),
            "-i", str(bgm_path),
        ]
    else:
        # Mix orig + narasi saja
        filter_chains.append(
            "[orig_low][1:a]amix=inputs=2:duration=first:dropout_transition=2[audio_out]"
        )
        input_files = [
            "-i", str(video_path),
            "-i", str(narration_path),
        ]

    filter_complex = "; ".join(filter_chains)

    log.info("Filter complex: %s", filter_complex)

    # ── FFmpeg command ──────────────────────────────────────
    cmd = [
        ffmpeg,
        "-y",  # overwrite tanpa konfirmasi
    ] + input_files + [
        "-filter_complex", filter_complex,
        "-map", "[audio_out]",  # audio hasil mix
        "-map", "0:v",          # video asli
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",            # potong sesuai durasi terpendek (narasi)
        "-movflags", "+faststart",
        str(output_path),
    ]

    log.info("Memulai rendering video...")
    log.debug("CMD: %s", " ".join(cmd))

    start_time = time.time()

    try:
        process = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        elapsed = time.time() - start_time
        log.info("Rendering selesai dalam %.1f dtk!", elapsed)

        # Log FFmpeg output jika ada warning
        if process.stderr:
            for line in process.stderr.strip().split("\n"):
                if "error" in line.lower():
                    log.error("FFmpeg: %s", line.strip())
                elif "warning" in line.lower():
                    log.warning("FFmpeg: %s", line.strip())

    except subprocess.CalledProcessError as e:
        log.error("FFmpeg gagal! RC=%d", e.returncode)
        log.error("STDERR:\n%s", e.stderr[:2000])
        raise

    # Verifikasi output
    if not output_path.exists():
        raise FileNotFoundError(f"File output tidak ditemukan: {output_path}")

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    log.info("Video final → %s (%.1f MB)", output_path, file_size_mb)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Gabungkan narasi TTS dengan video asli.")
    parser.add_argument("--video", default=str(OUTPUT_DIR / "video_original.mp4"),
                        help="Path video asli")
    parser.add_argument("--narration", default=str(OUTPUT_DIR / "narration.wav"),
                        help="Path audio narasi TTS")
    parser.add_argument("--bgm", default=str(OUTPUT_DIR / "bgm.wav"),
                        help="Path audio BGM (opsional, kosongkan untuk skip)")
    parser.add_argument("--output", default=str(FINAL_DIR / "final_video.mp4"),
                        help="Path output video final")
    parser.add_argument("--no-bgm", action="store_true",
                        help="Jangan gunakan BGM walaupun file bgm.wav ada")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        log.error("File video tidak ditemukan: %s", video_path)
        sys.exit(1)

    narration_path = Path(args.narration)
    if not narration_path.exists():
        log.error("File narasi tidak ditemukan: %s", narration_path)
        sys.exit(1)

    bgm_path = Path(args.bgm) if not args.no_bgm else None
    if bgm_path and not bgm_path.exists():
        log.warning("File BGM tidak ditemukan: %s — mixing tanpa BGM.", bgm_path)
        bgm_path = None

    output_path = Path(args.output)
    ensure_dir(output_path.parent)

    try:
        ffmpeg = get_ffmpeg_path()
        mix_audio_tracks(
            video_path=video_path,
            narration_path=narration_path,
            bgm_path=bgm_path,
            output_path=output_path,
            ffmpeg=ffmpeg,
        )
    except Exception as e:
        log.error("Video editing gagal: %s", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
