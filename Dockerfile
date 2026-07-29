FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime

# Set working directory
WORKDIR /app

# Install dependencies sistem
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy seluruh isi project ke container
COPY . /app

# Jalankan setup script jika ada file setup.sh
RUN if [ -f ./setup.sh ]; then chmod +x ./setup.sh && ./setup.sh; fi

# Install requirements jika ada file requirements.txt
RUN if [ -f ./requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
