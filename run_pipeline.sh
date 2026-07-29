#!/usr/bin/env bash
# ============================================================
# run_pipeline.sh — Master Bash Orchestrator
# Eksekusi bertahap (sequential) seluruh pipeline movie recap.
# Setiap modul Python dijalankan, ditunggu selesai, lalu VRAM
# dibersihkan sebelum modul berikutnya.
# ============================================================
set -euo pipefail

# ── Warna Terminal ──────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Direktori ───────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# ── Fungsi Helper ──────────────────────────────────────────
log_step()   { echo -e "\n${BOLD}${BLUE}═══════════════════════════════════════════════${NC}"; echo -e "${BOLD}${BLUE}  🔷 $1${NC}"; echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════${NC}\n"; }
log_ok()     { echo -e "${GREEN}  [✓] $1${NC}"; }
log_warn()   { echo -e "${YELLOW}  [⚠] $1${NC}"; }
log_error()  { echo -e "${RED}  [✗] $1${NC}"; }
log_info()   { echo -e "${CYAN}  [i] $1${NC}"; }

# ── Cek GPU & VRAM ─────────────────────────────────────────
check_gpu() {
    echo -e "\n${MAGENTA}━━━ GPU Status ━━━${NC}"
    if command -v nvidia-smi &>/dev/null; then
        nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader 2>/dev/null || true
        echo ""
    else
        log_warn "nvidia-smi tidak ditemukan. Pastikan driver NVIDIA terinstall."
    fi
}

# ── Bersihkan VRAM ─────────────────────────────────────────
clean_vram() {
    log_info "Membersihkan VRAM — memastikan GPU 100% kosong..."
    python3 -c "
import torch
import gc
gc.collect()
torch.cuda.empty_cache()
torch.cuda.synchronize()
print(f'VRAM used: {torch.cuda.memory_allocated() / 1024**2:.1f} MB')
print(f'VRAM cached: {torch.cuda.memory_reserved() / 1024**2:.1f} MB')
" 2>/dev/null || true
    sleep 2
    echo ""
}

# ── Jalankan Modul Python ──────────────────────────────────
run_module() {
    local module_name="$1"
    local script="$2"
    local args="${3:-}"

    log_step "${module_name}"

    if [ ! -f "${script}" ]; then
        log_error "File tidak ditemukan: ${script}"
        exit 1
    fi

    log_info "Menjalankan: python3 ${script} ${args}"
    echo ""

    set +e
    python3 ${script} ${args}
    local exit_code=$?
    set -e

    echo ""
    if [ ${exit_code} -eq 0 ]; then
        log_ok "${module_name} selesai dengan sukses! (exit code: ${exit_code})"
    else
        log_error "${module_name} gagal! (exit code: ${exit_code})"
        log_warn "Pipeline dihentikan karena error di ${module_name}."
        exit ${exit_code}
    fi

    # Bersihkan VRAM setelah setiap modul
    clean_vram
}

# ── Validasi Environment ────────────────────────────────────
validate_env() {
    log_step "Validasi Environment"

    # Cek Python
    if ! command -v python3 &>/dev/null; then
        log_error "python3 tidak ditemukan!"
        exit 1
    fi
    log_ok "Python: $(python3 --version)"

    # Cek CUDA
    python3 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.version.cuda}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"NONE\"}')" 2>/dev/null
    if [ $? -ne 0 ]; then
        log_error "PyTorch/CUDA tidak berfungsi. Jalankan setup.sh dulu."
        exit 1
    fi
    log_ok "CUDA tersedia & PyTorch siap."

    # Cek FFmpeg
    if ! command -v ffmpeg &>/dev/null; then
        log_error "FFmpeg tidak ditemukan! Jalankan: apt-get install ffmpeg"
        exit 1
    fi
    log_ok "FFmpeg: $(ffmpeg -version 2>&1 | head -1)"

    # Cek direktori
    mkdir -p downloads output

    check_gpu
    clean_vram
    log_ok "Environment siap!"
}

# ── Hapus Temporary Model Cache Antar Modul ────────────────
clean_temp_models() {
    log_info "Membersihkan cache model sisa dari modul sebelumnya..."
    clean_vram
    # Hapus folder separated Demucs jika ada
    if [ -d "separated" ]; then
        rm -rf separated
        log_info "Folder 'separated/' dihapus."
    fi
}

# ── Main Pipeline ──────────────────────────────────────────
main() {
    echo -e "${BOLD}${MAGENTA}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║      🎬 MOVIE RECAP PIPELINE — ORCHESTRATOR      ║"
    echo "║        Auto Video Recap Generator                ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "Waktu mulai: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Working dir: ${SCRIPT_DIR}"
    echo ""

    # ── Validasi ────────────────────────────────────────────
    validate_env

    # ── Argumen: URL YouTube ───────────────────────────────
    if [ $# -lt 1 ]; then
        echo -e "${YELLOW}Penggunaan:${NC}"
        echo "  ./run_pipeline.sh <YouTube-URL> [--language <lang>]"
        echo ""
        echo "Contoh:"
        echo "  ./run_pipeline.sh https://youtu.be/xxxxxxx"
        echo "  ./run_pipeline.sh https://youtu.be/xxxxxxx --language en"
        exit 1
    fi

    YT_URL="$1"
    shift
    EXTRA_ARGS="${*:-}"

    echo -e "${CYAN}YouTube URL  : ${YT_URL}${NC}"
    echo -e "${CYAN}Extra args   : ${EXTRA_ARGS}${NC}"
    echo ""

    # ── Pipeline Sequential ─────────────────────────────────
    # Module 1: Download
    run_module "1. Download Video & Audio" \
        "1_download.py" \
        "${YT_URL}"

    # Module 2: Audio Cleaner (Vocal Separation)
    run_module "2. Audio Cleaner (Demucs)" \
        "2_audio_cleaner.py"

    # Module 3: Transcription
    run_module "3. Transkripsi (Faster-Whisper)" \
        "3_transcribe.py"

    # Module 4: Script Writer
    run_module "4. Script Writer (Qwen3-VL)" \
        "4_script_writer.py"

    # Bersihkan model besar sebelum TTS
    clean_temp_models

    # Module 5: TTS
    run_module "5. Text-to-Speech (OmniVoice)" \
        "5_tts.py"

    # Module 6: Video Editor
    run_module "6. Video Editor (FFmpeg)" \
        "6_video_editor.py"

    # ── Selesai ─────────────────────────────────────────────
    echo -e "\n${BOLD}${GREEN}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║      ✅ PIPELINE COMPLETE! 🎉                    ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # Tampilkan output
    echo -e "${CYAN}Output files:${NC}"
    ls -lh downloads/ 2>/dev/null || true
    echo ""
    ls -lh output/ 2>/dev/null || true
    echo ""

    FINAL_VIDEO="output/final_video.mp4"
    if [ -f "${FINAL_VIDEO}" ]; then
        DURATION=$(ffprobe -v quiet -print_format json -show_format "${FINAL_VIDEO}" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{float(d['format']['duration']):.1f} dtk\")" 2>/dev/null || echo "?")
        SIZE=$(du -h "${FINAL_VIDEO}" 2>/dev/null | cut -f1)
        log_ok "Video final siap: ${FINAL_VIDEO} (${SIZE}, ${DURATION})"
    fi

    echo ""
    echo "Waktu selesai: $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${BOLD}${GREEN}Done!${NC}"
}

# ── Entry Point ─────────────────────────────────────────────
main "$@"
