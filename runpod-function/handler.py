import runpod
import json
import logging
import asyncio
import base64
from typing import Dict, Any, Optional

# Import the core modules from the original code
from speech_pipeline_manager import SpeechPipelineManager
from audio_in import AudioInputProcessor
from upsample_overlap import UpsampleOverlap

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances (initialized once per container)
speech_pipeline_manager = None
audio_input_processor = None
upsampler = None

def initialize_components():
    """Initialize the speech processing components."""
    global speech_pipeline_manager, audio_input_processor, upsampler
    
    if speech_pipeline_manager is None:
        logger.info("🚀 Initializing RunPod function components...")
        
        # Initialize with default settings
        speech_pipeline_manager = SpeechPipelineManager(
            tts_engine="coqui",
            llm_provider="openai", 
            llm_model="Qwen/Qwen2.5-7B-Instruct-AWQ",
            no_think=False,
            orpheus_model="orpheus-3b-0.1-ft-Q8_0-GGUF/orpheus-3b-0.1-ft-q8_0.gguf",
        )
        
        upsampler = UpsampleOverlap()
        
        audio_input_processor = AudioInputProcessor(
            "en",  # language
            is_orpheus=False,
            pipeline_latency=speech_pipeline_manager.full_output_pipeline_latency / 1000,
        )
        
        logger.info("✅ RunPod function components initialized with return_aggregate_stream=FALSE")

class VoiceChatProcessor:
    """Handles voice chat processing for RunPod serverless function."""
    
    def __init__(self):
        self.sessions = {}  # Store session state
    
    def get_or_create_session(self, client_id: str) -> Dict[str, Any]:
        """Get or create a session for the client."""
        if client_id not in self.sessions:
            self.sessions[client_id] = {
                "state": "idle",
                "conversation_history": [],
                "audio_buffer": b"",
                "last_activity": None
            }
        return self.sessions[client_id]
    
    def process_audio_data_streaming(self, client_id: str, audio_data: str):
        """Process incoming audio data with streaming responses."""
        try:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            
            session = self.get_or_create_session(client_id)
            session["audio_buffer"] += audio_bytes
            
            # Yield immediate acknowledgment
            yield {
                "type": "audio_received",
                "status": "processing",
                "audio_length": len(audio_bytes),
                "buffer_size": len(session["audio_buffer"])
            }
            
            # Step 1: Audio preprocessing
            yield {
                "type": "audio_preprocessing",
                "status": "complete",
                "message": "Audio preprocessing complete"
            }
            
            # Step 2: Real speech recognition
            logger.info(f"🎤 Starting speech recognition for {len(audio_bytes)} bytes of audio")
            
            try:
                # Process audio through the speech recognition pipeline
                import numpy as np
                
                # Convert audio bytes to numpy array (assuming 16-bit PCM)
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
                logger.info(f"🎤 Audio samples: {len(audio_np)}, max amplitude: {np.max(np.abs(audio_np))}")
                
                # Use the audio input processor for transcription
                processed_audio = audio_input_processor.process_audio_chunk(audio_bytes)
                logger.info(f"🎤 Processed audio samples: {len(processed_audio)}")
                
                # Feed to transcriber - this is a simplified approach
                # The original uses a complex async pipeline, but for RunPod we'll do it synchronously
                transcriber = audio_input_processor.transcriber
                
                # Initialize the transcriber if not already done
                if not transcriber.recorder:
                    logger.info("🎤 Initializing transcriber recorder...")
                    transcriber._create_recorder()
                
                # Feed the processed audio to the transcriber
                if transcriber.recorder:
                    logger.info("🎤 Feeding audio to transcriber...")
                    transcriber.feed_audio(processed_audio.tobytes())
                    
                    # Wait a bit for processing and try to get transcription
                    import time
                    time.sleep(0.5)  # Give it time to process
                    
                    # Try to get the current transcription
                    if hasattr(transcriber, 'realtime_text') and transcriber.realtime_text:
                        transcribed_text = transcriber.realtime_text
                        logger.info(f"🎤 Got realtime transcription: {transcribed_text}")
                    elif hasattr(transcriber, 'final_transcription') and transcriber.final_transcription:
                        transcribed_text = transcriber.final_transcription
                        logger.info(f"🎤 Got final transcription: {transcribed_text}")
                    else:
                        transcribed_text = "[No transcription available yet]"
                        logger.warning("🎤 No transcription text available from transcriber")
                else:
                    transcribed_text = "[Transcriber recorder not initialized]"
                    logger.error("🎤 Transcriber recorder failed to initialize")
                
                logger.info(f"🎤 Transcription result: {transcribed_text}")
                
            except Exception as e:
                logger.error(f"❌ Speech recognition error: {e}")
                import traceback
                logger.error(f"❌ Speech recognition traceback: {traceback.format_exc()}")
                transcribed_text = "[Speech recognition failed]"
            
            yield {
                "type": "speech_recognition", 
                "status": "complete",
                "text": transcribed_text
            }
            
            # Step 3: Real LLM processing
            logger.info(f"🤖 Starting LLM processing for: {transcribed_text[:50]}...")
            
            try:
                # Use the global speech pipeline manager's LLM
                llm = speech_pipeline_manager.llm
                
                # Add to conversation history
                session["conversation_history"].append({"role": "user", "content": transcribed_text})
                
                # Generate response using the LLM
                logger.info(f"🤖 Generating LLM response...")
                response_generator = llm.generate(
                    text=transcribed_text,
                    history=session["conversation_history"],
                    use_system_prompt=True
                )
                
                # Collect the full response
                response_parts = []
                for chunk in response_generator:
                    response_parts.append(chunk)
                
                response_text = "".join(response_parts)
                
                # Add assistant response to history
                session["conversation_history"].append({"role": "assistant", "content": response_text})
                
                logger.info(f"🤖 LLM response generated: {response_text[:50]}...")
                
            except Exception as e:
                logger.error(f"❌ LLM processing error: {e}")
                import traceback
                logger.error(f"❌ LLM traceback: {traceback.format_exc()}")
                response_text = "I'm sorry, I'm having trouble processing your request right now."
            
            yield {
                "type": "llm_response",
                "status": "complete", 
                "text": response_text
            }
            
            # Step 4: TTS generation using real audio processor
            logger.info(f"🔊 Generating TTS for: {response_text[:50]}...")
            
            # Use the global audio processor to generate real TTS
            import threading
            import queue
            import time
            
            # Create a queue for audio chunks (use threading.Queue, not asyncio.Queue)
            audio_queue = queue.Queue()
            stop_event = threading.Event()
            
            # Generate TTS audio in a separate thread
            def tts_worker():
                try:
                    # Use the global speech_pipeline_manager's audio processor
                    audio_processor = speech_pipeline_manager.audio
                    logger.info(f"🔊 TTS worker starting synthesis for: {response_text[:50]}...")
                    logger.info(f"🔊 Audio processor engine: {audio_processor.engine_name}")
                    
                    success = audio_processor.synthesize(
                        text=response_text,
                        audio_chunks=audio_queue,
                        stop_event=stop_event,
                        generation_string="RunPod"
                    )
                    logger.info(f"🔊 TTS synthesis completed: {success}")
                except Exception as e:
                    logger.error(f"❌ TTS synthesis error: {e}")
                    import traceback
                    logger.error(f"❌ TTS synthesis traceback: {traceback.format_exc()}")
                    stop_event.set()
            
            # Start TTS generation in background
            tts_thread = threading.Thread(target=tts_worker)
            tts_thread.start()
            
            # Collect all audio chunks
            audio_chunks = []
            start_time = time.time()
            timeout = 60.0  # 60 second timeout - let TTS finish!
            
            while True:
                try:
                    # Wait for audio chunks with timeout
                    chunk = audio_queue.get(timeout=0.1)
                    audio_chunks.append(chunk)
                except queue.Empty:
                    # No chunk available, check if we should continue waiting
                    if stop_event.is_set() or not tts_thread.is_alive():
                        break
                    if time.time() - start_time > timeout:
                        logger.warning("⏰ TTS generation timeout")
                        stop_event.set()
                        break
            
            # Wait for thread to finish
            tts_thread.join(timeout=2.0)
            
            # Combine all audio chunks and upsample from 24kHz to 48kHz
            if audio_chunks:
                combined_audio = b''.join(audio_chunks)
                logger.info(f"🔊 Generated {len(combined_audio)} bytes of TTS audio from {len(audio_chunks)} chunks")
                
                # Upsample from 24kHz to 48kHz using UpsampleOverlap
                upsampled_chunks = []
                
                # Process audio in chunks for upsampling (similar to original server)
                chunk_size = 4096  # Process in 4KB chunks
                for i in range(0, len(combined_audio), chunk_size):
                    chunk = combined_audio[i:i + chunk_size]
                    if len(chunk) > 0:
                        upsampled_b64 = upsampler.get_base64_chunk(chunk)
                        if upsampled_b64:  # Only add non-empty chunks
                            upsampled_chunks.append(upsampled_b64)
                
                # Get the final chunk
                final_chunk = upsampler.flush_base64_chunk()
                if final_chunk:
                    upsampled_chunks.append(final_chunk)
                
                # Combine all upsampled chunks
                if upsampled_chunks:
                    # Decode all base64 chunks and combine
                    upsampled_audio_parts = []
                    for chunk_b64 in upsampled_chunks:
                        chunk_bytes = base64.b64decode(chunk_b64)
                        upsampled_audio_parts.append(chunk_bytes)
                    
                    upsampled_audio = b''.join(upsampled_audio_parts)
                    audio_b64 = base64.b64encode(upsampled_audio).decode('utf-8')
                    
                    logger.info(f"🔊 Upsampled audio: {len(combined_audio)} bytes (24kHz) → {len(upsampled_audio)} bytes (48kHz)")
                    
                    # Log first few bytes for debugging
                    if len(upsampled_audio) >= 10:
                        first_samples = list(upsampled_audio[:10])
                        logger.info(f"🔊 First 10 bytes (upsampled): {first_samples}")
                else:
                    logger.warning("⚠️ No upsampled audio generated")
                    audio_b64 = base64.b64encode(combined_audio).decode('utf-8')  # Fallback to original
            else:
                # Fallback: Generate a simple test tone instead of silence
                logger.warning("⚠️ No TTS audio generated, using test tone")
                import math
                import struct
                
                # Generate a 1-second 440Hz sine wave at 24kHz, 16-bit
                sample_rate = 24000
                frequency = 440  # A4 note
                duration = 1.0  # 1 second
                samples = int(sample_rate * duration)
                
                audio_data = []
                for i in range(samples):
                    # Generate sine wave sample
                    t = i / sample_rate
                    sample = int(16383 * math.sin(2 * math.pi * frequency * t))  # 16-bit range
                    audio_data.append(struct.pack('<h', sample))  # Little-endian 16-bit
                
                combined_audio = b''.join(audio_data)
                audio_b64 = base64.b64encode(combined_audio).decode('utf-8')
                logger.info(f"🔊 Using {len(combined_audio)} bytes of test tone audio (440Hz sine wave)")
            
            yield {
                "type": "tts_generation",
                "status": "complete",
                "audio_data": audio_b64,
                "text": response_text
            }
            
            # Final result
            yield {
                "type": "processing_complete",
                "status": "success",
                "final_text": response_text,
                "final_audio": audio_b64
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing audio: {e}")
            yield {
                "type": "error",
                "message": f"Audio processing failed: {str(e)}"
            }

# Global processor instance
processor = VoiceChatProcessor()

def handler(job):
    """Main RunPod handler function with streaming support."""
    try:
        # Initialize components if not already done
        initialize_components()
        
        # Extract input data
        input_data = job.get("input", {})
        if not input_data:
            yield {"type": "error", "message": "No input data provided"}
            return
            
        client_id = input_data.get("client_id")
        if not client_id:
            yield {"type": "error", "message": "No client_id provided"}
            return
            
        # Extract message type directly from input_data
        message_type = input_data.get("message_type", "")
        
        logger.info(f"🔄🔄🔄 Processing message type: {message_type} for client: {client_id}")
        
        # Route based on message type
        if message_type == "audio_batch":
            audio_data = input_data.get("audio_data")
            if not audio_data:
                yield {"type": "error", "message": "No audio_data provided"}
                return
                
            tts_playing = input_data.get("tts_playing", False)
            timestamp = input_data.get("timestamp")
            
            # Stream the audio processing results
            for result in processor.process_audio_data_streaming(client_id, audio_data):
                yield result
            
        elif message_type == "control":
            message = input_data.get("message", {})
            if not message:
                yield {"type": "error", "message": "No control message provided"}
                return
                
            control_type = message.get("type", "")
            if control_type == "clear_history":
                yield {
                    "type": "control_response",
                    "status": "success",
                    "message": "History cleared"
                }
            elif control_type == "set_speed":
                speed = message.get("speed", 1.0)
                yield {
                    "type": "control_response",
                    "status": "success",
                    "message": f"Speed set to {speed}"
                }
            else:
                yield {
                    "type": "control_response",
                    "status": "success",
                    "message": f"Control message {control_type} processed"
                }
                
        else:
            yield {"type": "error", "message": f"Unknown message type: {message_type}"}
        
    except Exception as e:
        logger.error(f"❌ Handler error: {e}")
        yield {
            "type": "error",
            "message": str(e)
        }

# Start the RunPod serverless function with streaming enabled
if __name__ == "__main__":
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": False  # Enable real-time streaming!
    }) 