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
    
    def process_audio_data(self, client_id: str, audio_data: str) -> Dict[str, Any]:
        """Process incoming audio data."""
        try:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            
            session = self.get_or_create_session(client_id)
            session["audio_buffer"] += audio_bytes
            
            # Process with audio input processor
            # This is a simplified version - in reality you'd need to handle
            # the async nature of the original audio processing
            
            return {
                "type": "audio_processed",
                "status": "success",
                "message": "Audio data received and buffered"
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing audio: {e}")
            return {
                "type": "error",
                "message": f"Audio processing failed: {str(e)}"
            }
    
    def process_text_message(self, client_id: str, text: str) -> Dict[str, Any]:
        """Process incoming text message."""
        try:
            session = self.get_or_create_session(client_id)
            
            # Add to conversation history
            session["conversation_history"].append({
                "role": "user",
                "content": text
            })
            
            # Generate response using the speech pipeline manager
            # This is simplified - you'd need to adapt the async methods
            response_text = f"Echo: {text}"  # Placeholder
            
            session["conversation_history"].append({
                "role": "assistant", 
                "content": response_text
            })
            
            return {
                "type": "text_response",
                "text": response_text,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing text: {e}")
            return {
                "type": "error",
                "message": f"Text processing failed: {str(e)}"
            }
    
    def synthesize_speech(self, client_id: str, text: str) -> Dict[str, Any]:
        """Synthesize speech from text."""
        try:
            # Use the speech pipeline manager to generate audio
            # This would need to be adapted for the async nature
            
            # Placeholder - return base64 encoded audio
            audio_data = b"placeholder_audio_data"
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            return {
                "type": "audio_response",
                "audio_data": audio_b64,
                "format": "wav",
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Error synthesizing speech: {e}")
            return {
                "type": "error",
                "message": f"Speech synthesis failed: {str(e)}"
            }

# Global processor instance
processor = VoiceChatProcessor()

def handler(event):
    """Main RunPod handler function."""
    try:
        # Initialize components if not already done
        initialize_components()
        
        # Extract input data
        input_data = event.get("input", {})
        message = input_data.get("message", {})
        client_id = input_data.get("client_id", "unknown")
        
        message_type = message.get("type", "")
        
        logger.info(f"🔄 Processing message type: {message_type} for client: {client_id}")
        
        # Route based on message type
        if message_type == "audio_data":
            audio_data = message.get("data", "")
            result = processor.process_audio_data(client_id, audio_data)
            
        elif message_type == "text_message":
            text = message.get("text", "")
            result = processor.process_text_message(client_id, text)
            
        elif message_type == "synthesize_speech":
            text = message.get("text", "")
            result = processor.synthesize_speech(client_id, text)
            
        elif message_type == "ping":
            result = {
                "type": "pong",
                "status": "success",
                "timestamp": str(asyncio.get_event_loop().time())
            }
            
        else:
            result = {
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }
        
        return {"output": result}
        
    except Exception as e:
        logger.error(f"❌ Handler error: {e}")
        return {
            "output": {
                "type": "error",
                "message": f"Handler failed: {str(e)}"
            }
        }

# Start the RunPod serverless function
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler}) 