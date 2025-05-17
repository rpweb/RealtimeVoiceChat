FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install necessary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    wget \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -sf /usr/bin/python3 /usr/bin/python
RUN ln -sf /usr/bin/pip3 /usr/bin/pip

# Set working directory
WORKDIR /app

# Install PyTorch directly
RUN pip install --no-cache-dir torch==2.1.2 --index-url https://download.pytorch.org/whl/cu121

# Install runpod explicitly first
RUN pip install --no-cache-dir runpod==1.6.0

# Install Python dependencies with explicit vLLM version
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY handler.py predict.py /app/
COPY schema.py /app/

# Expose port for API
EXPOSE 8000

# Start the service
CMD ["python", "-m", "runpod.serverless.start"] 