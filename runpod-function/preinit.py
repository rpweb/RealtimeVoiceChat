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
        
        logger.info("📦 Creating SpeechPipelineManager...")
        speech_pipeline_manager = SpeechPipelineManager(
            tts_engine="coqui",
            llm_provider="openai", 
            llm_model="Qwen/Qwen2.5-7B-Instruct-AWQ",
            no_think=False,
            orpheus_model="orpheus-3b-0.1-ft-Q8_0-GGUF/orpheus-3b-0.1-ft-q8_0.gguf",
        )
        
        logger.info("📦 Creating UpsampleOverlap...")
        upsampler = UpsampleOverlap()
        
        logger.info("📦 Creating AudioInputProcessor...")
        audio_input_processor = AudioInputProcessor(
            "en",  # language
            is_orpheus=False,
            pipeline_latency=speech_pipeline_manager.full_output_pipeline_latency / 1000,
        )
        
        # Test TTS synthesis to warm up the engine
        logger.info("🔊 Testing TTS synthesis...")
        import threading
        import queue
        
        audio_queue = queue.Queue()
        stop_event = threading.Event()
        
        # Quick test synthesis
        success = speech_pipeline_manager.audio.synthesize(
            text="Hello, this is a test.",
            audio_chunks=audio_queue,
            stop_event=stop_event,
            generation_string="PreInit"
        )
        
        # Collect test audio
        test_chunks = []
        while not audio_queue.empty():
            try:
                chunk = audio_queue.get_nowait()
                test_chunks.append(chunk)
            except queue.Empty:
                break
        
        logger.info(f"🔊 TTS test completed: {len(test_chunks)} chunks generated")
        
        # Test upsampling
        if test_chunks:
            logger.info("📈 Testing audio upsampling...")
            combined_audio = b''.join(test_chunks)
            upsampled_b64 = upsampler.get_base64_chunk(combined_audio[:4096])  # Test with first 4KB
            final_chunk = upsampler.flush_base64_chunk()
            logger.info(f"📈 Upsampling test completed: {len(upsampled_b64)} chars base64")
        
        init_time = time.time() - start_time
        logger.info(f"✅ Pre-initialization completed successfully in {init_time:.2f}s")
        logger.info(f"🔊 TTS Engine: {speech_pipeline_manager.audio.engine_name}")
        logger.info(f"⏱️ Pipeline latency: {speech_pipeline_manager.full_output_pipeline_latency}ms")
        
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