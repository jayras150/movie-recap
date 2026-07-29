#!/usr/bin/env bash
# ============================================================
# setup.sh — Instalasi Awal Environment untuk Movie Recap Pipeline
# Wajib dijalankan sekali sebelum run_pipeline.sh
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log_info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# -----------------------------------------------
# 1. Update system & install basic packages
# -----------------------------------------------
log_info "Memperbarui system packages..."
apt-get update -y && apt-get upgrade -y
apt-get install -y --no-install-recommends \
    curl wget git unzip tar ffmpeg python3-pip python3-dev \
    build-essential cmake pkg-config libsndfile1-dev
log_ok "System packages terinstall."

# -----------------------------------------------
# 2. Pastikan Python 3.10+
# -----------------------------------------------
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
log_info "Python version: $PYTHON_VERSION"

# -----------------------------------------------
# 3. Install PyTorch with CUDA 12.1
# -----------------------------------------------
log_info "Menginstall PyTorch 2.5.x dengan CUDA 12.1..."
pip3 install --upgrade pip
pip3 install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
log_ok "PyTorch dengan CUDA 12.1 terinstall."

# -----------------------------------------------
# 4. Install dependensi Python dari requirements.txt
# -----------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log_info "Menginstall Python dependencies dari requirements.txt..."
pip3 install -r "${SCRIPT_DIR}/requirements.txt"
log_ok "Semua Python dependencies terinstall."

# -----------------------------------------------
# 5. Pre-download model weights ke cache
# -----------------------------------------------
log_info "Pre-download Demucs model (HTDemucs)..."
python3 -c "import demucs; demucs.pretrained.get_model('htdemucs')" 2>/dev/null || true
log_ok "Demucs model siap."

log_info "Pre-download Faster-Whisper model..."
python3 -c "from faster_whisper import WhisperModel; WhisperModel('Systran/faster-whisper-large-v3', device='cuda', compute_type='float16')" 2>/dev/null || true
log_ok "Faster-Whisper model siap."

log_info "Pre-download Qwen3-VL model (quantized 4-bit)..."
python3 -c "
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
import torch
from bitsandbytes.nn import Linear4bit

model = Qwen3VLForConditionalGeneration.from_pretrained(
    'Qwen/Qwen3-VL-8B-Instruct',
    device_map='auto',
    torch_dtype=torch.float16,
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type='nf4'
)
processor = AutoProcessor.from_pretrained('Qwen/Qwen3-VL-8B-Instruct')
print('Qwen3-VL model siap.')
" 2>/dev/null || true
log_ok "Qwen3-VL model siap."

log_info "Pre-download OmniVoice model..."
python3 -c "
from omnivoice import OmniVoice
tts = OmniVoice.from_pretrained('k2-fsa/OmniVoice')
print('OmniVoice model siap.')
" 2>/dev/null || true
log_ok "OmniVoice model siap."

# -----------------------------------------------
# 6. Verifikasi CUDA
# -----------------------------------------------
log_info "Verifikasi CUDA availability..."
python3 -c "
import torch
print(f'CUDA available : {torch.cuda.is_available()}')
print(f'GPU device     : {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')
print(f'VRAM total     : {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB' if torch.cuda.is_available() else 'N/A')
"
log_ok "Setup selesai! GPU siap digunakan."
