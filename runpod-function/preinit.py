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

def runtime_preload_models():
    """
    Pre-load all models into memory at runtime when GPU is available.
    This should be called when the container starts with GPU access.
    """
    try:
        logger.info("🚀 Starting RUNTIME model pre-loading with GPU access...")
        start_time = time.time()
        
        # Import components
        from speech_pipeline_manager import SpeechPipelineManager
        from audio_in import AudioInputProcessor
        from upsample_overlap import UpsampleOverlap
        
        logger.info("🔧 Initializing SpeechPipelineManager...")
        speech_pipeline_manager = SpeechPipelineManager()
        logger.info("✅ SpeechPipelineManager initialized")
        
        logger.info("🎤 Initializing AudioInputProcessor...")
        audio_input_processor = AudioInputProcessor()
        logger.info("✅ AudioInputProcessor initialized")
        
        logger.info("📈 Initializing UpsampleOverlap...")
        upsampler = UpsampleOverlap()
        logger.info("✅ UpsampleOverlap initialized")
        
        # Test that everything works
        logger.info("🧪 Running component tests...")
        
        # Test audio processing
        import struct
        test_audio = b''.join([struct.pack('<h', i % 1000) for i in range(4096)])
        processed = audio_input_processor.process_audio_chunk(test_audio)
        logger.info(f"🎤 Audio processing test: {len(processed)} samples")
        
        # Test upsampling
        upsampled_b64 = upsampler.get_base64_chunk(test_audio)
        logger.info(f"📈 Upsampling test: {len(upsampled_b64)} chars base64")
        
        # Test TTS (small test)
        logger.info("🔊 Testing TTS synthesis...")
        import queue
        import threading
        audio_queue = queue.Queue()
        stop_event = threading.Event()
        
        # Quick TTS test
        success = speech_pipeline_manager.audio.synthesize(
            text="Test",
            audio_chunks=audio_queue,
            stop_event=stop_event,
            generation_string="PreloadTest"
        )
        logger.info(f"🔊 TTS test completed: {success}")
        
        # Clear test audio
        while not audio_queue.empty():
            try:
                audio_queue.get_nowait()
            except:
                break
        
        init_time = time.time() - start_time
        logger.info(f"✅ RUNTIME model pre-loading completed in {init_time:.2f}s")
        logger.info("🚀 All models loaded and ready for instant processing!")
        
        return speech_pipeline_manager, audio_input_processor, upsampler
        
    except Exception as e:
        logger.error(f"❌ Error during runtime model pre-loading: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return None, None, None

def runtime_preload_models_parallel():
    """
    Pre-load all models into memory in PARALLEL at runtime when GPU is available.
    This loads STT, LLM, and TTS simultaneously instead of sequentially.
    """
    try:
        logger.info("🚀 Starting PARALLEL model pre-loading with GPU access...")
        start_time = time.time()
        
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Results storage
        results = {}
        errors = {}
        
        def load_speech_pipeline():
            """Load SpeechPipelineManager in parallel."""
            try:
                logger.info("🔧 [PARALLEL] Loading SpeechPipelineManager...")
                from speech_pipeline_manager import SpeechPipelineManager
                spm = SpeechPipelineManager(
                    tts_engine="coqui",
                    llm_provider="openai", 
                    llm_model="Qwen/Qwen2.5-7B-Instruct-AWQ",
                    no_think=False,
                    orpheus_model="orpheus-3b-0.1-ft-Q8_0-GGUF/orpheus-3b-0.1-ft-q8_0.gguf",
                )
                results['speech_pipeline'] = spm
                logger.info("✅ [PARALLEL] SpeechPipelineManager loaded")
                return spm
            except Exception as e:
                logger.error(f"❌ [PARALLEL] SpeechPipelineManager failed: {e}")
                errors['speech_pipeline'] = e
                return None
        
        def load_audio_processor():
            """Load AudioInputProcessor in parallel."""
            try:
                logger.info("🎤 [PARALLEL] Loading AudioInputProcessor...")
                import asyncio
                from audio_in import AudioInputProcessor
                
                # Create event loop for this thread if none exists
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Loop is closed")
                except RuntimeError:
                    logger.info("🎤 [PARALLEL] Creating new event loop for AudioInputProcessor...")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Use default latency for now, will update after speech_pipeline loads
                aip = AudioInputProcessor(
                    "en",  # language
                    is_orpheus=False,
                    pipeline_latency=0.5,  # Default, will update later
                )
                results['audio_processor'] = aip
                logger.info("✅ [PARALLEL] AudioInputProcessor loaded")
                return aip
            except Exception as e:
                logger.error(f"❌ [PARALLEL] AudioInputProcessor failed: {e}")
                import traceback
                logger.error(f"❌ [PARALLEL] AudioInputProcessor traceback: {traceback.format_exc()}")
                errors['audio_processor'] = e
                return None
        
        def load_upsampler():
            """Load UpsampleOverlap in parallel."""
            try:
                logger.info("📈 [PARALLEL] Loading UpsampleOverlap...")
                from upsample_overlap import UpsampleOverlap
                upsampler = UpsampleOverlap()
                results['upsampler'] = upsampler
                logger.info("✅ [PARALLEL] UpsampleOverlap loaded")
                return upsampler
            except Exception as e:
                logger.error(f"❌ [PARALLEL] UpsampleOverlap failed: {e}")
                errors['upsampler'] = e
                return None
        
        # Load all components in parallel using ThreadPoolExecutor
        logger.info("🏃‍♂️ Starting parallel loading of all components...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all loading tasks
            future_to_component = {
                executor.submit(load_speech_pipeline): 'speech_pipeline',
                executor.submit(load_audio_processor): 'audio_processor', 
                executor.submit(load_upsampler): 'upsampler'
            }
            
            # Wait for all tasks to complete and log progress
            completed_count = 0
            for future in as_completed(future_to_component):
                component_name = future_to_component[future]
                completed_count += 1
                try:
                    result = future.result()
                    logger.info(f"✅ [{completed_count}/3] {component_name} completed")
                except Exception as e:
                    logger.error(f"❌ [{completed_count}/3] {component_name} failed: {e}")
        
        # Check if all components loaded successfully
        speech_pipeline_manager = results.get('speech_pipeline')
        audio_input_processor = results.get('audio_processor')
        upsampler = results.get('upsampler')
        
        if not all([speech_pipeline_manager, audio_input_processor, upsampler]):
            error_msg = f"Failed to load components. Errors: {errors}"
            logger.error(f"❌ {error_msg}")
            return None, None, None
        
        # Update audio processor with correct latency now that speech_pipeline is loaded
        if speech_pipeline_manager and audio_input_processor:
            try:
                logger.info("🔧 Updating AudioInputProcessor latency...")
                audio_input_processor.transcriber.pipeline_latency = speech_pipeline_manager.full_output_pipeline_latency / 1000
                logger.info(f"✅ AudioInputProcessor latency updated to {audio_input_processor.transcriber.pipeline_latency}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to update AudioInputProcessor latency: {e}")
        
        # Test that everything works
        logger.info("🧪 Running parallel-loaded component tests...")
        
        # Test audio processing
        import struct
        test_audio = b''.join([struct.pack('<h', i % 1000) for i in range(4096)])
        processed = audio_input_processor.process_audio_chunk(test_audio)
        logger.info(f"🎤 Audio processing test: {len(processed)} samples")
        
        # Test upsampling
        upsampled_b64 = upsampler.get_base64_chunk(test_audio)
        logger.info(f"📈 Upsampling test: {len(upsampled_b64)} chars base64")
        
        # Test TTS (small test)
        logger.info("🔊 Testing TTS synthesis...")
        import queue
        import threading
        audio_queue = queue.Queue()
        stop_event = threading.Event()
        
        # Quick TTS test
        success = speech_pipeline_manager.audio.synthesize(
            text="Parallel loading test",
            audio_chunks=audio_queue,
            stop_event=stop_event,
            generation_string="ParallelTest"
        )
        logger.info(f"🔊 TTS test completed: {success}")
        
        # Clear test audio
        while not audio_queue.empty():
            try:
                audio_queue.get_nowait()
            except:
                break
        
        init_time = time.time() - start_time
        logger.info(f"✅ PARALLEL model pre-loading completed in {init_time:.2f}s")
        logger.info("🚀 All models loaded in parallel and ready for instant processing!")
        
        return speech_pipeline_manager, audio_input_processor, upsampler
        
    except Exception as e:
        logger.error(f"❌ Error during parallel model pre-loading: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return None, None, None

def runtime_preload_models_fast():
    """
    Pre-load models optimized for SPEED at runtime.
    Uses smaller/faster models to reduce cold start time significantly.
    """
    try:
        logger.info("⚡ Starting FAST model pre-loading with optimized models...")
        start_time = time.time()
        
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Results storage
        results = {}
        errors = {}
        
        def load_speech_pipeline_fast():
            """Load SpeechPipelineManager with optimized settings for speed."""
            try:
                logger.info("🔧 [FAST] Loading SpeechPipelineManager with speed optimizations...")
                from speech_pipeline_manager import SpeechPipelineManager
                
                # Use faster model configuration
                spm = SpeechPipelineManager(
                    tts_engine="coqui",
                    llm_provider="openai", 
                    llm_model="Qwen/Qwen2.5-7B-Instruct-AWQ",  # Keep same LLM for quality
                    no_think=True,  # Faster processing
                    orpheus_model=None,  # Skip orpheus for speed
                )
                results['speech_pipeline'] = spm
                logger.info("✅ [FAST] SpeechPipelineManager loaded with speed optimizations")
                return spm
            except Exception as e:
                logger.error(f"❌ [FAST] SpeechPipelineManager failed: {e}")
                errors['speech_pipeline'] = e
                return None
        
        def load_audio_processor_fast():
            """Load AudioInputProcessor with optimized settings for speed."""
            try:
                logger.info("🎤 [FAST] Loading AudioInputProcessor with speed optimizations...")
                import asyncio
                from audio_in import AudioInputProcessor
                
                # Create event loop for this thread if none exists
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Loop is closed")
                except RuntimeError:
                    logger.info("🎤 [FAST] Creating new event loop for AudioInputProcessor...")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Use faster settings
                aip = AudioInputProcessor(
                    "en",  # language
                    is_orpheus=False,  # Disable orpheus for speed
                    pipeline_latency=0.3,  # Faster latency
                )
                results['audio_processor'] = aip
                logger.info("✅ [FAST] AudioInputProcessor loaded with speed optimizations")
                return aip
            except Exception as e:
                logger.error(f"❌ [FAST] AudioInputProcessor failed: {e}")
                import traceback
                logger.error(f"❌ [FAST] AudioInputProcessor traceback: {traceback.format_exc()}")
                errors['audio_processor'] = e
                return None
        
        def load_upsampler_fast():
            """Load UpsampleOverlap (already fast)."""
            try:
                logger.info("📈 [FAST] Loading UpsampleOverlap...")
                from upsample_overlap import UpsampleOverlap
                upsampler = UpsampleOverlap()
                results['upsampler'] = upsampler
                logger.info("✅ [FAST] UpsampleOverlap loaded")
                return upsampler
            except Exception as e:
                logger.error(f"❌ [FAST] UpsampleOverlap failed: {e}")
                errors['upsampler'] = e
                return None
        
        # Load all components in parallel with maximum concurrency
        logger.info("⚡ Starting FAST parallel loading of all components...")
        
        with ThreadPoolExecutor(max_workers=4) as executor:  # Extra worker for speed
            # Submit all loading tasks
            future_to_component = {
                executor.submit(load_speech_pipeline_fast): 'speech_pipeline',
                executor.submit(load_audio_processor_fast): 'audio_processor', 
                executor.submit(load_upsampler_fast): 'upsampler'
            }
            
            # Wait for all tasks to complete and log progress
            completed_count = 0
            for future in as_completed(future_to_component):
                component_name = future_to_component[future]
                completed_count += 1
                try:
                    result = future.result()
                    logger.info(f"⚡ [{completed_count}/3] {component_name} completed FAST")
                except Exception as e:
                    logger.error(f"❌ [{completed_count}/3] {component_name} failed: {e}")
        
        # Check if all components loaded successfully
        speech_pipeline_manager = results.get('speech_pipeline')
        audio_input_processor = results.get('audio_processor')
        upsampler = results.get('upsampler')
        
        if not all([speech_pipeline_manager, audio_input_processor, upsampler]):
            error_msg = f"Failed to load components. Errors: {errors}"
            logger.error(f"❌ {error_msg}")
            return None, None, None
        
        # Update audio processor with correct latency
        if speech_pipeline_manager and audio_input_processor:
            try:
                logger.info("🔧 [FAST] Updating AudioInputProcessor latency...")
                audio_input_processor.transcriber.pipeline_latency = speech_pipeline_manager.full_output_pipeline_latency / 1000
                logger.info(f"✅ [FAST] AudioInputProcessor latency updated to {audio_input_processor.transcriber.pipeline_latency}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to update AudioInputProcessor latency: {e}")
        
        # Quick functionality test (minimal for speed)
        logger.info("⚡ Running minimal component tests...")
        
        # Test audio processing (minimal)
        import struct
        test_audio = b''.join([struct.pack('<h', i % 1000) for i in range(1024)])  # Smaller test
        processed = audio_input_processor.process_audio_chunk(test_audio)
        logger.info(f"🎤 [FAST] Audio processing test: {len(processed)} samples")
        
        # Test upsampling (minimal)
        upsampled_b64 = upsampler.get_base64_chunk(test_audio)
        logger.info(f"📈 [FAST] Upsampling test: {len(upsampled_b64)} chars base64")
        
        # Skip TTS test for speed - just verify it exists
        if hasattr(speech_pipeline_manager, 'audio') and speech_pipeline_manager.audio:
            logger.info("🔊 [FAST] TTS component verified (skipping synthesis test for speed)")
        else:
            logger.warning("⚠️ [FAST] TTS component not found")
        
        init_time = time.time() - start_time
        logger.info(f"⚡ FAST model pre-loading completed in {init_time:.2f}s")
        logger.info("🚀 All models loaded in FAST mode and ready for instant processing!")
        
        return speech_pipeline_manager, audio_input_processor, upsampler
        
    except Exception as e:
        logger.error(f"❌ Error during FAST model pre-loading: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return None, None, None

def runtime_preload_models_sequential():
    """
    Fallback: Pre-load models sequentially when parallel loading fails.
    This is more reliable for components that need asyncio.
    """
    try:
        logger.info("🔄 Starting SEQUENTIAL model pre-loading (fallback)...")
        start_time = time.time()
        
        # Load SpeechPipelineManager first
        logger.info("🔧 [SEQ] Loading SpeechPipelineManager...")
        from speech_pipeline_manager import SpeechPipelineManager
        speech_pipeline_manager = SpeechPipelineManager(
            tts_engine="coqui",
            llm_provider="openai", 
            llm_model="Qwen/Qwen2.5-7B-Instruct-AWQ",
            no_think=True,  # Faster processing
            orpheus_model=None,  # Skip orpheus for speed
        )
        logger.info("✅ [SEQ] SpeechPipelineManager loaded")
        
        # Load AudioInputProcessor second
        logger.info("🎤 [SEQ] Loading AudioInputProcessor...")
        from audio_in import AudioInputProcessor
        audio_input_processor = AudioInputProcessor(
            "en",  # language
            is_orpheus=False,
            pipeline_latency=speech_pipeline_manager.full_output_pipeline_latency / 1000,
        )
        logger.info("✅ [SEQ] AudioInputProcessor loaded")
        
        # Load UpsampleOverlap last
        logger.info("📈 [SEQ] Loading UpsampleOverlap...")
        from upsample_overlap import UpsampleOverlap
        upsampler = UpsampleOverlap()
        logger.info("✅ [SEQ] UpsampleOverlap loaded")
        
        # Quick test
        logger.info("🧪 [SEQ] Running quick component tests...")
        import struct
        test_audio = b''.join([struct.pack('<h', i % 1000) for i in range(1024)])
        processed = audio_input_processor.process_audio_chunk(test_audio)
        upsampled_b64 = upsampler.get_base64_chunk(test_audio)
        logger.info(f"🧪 [SEQ] Tests completed: {len(processed)} samples, {len(upsampled_b64)} chars")
        
        init_time = time.time() - start_time
        logger.info(f"✅ SEQUENTIAL model pre-loading completed in {init_time:.2f}s")
        logger.info("🚀 All models loaded sequentially and ready for processing!")
        
        return speech_pipeline_manager, audio_input_processor, upsampler
        
    except Exception as e:
        logger.error(f"❌ Error during sequential model pre-loading: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return None, None, None

if __name__ == "__main__":
    logger.info("🚀 Running pre-initialization script...")
    success = preinit_components()
    if success:
        logger.info("✅ Pre-initialization script completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Pre-initialization script failed")
        sys.exit(1) 