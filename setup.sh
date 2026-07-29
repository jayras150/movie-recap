#!/usr/bin/env bash
# ============================================================
# setup.sh — Instalasi Environment untuk Movie Recap Pipeline
# Versi ringan untuk Docker: tanpa apt upgrade, tanpa torch
# ulang, tanpa download model (model di-download saat runtime).
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log_info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# -----------------------------------------------
# 1. Cek & install system packages jika belum ada
# -----------------------------------------------
log_info "Memeriksa system packages..."
MISSING=""
for pkg in ffmpeg git curl python3-pip; do
    if ! command -v "$pkg" &>/dev/null; then
        MISSING="$MISSING $pkg"
    fi
done

if [ -n "$MISSING" ]; then
    log_info "Menginstall system packages yang kurang:$MISSING"
    apt-get update -y
    apt-get install -y --no-install-recommends $MISSING
    rm -rf /var/lib/apt/lists/*
    log_ok "System packages terinstall."
else
    log_ok "Semua system packages sudah tersedia."
fi

# -----------------------------------------------
# 2. Install Python dependencies (tanpa torch)
# -----------------------------------------------
log_info "Menginstall Python dependencies..."
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir -r "${SCRIPT_DIR}/requirements.txt"
log_ok "Semua Python dependencies terinstall."

# -----------------------------------------------
# 3. Verifikasi CUDA (jika GPU tersedia)
# -----------------------------------------------
log_info "Verifikasi CUDA availability..."
python3 -c "
import torch
print(f'PyTorch   : {torch.__version__}')
print(f'CUDA      : {torch.version.cuda}')
print(f'CUDA avail: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU device: {torch.cuda.get_device_name(0)}')
    print(f'VRAM total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')
"
log_ok "Setup selesai!"
