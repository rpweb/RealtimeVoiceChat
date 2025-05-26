# Stage 1: Builder Stage - Install dependencies including build tools and CUDA toolkit components
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04 AS builder

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.10, pip, build essentials, git, and other system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-dev \
    python3.10-venv \
    build-essential \
    git \
    libsndfile1 \
    libportaudio2 \
    ffmpeg \
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

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install remaining Python dependencies from requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt \
    || (echo "pip install -r requirements.txt FAILED." && exit 1)

# Pin ctranslate2 to a compatible version
RUN pip install --no-cache-dir "ctranslate2<4.5.0"

# Copy the application code
COPY . .

# --- Stage 2: Runtime Stage ---
# Base image still needs CUDA toolkit for PyTorch/DeepSpeed/etc in the app
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies for the APP + gosu
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-dev \
    libsndfile1 \
    ffmpeg \
    libportaudio2 \
    python3-setuptools \
    python3.10-distutils \
    ninja-build \
    build-essential \
    g++ \
    curl \
    gosu \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Make python3.10 the default python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Set working directory for the application
WORKDIR /app

# Copy installed Python packages from the builder stage
RUN mkdir -p /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages

# Copy the application code from the builder stage
COPY --from=builder /app .

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
    python3 <<EOF
import os
import faster_whisper
try:
    model_name = os.getenv('WHISPER_MODEL')
    print(f"Downloading STT model: {model_name}")
    model = faster_whisper.WhisperModel(model_name, device='cpu')
    print('Model download successful.')
except Exception as e:
    print(f'Error downloading faster_whisper model: {e}')
    exit(1)
EOF

# <<<--- SentenceFinishedClassification Pre-download --->>>
RUN echo "Preloading SentenceFinishedClassification model..." && \
    python3 <<EOF
from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification
try:
    print('Downloading tokenizer...')
    tokenizer = DistilBertTokenizerFast.from_pretrained('KoljaB/SentenceFinishedClassification')
    print('Downloading classification model...')
    model = DistilBertForSequenceClassification.from_pretrained('KoljaB/SentenceFinishedClassification')
    print('Model downloads successful.')
except Exception as e:
    print(f'Error downloading SentenceFinishedClassification: {e}')
    exit(1)
EOF

# <<<--- Coqui TTS Model Pre-download --->>>
RUN echo "Preloading Coqui TTS Lasinya model..." && \
    python3 <<EOF
from huggingface_hub import hf_hub_download
import os
try:
    base = 'models/Lasinya'
    os.makedirs(base, exist_ok=True)
    files = ['config.json', 'vocab.json', 'speakers_xtts.pth', 'model.pth']
    for fn in files:
        print(f'Downloading {fn}...')
        hf_hub_download(repo_id='KoljaB/XTTS_Lasinya', filename=fn, local_dir=base)
    print('Coqui TTS model download successful.')
except Exception as e:
    print(f'Error downloading Coqui TTS model: {e}')
    exit(1)
EOF

# <<<--- Pre-initialize Speech Pipeline Components --->>>
RUN echo "Pre-initializing speech pipeline components..." && \
    python3 preinit.py || (echo "⚠️ Pre-initialization failed, but continuing with build..." && true)

# Create a non-root user and group - DO NOT switch to it here
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid 1001 --create-home appuser

# Ensure directories are owned by appuser - This prepares the image layers correctly
# The entrypoint will handle runtime permissions for volumes/cache
RUN mkdir -p /home/appuser/.cache && \
    chown -R appuser:appgroup /app && \
    chown -R appuser:appgroup /home/appuser && \
    # Also chown the caches potentially populated by root during build
    if [ -d /root/.cache ]; then chown -R appuser:appgroup /root/.cache; fi

# --- REMOVED USER appuser --- The container will start as root.

# --- Keep ENV vars ---
ENV HOME=/home/appuser
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="${CUDA_HOME}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}"
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV RUNNING_IN_DOCKER=true
ENV DS_BUILD_OPS=1
ENV DS_BUILD_CPU_ADAM=0
ENV DS_BUILD_FUSED_ADAM=0
ENV DS_BUILD_UTILS=0
ENV DS_BUILD_TRANSFORMER=1
ENV HF_HOME=${HOME}/.cache/huggingface
ENV TORCH_HOME=${HOME}/.cache/torch
ENV TRANSFORMERS_CACHE=${HOME}/.cache/huggingface/transformers
ENV HF_DATASETS_CACHE=${HOME}/.cache/huggingface/datasets
ENV RUNPOD_PREINITIALIZED=true

# Expose the port
EXPOSE 8000

# Command to run the handler (changed from original uvicorn server)
CMD ["python", "handler.py"] 