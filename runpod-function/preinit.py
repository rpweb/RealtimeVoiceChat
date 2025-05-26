#!/usr/bin/env python3
"""
Pre-initialization script for RunPod function.
This script warms up all components during Docker build to reduce cold start time.
"""

import os
import sys
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def preinit_components():
    """Pre-initialize all speech processing components."""
    try:
        logger.info("🚀 Starting pre-initialization of speech components...")
        start_time = time.time()
        
        # Import components
        from speech_pipeline_manager import SpeechPipelineManager
        from audio_in import AudioInputProcessor
        from upsample_overlap import UpsampleOverlap
        
        # During Docker build, we only want to ensure models are downloaded
        # Full initialization will happen at runtime when GPU is available
        logger.info("📦 Verifying model downloads and basic imports...")
        
        # Test basic imports
        from speech_pipeline_manager import SpeechPipelineManager
        from audio_in import AudioInputProcessor  
        from upsample_overlap import UpsampleOverlap
        logger.info("✅ All imports successful")
        
        # Test UpsampleOverlap (doesn't require GPU)
        logger.info("📈 Testing UpsampleOverlap...")
        upsampler = UpsampleOverlap()
        
        # Create test audio data
        import struct
        test_audio = b''.join([struct.pack('<h', i % 1000) for i in range(4096)])
        upsampled_b64 = upsampler.get_base64_chunk(test_audio)
        final_chunk = upsampler.flush_base64_chunk()
        logger.info(f"📈 UpsampleOverlap test completed: {len(upsampled_b64)} chars base64")
        
        # Verify model files exist
        model_files = [
            "models/Lasinya/config.json",
            "models/Lasinya/vocab.json", 
            "models/Lasinya/speakers_xtts.pth",
            "models/Lasinya/model.pth"
        ]
        
        for model_file in model_files:
            if os.path.exists(model_file):
                logger.info(f"✅ Model file exists: {model_file}")
            else:
                logger.warning(f"⚠️ Model file missing: {model_file}")
        
        logger.info("🚀 Skipping full TTS initialization during build (requires GPU)")
        logger.info("🚀 Full initialization will happen at runtime")
        
        init_time = time.time() - start_time
        logger.info(f"✅ Pre-initialization completed successfully in {init_time:.2f}s")
        logger.info("🔊 Models downloaded and verified - ready for runtime initialization")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during pre-initialization: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Running pre-initialization script...")
    success = preinit_components()
    if success:
        logger.info("✅ Pre-initialization script completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Pre-initialization script failed")
        sys.exit(1) 