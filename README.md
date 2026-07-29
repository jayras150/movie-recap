# 🎬 Movie Recap Pipeline

Sistem otomatisasi pembuat alur cerita (movie recap) berbasis AI yang siap di-deploy dan dijalankan di **Vast.ai Instance** (Ubuntu Linux, GPU Nvidia RTX 3060 12GB VRAM).

## 📋 Daftar Isi

- [Fitur](#fitur)
- [Persyaratan Sistem](#persyaratan-sistem)
- [Struktur Proyek](#struktur-proyek)
- [Cara Menjalankan](#cara-menjalankan)
  - [1. Upload Proyek ke Vast.ai](#1-upload-proyek-ke-vastai)
  - [2. Setup Environment (Sekali Saja)](#2-setup-environment-sekali-saja)
  - [3. Jalankan Pipeline](#3-jalankan-pipeline)
  - [4. Pipeline Per-Modul (Manual)](#4-pipeline-per-modul-manual)
- [Deskripsi Modul](#deskripsi-modul)
- [Alur Pipeline](#alur-pipeline)
- [Manajemen VRAM](#manajemen-vram)
- [Troubleshooting](#troubleshooting)
- [Referensi](#referensi)

---

## ✨ Fitur

- ✅ **Download Video YouTube** — Unduh video + audio dengan `yt-dlp`
- ✅ **Pemisahan Vokal** — Pisahkan vokal dari BGM menggunakan **Demucs v4 (HTDemucs)**
- ✅ **Transkripsi Akurat** — Transkripsi vokal ke teks dengan **Faster-Whisper Large-v3**
- ✅ **Penulisan Skrip AI** — Buat skrip narasi gaya YouTuber recap film dengan **Qwen3-VL-8B-Instruct** (kuantisasi 4-bit)
- ✅ **Text-to-Speech** — Ubah skrip jadi audio narasi dengan **OmniVoice**
- ✅ **Video Editing** — Gabungkan narasi + video asli + BGM dengan **FFmpeg**
- ✅ **Modular** — Setiap modul adalah skrip Python terpisah
- ✅ **Manajemen VRAM** — VRAM dibersihkan antar modul agar tidak overload
- ✅ **Orkestrasi Otomatis** — Satu perintah untuk seluruh pipeline

---

## 💻 Persyaratan Sistem

| Komponen | Spesifikasi |
|----------|-------------|
| **OS** | Ubuntu 22.04+ (Vast.ai / Linux) |
| **GPU** | Nvidia RTX 3060 12GB VRAM (atau GPU lain dengan ≥10GB VRAM) |
| **CUDA** | 12.1 |
| **RAM** | Minimal 16GB |
| **Storage** | Minimal 20GB (untuk model + video) |
| **Python** | 3.10+ |

---

## 📁 Struktur Proyek

```
/workspace/movie-recap/
├── setup.sh                 # ⚙️ Instalasi awal environment (jalankan sekali)
├── requirements.txt         # 📦 Daftar dependensi Python
├── 1_download.py            # 🎥 Download YouTube video & audio
├── 2_audio_cleaner.py       # 🔊 Pemisahan vokal (Demucs)
├── 3_transcribe.py          # 📝 Transkripsi (Faster-Whisper)
├── 4_script_writer.py       # ✍️ Pembuatan skrip narasi (Qwen3-VL)
├── 5_tts.py                 # 🗣️ Text-to-Speech (OmniVoice)
├── 6_video_editor.py        # 🎬 Video editing final (FFmpeg)
├── run_pipeline.sh          # 🚀 Master orchestrator (satu perintah)
├── README.md                # 📖 Dokumentasi ini
├── downloads/               # 📂 Folder output sementara (dibuat otomatis)
└── output/                  # 📂 Folder video final (dibuat otomatis)
```

---

## 🚀 Cara Menjalankan

### 1. Upload Proyek ke Vast.ai

Di komputer lokal Anda, upload folder proyek ke instance Vast.ai via **SCP**:

```bash
scp -P <PORT> -r /path/to/movie-recap/ root@<VAST_IP>:/workspace/
```

Atau buat folder baru di Vast.ai lalu upload file satu per satu.

### 2. Setup Environment (Sekali Saja)

SSH ke instance Vast.ai, lalu jalankan:

```bash
cd /workspace/movie-recap

# Beri izin eksekusi
chmod +x setup.sh run_pipeline.sh

# Jalankan setup
./setup.sh
```

**Proses setup meliputi:**
- Update system packages
- Install FFmpeg, build tools, dan utilities
- Install Python 3.10+ dependencies
- Install PyTorch dengan CUDA 12.1
- Install semua dependensi dari `requirements.txt`
- **Pre-download semua model weight** (Demucs, Faster-Whisper, Qwen3-VL, OmniVoice) ke cache
- Verifikasi CUDA dan GPU

> ⏱ **Estimasi waktu setup:** 15–30 menit (tergantung kecepatan internet dan CPU).

### 3. Jalankan Pipeline

Setelah setup selesai, jalankan pipeline dengan satu perintah:

```bash
# Format dasar
./run_pipeline.sh <URL_YOUTUBE>

# Contoh
./run_pipeline.sh "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Pipeline akan menjalankan **6 modul secara berurutan** dengan log berwarna di terminal. Jika ada modul yang gagal, pipeline akan berhenti dan menampilkan pesan error.

#### Opsi Tambahan

Pipeline meneruskan argumen tambahan ke modul transkripsi. Contoh mengganti bahasa:

```bash
# Untuk video berbahasa Inggris
./run_pipeline.sh "https://youtu.be/xxxxxx" --language en

# Untuk video berbahasa Indonesia (default)
./run_pipeline.sh "https://youtu.be/xxxxxx" --language id
```

### 4. Pipeline Per-Modul (Manual)

Jika ingin menjalankan modul satu per satu secara manual (misalnya untuk debugging):

```bash
# Masuk ke direktori proyek
cd /workspace/movie-recap

# 1. Download video
python3 1_download.py "https://www.youtube.com/watch?v=xxxxxx"

# 2. Pisahkan vokal
python3 2_audio_cleaner.py

# 3. Transkripsi
python3 3_transcribe.py

# 4. Generate skrip narasi (QLoRA 4-bit)
python3 4_script_writer.py

# 5. Text-to-Speech
python3 5_tts.py

# 6. Edit video final
python3 6_video_editor.py
```

Setiap modul memiliki opsi `--help` untuk melihat argumen yang tersedia:

```bash
python3 1_download.py --help
python3 3_transcribe.py --help
# ... dst
```

---

## 📖 Deskripsi Modul

### Modul 1: Download (`1_download.py`)
- **Fungsi**: Mengunduh video dan audio dari YouTube
- **Tool**: `yt-dlp`
- **Output**:
  - `downloads/video_original.mp4` — video resolusi terbaik
  - `downloads/audio_original.wav` — audio WAV

### Modul 2: Audio Cleaner (`2_audio_cleaner.py`)
- **Fungsi**: Memisahkan vokal dari BGM/instrumen
- **Tool**: **Demucs v4 (HTDemucs)** — model SOTA untuk source separation
- **Output**:
  - `downloads/vocals.wav` — vokal bersih (untuk transkripsi)
  - `downloads/bgm.wav` — background music (untuk mixing final)

### Modul 3: Transcribe (`3_transcribe.py`)
- **Fungsi**: Mentranskripsi audio vokal menjadi teks dengan timestamp
- **Tool**: **Faster-Whisper Large-v3** (`Systran/faster-whisper-large-v3`)
- **Konfigurasi**: `float16`, `vad_filter=True`, `beam_size=5`
- **Output**: `downloads/transcript.json`
  ```json
  [
    {
      "id": 0,
      "start": 0.000,
      "end": 3.520,
      "start_str": "00:00:00.000",
      "end_str": "00:00:03.520",
      "text": "Halo dan selamat datang di channel saya..."
    },
    ...
  ]
  ```

### Modul 4: Script Writer (`4_script_writer.py`)
- **Fungsi**: Menulis skrip narasi ala YouTuber recap film
- **Tool**: **Qwen3-VL-8B-Instruct** (kuantisasi 4-bit NF4 via BitsAndBytes)
- **Teknik**:
  - **Chunking**: Transkrip dibagi per 15 menit (900 detik) agar muat di konteks model
  - **4-bit Quantization**: Model dimuat dengan NF4 + double quantization → VRAM ~6.5 GB
  - **Prompt Engineering**: Prompt dirancang khusus untuk menghasilkan narasi santai, seru, dan engaging khas YouTuber Indonesia
- **Output**: `downloads/narration_script.txt`

### Modul 5: TTS (`5_tts.py`)
- **Fungsi**: Mengubah teks skrip menjadi audio narasi
- **Tool**: **OmniVoice** (`k2-fsa/OmniVoice`)
- **Output**: `downloads/narration.wav`

### Modul 6: Video Editor (`6_video_editor.py`)
- **Fungsi**: Menggabungkan semua elemen menjadi video final
- **Tool**: **FFmpeg**
- **Proses**:
  1. Audio video asli dikecilkan volumenya menjadi **15%** (background)
  2. Audio BGM dikecilkan menjadi **10%** (jika ada)
  3. Audio narasi TTS **full volume** (foreground/tuan rumah)
  4. Semua audio di-mix dengan filter `amix`
  5. Video asli dan audio hasil mix digabung
- **Output**: `output/final_video.mp4`

---

## 🔄 Alur Pipeline

```
YouTube URL
    │
    ▼
┌─────────────────┐
│ 1_download.py   │  yt-dlp → video.mp4 + audio.wav
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 2_audio_cleaner │  Demucs → vocals.wav + bgm.wav
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 3_transcribe.py │  Faster-Whisper → transcript.json
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 4_script_writer │  Qwen3-VL → narration_script.txt
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 5_tts.py        │  OmniVoice → narration.wav
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 6_video_editor  │  FFmpeg → final_video.mp4
└─────────────────┘
    │
    ▼
✅ Selesai!
```

---

## 🧠 Manajemen VRAM

Pipeline ini dirancang untuk berjalan di **GPU 12GB VRAM**. Hal-hal yang dilakukan untuk memastikan VRAM cukup:

| Modul | Perkiraan VRAM | Strategi |
|-------|---------------|----------|
| Demucs | ~3 GB | Model di-unload setelah selesai |
| Faster-Whisper | ~4 GB | Model di-unload + `float16` |
| Qwen3-VL | ~6.5 GB | 4-bit NF4 quantization, di-unload setelah selesai |
| OmniVoice | ~2 GB | Model di-unload setelah selesai |

**Setiap modul berat**, pipeline akan:
1. Memanggil `torch.cuda.empty_cache()`
2. Memanggil `gc.collect()`
3. Menampilkan status VRAM via `nvidia-smi`
4. Delay 2 detik

Hal ini memastikan GPU **100% kosong** sebelum modul berikutnya dimulai.

---

## 🔧 Troubleshooting

### ❌ "CUDA out of memory"

**Penyebab**: VRAM tidak cukup untuk modul tertentu.

**Solusi**:
1. Pastikan tidak ada proses GPU lain berjalan (`nvidia-smi`)
2. Untuk Qwen3-VL, turunkan `max_new_tokens` di `4_script_writer.py` (baris `max_new_tokens=2048`)
3. Untuk Demucs, tambahkan argumen `--segment` yang lebih kecil (default: `--segment 9.0`)
4. Turunkan `beam_size` di `3_transcribe.py` (dari 5 ke 3)

### ❌ "ModuleNotFoundError: No module named '...'"

**Penyebab**: Dependensi belum terinstall.

**Solusi**: Jalankan ulang `./setup.sh` atau install manual:
```bash
pip install -r requirements.txt
```

### ❌ "yt-dlp: command not found"

**Penyebab**: yt-dlp belum terinstall.

**Solusi**:
```bash
pip install yt-dlp
```

### ❌ "FFmpeg not found"

**Penyebab**: FFmpeg belum terinstall.

**Solusi**:
```bash
sudo apt-get install ffmpeg
```

### ❌ Demucs gagal memisahkan audio

**Solusi**: Jalankan dengan segment size lebih kecil:
```bash
python3 -m demucs --two-stems vocals --segment 5.0 -o separated downloads/audio_original.wav
```

### ❌ Pipeline berhenti di tengah jalan

Periksa log untuk melihat modul mana yang gagal. Perbaiki error, lalu jalankan ulang pipeline dari modul yang gagal (lewati modul yang sudah berhasil dengan menjalankan masing-masing skrip secara manual).

---

## 📚 Referensi

| Komponen | Referensi |
|----------|-----------|
| **Demucs v4** | https://github.com/facebookresearch/demucs |
| **Faster-Whisper Large-v3** | https://huggingface.co/Systran/faster-whisper-large-v3 |
| **Qwen3-VL 8B Instruct** | https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct |
| **OmniVoice TTS** | https://huggingface.co/k2-fsa/OmniVoice |
| **yt-dlp** | https://github.com/yt-dlp/yt-dlp |
| **FFmpeg** | https://ffmpeg.org/ |
| **Vast.ai** | https://vast.ai/ |

---

## 📄 Lisensi

Proyek ini dibuat untuk keperluan belajar dan pengembangan konten. Harap perhatikan hak cipta dan kebijakan penggunaan YouTube saat menggunakan alat ini.

---

**Dibuat dengan ❤️ untuk para content creator**
