#!/usr/bin/env python3

import runpod
from handler import handler

# This is the correct way to start a runpod serverless worker in 1.6.0
if __name__ == "__main__":
    # Print version info
    print(f"Starting RunPod TTS Worker (Version: {runpod.__version__})")
    
    # The correct way to start a worker
    runpod.serverless.start({"handler": handler}) 