# 🚀 Panduan Menjalankan Movie Recap Pipeline di Vast.ai

Panduan ini khusus untuk **Vast.ai Instance** dengan spesifikasi:
- **OS**: Ubuntu Linux (Vast.ai template)
- **GPU**: Nvidia RTX 3060 12GB VRAM (atau GPU ≥ 10GB VRAM)
- **CUDA**: 12.1
- **Storage**: Minimal 30GB

---

## 📋 Daftar Isi

- [1. Buat Instance di Vast.ai](#1-buat-instance-di-vastai)
- [2. SSH ke Instance](#2-ssh-ke-instance)
- [3. Clone Repository](#3-clone-repository)
- [4. Setup Environment](#4-setup-environment)
- [5. Jalankan Pipeline](#5-jalankan-pipeline)
- [6. Opsi Lanjutan](#6-opsi-lanjutan)
- [7. Menggunakan Docker (Alternatif)](#7-menggunakan-docker-alternatif)
- [8. Troubleshooting Vast.ai](#8-troubleshooting-vastai)

---

## 1. Buat Instance di Vast.ai

### Langkah-langkah:

1. Buka [Vast.ai](https://vast.ai) dan login.
2. Klik **Rent a GPU** di sidebar kiri.
3. Filter instance:
   - **GPU**: RTX 3060 (atau GPU lain ≥ 10GB VRAM)
   - **CUDA**: 12.1 atau lebih baru
   - **Disk Space**: ≥ 30GB
   - **Price**: Pilih yang termurah dengan koneksi internet bagus
4. Klik **Rent** pada instance yang dipilih.
5. Pilih template **PyTorch** (atau **CUDA 12.1 + PyTorch**).
6. Set **Disk Space** minimal **30GB** (model AI memakan ~15GB).
7. Klik **Rent** dan tunggu hingga status **Running**.

> **Tips**: Cari instance dengan `cuda >= 12.1` dan `disk >= 30`. Jangan pake template `docker` — pake template `pytorch` biar PyTorch + CUDA sudah terinstall.

---

## 2. SSH ke Instance

Setelah instance running, SSH menggunakan command dari Vast.ai:

```bash
# Contoh — ganti PORT dan IP sesuai instance kamu
ssh -p 12345 root@12.34.56.78
```

Atau copy paste command dari halaman instance Vast.ai (klik ikon **SSH**).

---

## 3. Clone Repository

```bash
# Clone repo
git clone https://github.com/jayras150/movie-recap.git
cd movie-recap
```

Cek isi folder:

```bash
ls -la
```

Pastikan semua file ada:

```
1_download.py
2_audio_cleaner.py
3_transcribe.py
4_script_writer.py
5_tts.py
6_video_editor.py
Dockerfile
entrypoint.sh
requirements.txt
run_pipeline.sh
setup.sh
```

---

## 4. Setup Environment

> **Catatan**: Di Vast.ai template PyTorch, CUDA dan PyTorch **sudah terinstall**. Jadi kita hanya perlu install dependencies tambahan.

```bash
cd ~/movie-recap

# Beri izin eksekusi
chmod +x setup.sh run_pipeline.sh entrypoint.sh

# Jalankan setup (ringan — hanya install dependencies & verifikasi CUDA)

apt-get remove -y libnode-dev && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs && python3 -m pip install -U yt-dlp yt-dlp-ejs


./setup.sh
```

### Yang dilakukan setup.sh:

| Step | Keterangan |
|------|-----------|
| Cek system packages | Install FFmpeg, git, curl jika belum ada |
| Install Python dependencies | `pip install -r requirements.txt` |
| Verifikasi CUDA | Cek PyTorch, CUDA version, GPU name |

> ⏱ **Estimasi**: 3–5 menit.
>
> Model AI **tidak** di-download saat setup. Model akan di-download otomatis saat pertama kali pipeline dijalankan.

### Verifikasi CUDA (manual):

```bash
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

Output yang diharapkan:

```
CUDA: True, GPU: NVIDIA GeForce RTX 3060
```

---

## 5. Jalankan Pipeline

### Cara 1: Otomatis (via entrypoint)

Pipeline akan **download model otomatis** lalu memproses video:

```bash
./entrypoint.sh "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
```

Atau:

```bash
./entrypoint.sh "https://youtu.be/YOUR_VIDEO_ID"
```

**Proses download model (hanya sekali):**

Saat pertama kali dijalankan, entrypoint akan mendownload semua model AI:

```
[1/4] Demucs (HTDemucs)        ~ 500 MB
[2/4] Faster-Whisper Large-v3  ~ 3 GB
[3/4] Qwen3-VL-8B-Instruct     ~ 4.5 GB
[4/4] OmniVoice                 ~ 1.5 GB
```

> ⏱ **Estimasi download**: 10–20 menit (tergantung koneksi internet).
>
> Model disimpan di folder `~/.cache/` (HF: `~/.cache/huggingface/`, Torch: `~/.cache/torch/`).

### Cara 2: Manual (step-by-step)

Jika ingin kontrol lebih:

```bash
# 1. Download video dari YouTube
python3 1_download.py "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"

# 2. Pisahkan vokal dari BGM (Demucs)
python3 2_audio_cleaner.py

# 3. Transkripsi vokal ke teks (Faster-Whisper)
python3 3_transcribe.py

# 4. Generate skrip narasi (Qwen3-VL) — download model otomatis
python3 4_script_writer.py

# 5. Text-to-Speech (OmniVoice) — download model otomatis
python3 5_tts.py

# 6. Edit video final (FFmpeg)
python3 6_video_editor.py
```

### Cara 3: Pipeline otomatis (via run_pipeline.sh)

```bash
./run_pipeline.sh "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
```

Perbedaan dengan entrypoint: `run_pipeline.sh` **tidak** otomatis download model. Jalankan dulu `entrypoint.sh` atau download manual jika pakai `run_pipeline.sh`.

---

## 6. Opsi Lanjutan

### Ganti Bahasa Transkripsi

Default: `id` (Bahasa Indonesia). Untuk video bahasa Inggris:

```bash
./entrypoint.sh "https://youtu.be/xxxx" --language en
```

### Pipeline Per-Modul dengan Argumen Kustom

```bash
# Transkripsi dengan bahasa Spanyol
python3 3_transcribe.py --language es

# TTS dengan voice tertentu (jika OmniVoice mendukung)
python3 5_tts.py --voice female
```

### Download Model Manual (Tanpa Pipeline)

Jika hanya ingin mendownload model dulu tanpa memproses video:

```bash
./entrypoint.sh --help
```

Ini akan mendownload semua model lalu menampilkan help.

### Cek Status GPU Saat Pipeline Berjalan

Buka terminal kedua via SSH, lalu:

```bash
watch -n 2 nvidia-smi
```

Atau:

```bash
nvidia-smi -l 2
```

---

## 7. Menggunakan Docker (Alternatif)

Jika instance Vast.ai mendukung Docker, kamu bisa pakai image dari Docker Hub.

### Build Sendiri

```bash
# Di instance Vast.ai
docker build -t movie-recap:latest .
```

### Pull dari Docker Hub (jika sudah di-push)

```bash
docker pull jayras150/movie-recap:latest
```

### Jalankan Container

```bash
# Model akan otomatis di-download saat container pertama dijalankan
docker run --gpus all -v movie-recap-models:/models \
  -v $(pwd)/output:/app/output \
  movie-recap:latest "https://www.youtube.com/watch?v=xxxx"
```

Model AI disimpan di volume `movie-recap-models` — container restart tidak perlu download ulang.

---

## 8. Troubleshooting Vast.ai

### ❌ "CUDA out of memory"

**Penyebab**: VRAM tidak cukup saat menjalankan Qwen3-VL (butuh ~6.5 GB).

**Solusi**:
1. Tutup proses GPU lain: `killall python3` atau `nvidia-smi` → cek PID → `kill -9 <PID>`
2. Pipeline otomatis sudah membersihkan VRAM antar modul, jadi ini jarang terjadi.
3. Jika tetap terjadi, restart instance dari Vast.ai dashboard.

### ❌ "No space left on device"

**Penyebab**: Disk penuh karena model AI + video.

**Solusi**:
1. Periksa disk: `df -h`
2. Hapus file sementara: `rm -rf ~/.cache/pip ~/movie-recap/downloads/*.wav ~/movie-recap/separated/`
3. Di Vast.ai, kamu bisa **extend disk** dari halaman instance (Settings → Extend Disk).

### ❌ "pip install" gagal / timeout

**Penyebab**: Koneksi internet lambat.

**Solusi**:
```bash
# Gunakan mirror PyPI Indonesia/Asia
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### ❌ yt-dlp: "HTTP Error 403"

**Penyebab**: YouTube memblokir request.

**Solusi**:
```bash
# Update yt-dlp ke versi terbaru
pip install -U yt-dlp

# Atau gunakan cookies
yt-dlp --cookies-from-browser chrome "URL"
```

### ❌ Demucs gagal di tengah jalan

**Solusi**: Jalankan dengan segment size lebih kecil untuk menghemat VRAM:
```bash
python3 -m demucs --two-stems vocals --segment 5.0 -o separated downloads/audio_original.wav
```

### ❌ Koneksi SSH terputus saat pipeline berjalan

Gunakan `tmux` atau `screen` agar proses tetap jalan walau SSH disconnect:

```bash
# Install tmux
apt-get install tmux -y

# Buat session
tmux new -s movie-recap

# Jalankan pipeline
./entrypoint.sh "https://youtu.be/xxxx"

# Detach: Ctrl+B, lalu D
# Re-attach: tmux attach -t movie-recap
```

### ❌ Ingin Reset Total

```bash
# Hapus semua cache model dan download ulang
rm -rf ~/.cache/huggingface ~/.cache/torch ~/.cache/demucs
rm -rf ~/movie-recap/downloads ~/movie-recap/output ~/movie-recap/separated
```

---

## 📁 Struktur Folder Output

Setelah pipeline selesai, file-file berikut tersedia:

```
~/movie-recap/
├── downloads/
│   ├── video_original.mp4      # Video asli dari YouTube
│   ├── audio_original.wav      # Audio asli
│   ├── vocals.wav              # Vokal bersih (setelah Demucs)
│   ├── bgm.wav                 # Background music
│   ├── transcript.json         # Hasil transkripsi (teks + timestamp)
│   └── narration_script.txt    # Skrip narasi dari Qwen3-VL
├── separated/                  # Folder output Demucs
└── output/
    └── final_video.mp4         # 🎬 Video final siap upload!
```

---

## 💎 Tips

1. **Gunakan `tmux`** — biar pipeline tetap jalan walau SSH disconnect.
2. **Download model dulu** — jalankan `./entrypoint.sh --help` sebelum pipeline beneran, biar download model selesai duluan.
3. **Cek `nvidia-smi`** — pastikan VRAM bersih antar modul.
4. **Video pendek dulu** — coba dengan video 5-10 menit dulu untuk testing, baru naik ke video panjang.
5. **Docker alternatif** — kalau Vast.ai support Docker, image lebih portabel antar instance.

---

**Selamat mencoba! 🎬**
