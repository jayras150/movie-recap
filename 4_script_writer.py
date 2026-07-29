#!/usr/bin/env python3
"""
4_script_writer.py — Menulis skrip narasi ala YouTuber recap film menggunakan Qwen3-VL-8B-Instruct
(kuantisasi 4-bit NF4 via BitsAndBytes agar VRAM ~6.5 GB).

Input:
  - downloads/transcript.json  (hasil transkripsi)
  - downloads/video_original.mp4  (untuk konteks visual — opsional)
Output:
  - downloads/narration_script.txt  (skrip narasi final 300-500 kata)
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
log = logging.getLogger("script_writer")

OUTPUT_DIR = Path("downloads")

# ── Konstanta Chunking ──────────────────────────────────────
MAX_CHUNK_DURATION_SEC = 900   # 15 menit per chunk
MAX_CHUNK_WORDS = 4000         # fallback jika timestamp tidak tersedia


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_transcript(transcript_path: Path) -> list[dict]:
    """Muat transcript.json."""
    with open(transcript_path, "r", encoding="utf-8") as f:
        return json.load(f)


def chunk_transcript(segments: list[dict]) -> list[list[dict]]:
    """
    Membagi segmen transkrip per 10-15 menit (chunking).
    Returns list of chunks, setiap chunk berisi list segmen.
    """
    chunks: list[list[dict]] = []
    current_chunk: list[dict] = []
    chunk_start_time = 0.0

    for seg in segments:
        seg_start = seg.get("start", 0.0)
        if current_chunk and (seg_start - chunk_start_time) > MAX_CHUNK_DURATION_SEC:
            chunks.append(current_chunk)
            current_chunk = []
            chunk_start_time = seg_start
        current_chunk.append(seg)

    if current_chunk:
        chunks.append(current_chunk)

    log.info("Transcript dibagi menjadi %d chunk (maks %d menit/chunk)", len(chunks), MAX_CHUNK_DURATION_SEC // 60)
    return chunks


def chunk_to_text(chunk: list[dict]) -> str:
    """Konversi satu chunk ke teks polos dengan timestamp."""
    lines = []
    for seg in chunk:
        start = seg.get("start_str", f"{seg['start']:.1f}")
        end = seg.get("end_str", f"{seg['end']:.1f}")
        lines.append(f"[{start} → {end}] {seg['text']}")
    return "\n".join(lines)


def build_prompt(transcript_text: str, chunk_idx: int, total_chunks: int) -> str:
    """Bangun prompt untuk Qwen3-VL."""
    part_info = f" (Bagian {chunk_idx + 1} dari {total_chunks})" if total_chunks > 1 else ""

    prompt = f"""Kamu adalah seorang content creator YouTube yang terkenal dengan gaya narasi film yang santai, seru, dan engaging.

Berikut adalah transkrip dialog dari sebuah film{part_info}:

--- TRANSCRIPT MULAI ---
{transcript_text}
--- TRANSCRIPT SELESAI ---

Tugas kamu:
1. Pahami adegan dan dialog dari transkrip di atas.
2. Buatlah skrip narasi ulang (movie recap) dalam Bahasa Indonesia, dengan gaya khas YouTuber recap film:
   - Santai dan mengalir seperti ngobrol dengan teman.
   - Gunakan bahasa sehari-hari yang hidup, bukan bahasa formal kaku.
   - Tambahkan elemen "oh wow", "gila sih", "makanya", dll. yang natural.
   - Ceritakan ulang dengan urutan kronologis yang mudah diikuti.
   - Beri sedikit komentar atau reaksi pribadi yang lucu/menarik di sela-sela cerita.
   - Jangan gunakan format label "Pembukaan", "Isi", "Penutup". Cukup narasi mengalir.
   - Akhiri dengan kalimat penutup yang mengajak viewer like & subscribe secara natural.

Panjang skrip: sekitar 300-500 kata untuk keseluruhan film.
{("Setiap bagian harus bisa berdiri sendiri tetapi tetap nyambung dengan bagian sebelumnya.") if total_chunks > 1 else ""}
"""
    return prompt


def call_qwen_chunk(
    chunk_text: str,
    chunk_idx: int,
    total_chunks: int,
    model_name: str = "Qwen/Qwen3-VL-8B-Instruct",
) -> str:
    """
    Panggil Qwen3-VL-8B-Instruct untuk satu chunk.
    Model di-load dengan 4-bit quantization agar VRAM ~6.5 GB.
    """
    from transformers import Qwen3VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
    import torch

    # ── Konfigurasi 4-bit quantization ──────────────────────
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    log.info("Memuat model Qwen3-VL-8B-Instruct (4-bit NF4)...")
    load_start = time.time()

    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )
    processor = AutoProcessor.from_pretrained(
        model_name,
        trust_remote_code=True,
    )

    log.info("Model dimuat dalam %.1f dtk", time.time() - load_start)

    # ── Siapkan prompt ──────────────────────────────────────
    prompt = build_prompt(chunk_text, chunk_idx, total_chunks)
    messages = [
        {"role": "system", "content": "Kamu adalah narator YouTube recap film yang santai dan seru."},
        {"role": "user", "content": prompt},
    ]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs = processor(
        text=[text],
        padding=True,
        return_tensors="pt",
    ).to(model.device)

    # ── Generate ────────────────────────────────────────────
    log.info("Mengenerate skrip chunk %d/%d...", chunk_idx + 1, total_chunks)
    gen_start = time.time()

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=2048,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.05,
            do_sample=True,
        )

    # Decode
    generated_ids = generated_ids[0][inputs["input_ids"].shape[1]:]
    output_text = processor.decode(generated_ids, skip_special_tokens=True)

    elapsed = time.time() - gen_start
    log.info("Selesai generate dalam %.1f dtk (%d tokens)", elapsed, len(generated_ids))

    # Bersihkan VRAM
    del model
    del processor
    torch.cuda.empty_cache()

    return output_text.strip()


def write_final_script(chunks_output: list[str], output_path: Path) -> None:
    """Gabungkan hasil semua chunk dan simpan."""
    full_script = "\n\n".join(chunks_output)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_script)

    word_count = len(full_script.split())
    log.info("Skrip narasi final tersimpan di: %s", output_path)
    log.info("Total kata: %d", word_count)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hasilkan skrip narasi recap film dari transkrip.")
    parser.add_argument("--transcript", default=str(OUTPUT_DIR / "transcript.json"),
                        help="Path ke transcript JSON")
    parser.add_argument("--output", default=str(OUTPUT_DIR / "narration_script.txt"),
                        help="Path output skrip narasi")
    parser.add_argument("--model", default="Qwen/Qwen3-VL-8B-Instruct",
                        help="Nama model Qwen3-VL")
    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        log.error("File transcript tidak ditemukan: %s", transcript_path)
        sys.exit(1)

    output_path = Path(args.output)
    ensure_dir(output_path.parent)

    try:
        # 1. Load transcript
        segments = load_transcript(transcript_path)
        log.info("Loaded %d segmen transkrip.", len(segments))

        # 2. Chunking
        chunks = chunk_transcript(segments)
        log.info("Total chunk: %d", len(chunks))

        # 3. Proses setiap chunk
        chunk_results = []
        for idx, chunk in enumerate(chunks):
            chunk_text = chunk_to_text(chunk)
            log.info("=== Memproses chunk %d/%d (%d segmen, %d karakter) ===",
                     idx + 1, len(chunks), len(chunk), len(chunk_text))

            result = call_qwen_chunk(
                chunk_text=chunk_text,
                chunk_idx=idx,
                total_chunks=len(chunks),
                model_name=args.model,
            )
            chunk_results.append(result)
            log.info("Chunk %d selesai.", idx + 1)

        # 4. Gabungkan & simpan
        write_final_script(chunk_results, output_path)

    except Exception as e:
        log.error("Pembuatan skrip gagal: %s", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
