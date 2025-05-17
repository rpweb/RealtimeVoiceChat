FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install CUDA - but this would require a CUDA-enabled base image
# For testing purposes, we'll continue without CUDA to check if runpod works

# Set working directory
WORKDIR /app

# Install RunPod first and verify installation
RUN pip install --no-cache-dir runpod==1.6.0 && \
    python -c "import runpod; print(f'RunPod version: {runpod.__version__}')"

# Install other dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY handler.py predict.py /app/
COPY schema.py /app/
COPY entrypoint.py /app/

# Make entrypoint executable
RUN chmod +x /app/entrypoint.py

# Expose port for API
EXPOSE 8000

# Set environment variable to force module path recognition
ENV PYTHONPATH=/app

# Use our debug entrypoint script
CMD ["python", "/app/entrypoint.py"] 