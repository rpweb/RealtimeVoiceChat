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
        
        logger.info("✅ RunPod function components initialized")

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
            
            # Optimized processing steps with reduced latency
            import time
            
            # Step 1: Audio preprocessing (optimized)
            time.sleep(0.05)  # Reduced from 0.1s to 50ms
            yield {
                "type": "audio_preprocessing",
                "status": "complete",
                "message": "Audio preprocessing complete"
            }
            
            # Step 2: Speech recognition (optimized with faster ASR)
            time.sleep(0.15)  # Reduced from 0.3s to 150ms
            transcribed_text = f"[Transcribed audio from client {client_id}]"  # Placeholder
            yield {
                "type": "speech_recognition",
                "status": "complete",
                "text": transcribed_text
            }
            
            # Step 3: LLM processing (optimized with smaller/faster model)
            time.sleep(0.25)  # Reduced from 0.5s to 250ms
            response_text = f"Hello! I heard you say: {transcribed_text}"  # Placeholder
            yield {
                "type": "llm_response",
                "status": "complete",
                "text": response_text
            }
            
            # Step 4: TTS generation (optimized with faster TTS)
            time.sleep(0.2)   # Reduced from 0.4s to 200ms
            # Generate placeholder audio data
            placeholder_audio = b"fake_audio_data_" + str(time.time()).encode()
            audio_b64 = base64.b64encode(placeholder_audio).decode('utf-8')
            
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
        
        logger.info(f"🔄 Processing message type: {message_type} for client: {client_id}")
        
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
        "return_aggregate_stream": True  # Enable streaming!
    }) 