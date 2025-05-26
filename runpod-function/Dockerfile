# Use CUDA 12.1.1 base image
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.10, pip, and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-dev \
    python3.10-venv \
    build-essential \
    git \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    portaudio19-dev \
    python3-setuptools \
    python3.10-distutils \
    ninja-build \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Make python3.10 the default python/pip
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Set working directory
WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install PyTorch with CUDA 12.1 support
RUN pip install --no-cache-dir \
    torch==2.5.1+cu121 \
    torchaudio==2.5.1+cu121 \
    torchvision==0.20.1 \
    --index-url https://download.pytorch.org/whl/cu121

# Install DeepSpeed
ENV DS_BUILD_TRANSFORMER=1
ENV DS_BUILD_CPU_ADAM=0
ENV DS_BUILD_FUSED_ADAM=0
ENV DS_BUILD_UTILS=0
ENV DS_BUILD_OPS=0

RUN echo "Building DeepSpeed with flags: DS_BUILD_TRANSFORMER=${DS_BUILD_TRANSFORMER}, DS_BUILD_CPU_ADAM=${DS_BUILD_CPU_ADAM}, DS_BUILD_FUSED_ADAM=${DS_BUILD_FUSED_ADAM}, DS_BUILD_UTILS=${DS_BUILD_UTILS}, DS_BUILD_OPS=${DS_BUILD_OPS}" && \
    pip install --no-cache-dir deepspeed \
    || (echo "DeepSpeed install failed. Check build logs above." && exit 1)

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt \
    || (echo "pip install -r requirements.txt FAILED." && exit 1)

# Pin ctranslate2 to a compatible version
RUN pip install --no-cache-dir "ctranslate2<4.5.0"

# Copy all application files
COPY . .

# <<<--- Model Pre-downloads for faster cold starts --->>>
# <<<--- Silero VAD Pre-download --->>>
RUN echo "Preloading Silero VAD model..." && \
    python3 <<EOF
import torch
import os
try:
    # Downloads will happen as root here, ownership fixed later
    cache_dir = os.path.expanduser("~/.cache/torch")
    os.environ['TORCH_HOME'] = cache_dir
    print(f"Using TORCH_HOME: {cache_dir}")
    torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        force_reload=False,
        onnx=False,
        trust_repo=True
    )
    print("Silero VAD download successful.")
except Exception as e:
    print(f"Error downloading Silero VAD: {e}")
    exit(1)
EOF

# <<<--- faster-whisper Pre-download --->>>
ARG WHISPER_MODEL=base.en
ENV WHISPER_MODEL=${WHISPER_MODEL}
RUN echo "Preloading faster_whisper model: ${WHISPER_MODEL}" && \
    python3 -c "import os; print(f\"Downloading STT model: {os.getenv('WHISPER_MODEL')}\"); import faster_whisper; model = faster_whisper.WhisperModel(os.getenv('WHISPER_MODEL'), device='cpu'); print('Model download successful.')" \
    || (echo "Faster Whisper download failed" && exit 1)

# <<<--- SentenceFinishedClassification Pre-download --->>>
RUN echo "Preloading SentenceFinishedClassification model..." && \
    python3 -c "from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification; \
                print('Downloading tokenizer...'); \
                tokenizer = DistilBertTokenizerFast.from_pretrained('KoljaB/SentenceFinishedClassification'); \
                print('Downloading classification model...'); \
                model = DistilBertForSequenceClassification.from_pretrained('KoljaB/SentenceFinishedClassification'); \
                print('Model downloads successful.')" \
    || (echo "Sentence Classifier download failed" && exit 1)

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="${CUDA_HOME}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}"
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV HF_HOME=/app/.cache/huggingface
ENV TORCH_HOME=/app/.cache/torch
ENV DS_BUILD_OPS=1
ENV DS_BUILD_CPU_ADAM=0
ENV DS_BUILD_FUSED_ADAM=0
ENV DS_BUILD_UTILS=0
ENV DS_BUILD_TRANSFORMER=1

# Create cache directories
RUN mkdir -p /app/.cache/huggingface /app/.cache/torch

# Expose port (though not strictly necessary for serverless)
EXPOSE 8000

# Command to run the handler
CMD ["python", "handler.py"] 