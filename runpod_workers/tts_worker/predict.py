import os
import base64
import tempfile
import io
from typing import Dict, Any, Optional, List
import json
import numpy as np
from piper import PiperVoice
from pydub import AudioSegment

class TTSProcessor:
    def __init__(self):
        """
        Initialize the TTSProcessor with Piper TTS models
        """
        # Get model path from environment or use default
        self.models_dir = os.environ.get("MODEL_PATH", os.path.join(os.getcwd(), "models"))
        print(f"Using models directory: {self.models_dir}")
        
        # Ensure the models directory exists
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Load available models
        self.available_voices = {
            "lessac": os.path.join(self.models_dir, "en_US-lessac-medium.onnx")
        }
        
        # Check for additional voice models specified in environment
        additional_models_dir = os.environ.get("ADDITIONAL_MODELS_DIR", None)
        if additional_models_dir:
            print(f"Scanning additional models directory: {additional_models_dir}")
            if os.path.exists(additional_models_dir):
                for file in os.listdir(additional_models_dir):
                    if file.endswith(".onnx"):
                        voice_name = file.split('.')[0]
                        self.available_voices[voice_name] = os.path.join(additional_models_dir, file)
                        print(f"Found additional voice model: {voice_name}")
        
        # Load default voice
        self.default_voice = os.environ.get("DEFAULT_VOICE", "lessac")
        self.voice_instances = {}
        
        print(f"TTS processor initialized with Piper TTS. Available voices: {list(self.available_voices.keys())}")
    
    def _get_voice_instance(self, voice_name: str) -> PiperVoice:
        """
        Get a PiperVoice instance for the specified voice, creating it if necessary
        
        Args:
            voice_name: Name of the voice to use
            
        Returns:
            PiperVoice instance
        """
        if voice_name not in self.available_voices:
            raise ValueError(f"Voice '{voice_name}' not found. Available voices: {list(self.available_voices.keys())}")
        
        if voice_name not in self.voice_instances:
            model_path = self.available_voices[voice_name]
            config_path = f"{model_path}.json"
            
            # Load the model configuration
            with open(config_path, "r") as config_file:
                config = json.load(config_file)
            
            # Create the voice instance
            self.voice_instances[voice_name] = PiperVoice.load(model_path, config_path)
        
        return self.voice_instances[voice_name]
    
    def synthesize_speech(
        self,
        text: str,
        voice: str = "lessac",
        format: str = "mp3",
        speed: float = 1.0,
        response_format: str = "base64"
    ) -> Dict[str, Any]:
        """
        Synthesize speech from text using Piper TTS
        
        Args:
            text: Text to convert to speech
            voice: Voice name to use (lessac)
            format: Audio format (mp3 or wav)
            speed: Speed of speech (0.5 to 2.0)
            response_format: How to return the audio (base64 or url)
            
        Returns:
            Dictionary with speech data
        """
        try:
            # Validate inputs
            if voice not in self.available_voices:
                voice = self.default_voice
            
            if format not in ["mp3", "wav"]:
                format = "mp3"
            
            if speed < 0.5 or speed > 2.0:
                speed = 1.0
            
            # Get the voice instance
            voice_instance = self._get_voice_instance(voice)
            
            # Generate speech using Piper TTS
            audio_data, sample_rate = voice_instance.synthesize(text)
            
            # Convert to in-memory audio file
            audio_buffer = io.BytesIO()
            
            # Create an AudioSegment from the raw audio data
            audio_segment = AudioSegment(
                data=audio_data.tobytes(),
                sample_width=2,  # 16-bit audio
                frame_rate=sample_rate,
                channels=1,  # mono
            )
            
            # Apply speed adjustment if needed
            if speed != 1.0:
                audio_segment = audio_segment.speedup(playback_speed=speed)
            
            # Export to the desired format
            audio_segment.export(audio_buffer, format=format)
            audio_buffer.seek(0)
            
            if response_format == "base64":
                # Encode audio data as base64
                audio_base64 = base64.b64encode(audio_buffer.read()).decode("utf-8")
                
                return {
                    "audio_base64": audio_base64,
                    "format": format,
                    "voice": voice,
                    "speed": speed
                }
            else:  # url - save temporarily and return URL
                # Save to a temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}")
                temp_file.write(audio_buffer.read())
                temp_file.close()
                
                # For simplicity in this example, we'll just return the file path
                # In a real implementation, you would upload this to a storage service and return the URL
                return {
                    "audio_file_path": temp_file.name,
                    "format": format,
                    "voice": voice,
                    "speed": speed
                }
                
        except Exception as e:
            raise Exception(f"Speech synthesis failed: {str(e)}")
            
    def get_available_voices(self) -> List[str]:
        """
        Get a list of available voices
        
        Returns:
            List of voice names
        """
        return list(self.available_voices.keys())

    def upload_to_temporary_storage(self, file_path: str) -> str:
        """
        Upload a file to a temporary storage service and return the URL
        This is a placeholder - in a real implementation, you would integrate with
        your preferred storage service (S3, GCS, etc.)
        """
        # This is a dummy implementation
        # In a real scenario, you would upload the file to a storage service and return the URL
        return f"https://example.com/temp/{os.path.basename(file_path)}" 