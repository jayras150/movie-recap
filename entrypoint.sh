#!/usr/bin/env bash
# ============================================================
# entrypoint.sh — Container entrypoint
# 1. Cek & download model AI jika belum ada
# 2. Jalankan pipeline atau perintah yang diberikan
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log_step()  { echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════${NC}\n"; }
log_ok()    { echo -e "${GREEN}  [✓] $1${NC}"; }
log_warn()  { echo -e "${YELLOW}  [⚠] $1${NC}"; }
log_info()  { echo -e "${CYAN}  [i] $1${NC}"; }
log_error() { echo -e "${RED}  [✗] $1${NC}"; }

# ── Markers ──────────────────────────────────────────────────
MODEL_DIR="/models"
DOWNLOAD_MARKER="${MODEL_DIR}/.models_downloaded"
MODEL_LOCK="${MODEL_DIR}/.download.lock"

# ── Cache env vars (harus match dengan Dockerfile) ───────────
export HF_HOME="${MODEL_DIR}/huggingface"
export HUGGINGFACE_HUB_CACHE="${MODEL_DIR}/huggingface/hub"
export TRANSFORMERS_CACHE="${MODEL_DIR}/huggingface"
export TORCH_HOME="${MODEL_DIR}/torch"
export XDG_CACHE_HOME="${MODEL_DIR}/cache"
export DEMUCS_CACHE="${MODEL_DIR}/demucs"
export WHISPER_CACHE="${MODEL_DIR}/whisper"

# Pastikan direktori models ada
mkdir -p "${HF_HOME}/hub" "${TORCH_HOME}" "${XDG_CACHE_HOME}" "${DEMUCS_CACHE}" "${WHISPER_CACHE}"

# Symlink agar Demucs & torch hub能找到 cache
ln -sf "${TORCH_HOME}" /root/.cache/torch 2>/dev/null || true

# ── Fungsi download model ────────────────────────────────────
download_models() {
    log_step "📥 Mendownload Model AI (pertama kali)"

    # Lock file agar tidak tabrakan
    if [ -f "${MODEL_LOCK}" ]; then
        log_warn "Proses download sedang berjalan. Menunggu..."
        sleep 5
        if [ -f "${DOWNLOAD_MARKER}" ]; then
            log_ok "Model sudah di-download oleh proses lain."
            return 0
        fi
    fi

    touch "${MODEL_LOCK}"
    trap 'rm -f "${MODEL_LOCK}"' EXIT

    # ── 1. Demucs (HTDemucs) ────────────────────────────────
    log_info "[1/4] Mendownload Demucs model (HTDemucs)..."
    python3 -c "
import torch
import demucs
from demucs import pretrained
print('Memuat Demucs HTDemucs...')
model = pretrained.get_model('htdemucs')
print('Demucs siap.')
" 2>&1 | tail -5
    log_ok "Demucs model siap."

    # ── 2. Faster-Whisper Large-v3 ──────────────────────────
    log_info "[2/4] Mendownload Faster-Whisper model..."
    python3 -c "
from faster_whisper import WhisperModel
print('Memuat Faster-Whisper Large-v3...')
model = WhisperModel('Systran/faster-whisper-large-v3', device='cpu', compute_type='float16')
print('Faster-Whisper siap.')
" 2>&1 | tail -5
    log_ok "Faster-Whisper model siap."

    # ── 3. Qwen3-VL-8B-Instruct (4-bit) ────────────────────
    log_info "[3/4] Mendownload Qwen3-VL model (4-bit NF4)..."
    python3 -c "
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
import torch

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type='nf4',
)

model = Qwen3VLForConditionalGeneration.from_pretrained(
    'Qwen/Qwen3-VL-8B-Instruct',
    quantization_config=bnb_config,
    device_map='auto',
    torch_dtype=torch.float16,
    trust_remote_code=True,
)
processor = AutoProcessor.from_pretrained(
    'Qwen/Qwen3-VL-8B-Instruct',
    trust_remote_code=True,
)
print('Qwen3-VL siap.')
" 2>&1 | tail -5
    log_ok "Qwen3-VL model siap."

    # ── 4. OmniVoice ────────────────────────────────────────
    log_info "[4/4] Mendownload OmniVoice model..."
    python3 -c "
from omnivoice import OmniVoice
print('Memuat OmniVoice...')
tts = OmniVoice.from_pretrained('k2-fsa/OmniVoice', device='cpu')
print('OmniVoice siap.')
" 2>&1 | tail -5
    log_ok "OmniVoice model siap."

    # ── Buat marker ─────────────────────────────────────────
    date > "${DOWNLOAD_MARKER}"
    rm -f "${MODEL_LOCK}"
    trap - EXIT
    log_ok "✅ Semua model berhasil di-download!"
}

# ── Main ─────────────────────────────────────────────────────
main() {
    echo -e "${BOLD}${CYAN}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║   🎬 Movie Recap Pipeline — Docker Container     ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # ── Cek apakah model sudah ada ──────────────────────────
    if [ ! -f "${DOWNLOAD_MARKER}" ]; then
        download_models
    else
        log_ok "Model sudah pernah di-download (${DOWNLOAD_MARKER})."
        log_info "Hapus file marker untuk mendownload ulang: rm -f ${DOWNLOAD_MARKER}"
    fi

    # ── Tampilkan versi & GPU ───────────────────────────────
    echo ""
    log_info "Python: $(python3 --version 2>&1)"
    python3 -c "
import torch
print(f'PyTorch: {torch.__version__}, CUDA: {torch.version.cuda}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')
" 2>/dev/null || true

    # ── Jika tidak ada argumen, tampilkan help ──────────────
    if [ $# -eq 0 ]; then
        echo ""
        echo "Penggunaan:"
        echo "  docker run ... <URL_YOUTUBE>              # Jalankan pipeline"
        echo "  docker run ... bash                        # Masuk shell"
        echo "  docker run ... python3 1_download.py ...   # Jalankan modul spesifik"
        echo ""
        echo "Contoh:"
        echo "  docker run -v /path/to/models:/models -v /path/to/output:/app/output \\"
        echo "    movie-recap \"https://youtu.be/xxxx\""
        echo ""
        exec /app/run_pipeline.sh --help
    fi

    # ── Jalankan pipeline dengan argumen ────────────────────
    exec /app/run_pipeline.sh "$@"
}

main "$@"
