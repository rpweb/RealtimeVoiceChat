import os
import base64
import tempfile
import io
from typing import Dict, Any, Optional, List
import json
from piper import PiperVoice
from pydub import AudioSegment
import urllib.request
import subprocess
import re

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
        
        # Download the default model if it doesn't exist
        self.ensure_model_is_downloaded()
        
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
    
    def ensure_model_is_downloaded(self):
        """
        Check if the default model exists, download if not
        """
        model_path = os.path.join(self.models_dir, "en_US-lessac-medium.onnx")
        model_config_path = os.path.join(self.models_dir, "en_US-lessac-medium.onnx.json")
        
        # Check if model files already exist
        if os.path.exists(model_path) and os.path.exists(model_config_path):
            print(f"Model files already exist at {self.models_dir}")
            return
        
        print(f"Downloading model files to {self.models_dir}...")
        
        # Model URLs
        model_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
        config_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
        
        try:
            # Download model file
            print(f"Downloading model file from {model_url}")
            urllib.request.urlretrieve(model_url, model_path)
            
            # Download config file
            print(f"Downloading config file from {config_url}")
            urllib.request.urlretrieve(config_url, model_config_path)
            
            print("Model files downloaded successfully")
        except Exception as e:
            print(f"Error downloading model files: {str(e)}")
            raise
    
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
            # Create temporary files for WAV input/output
            temp_wav_path = None
            temp_output_path = None
            
            try:
                # Create a temporary file for Piper output
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    temp_wav_path = temp_wav.name
                
                # Synthesize speech using Piper
                print(f"Synthesizing speech to {temp_wav_path}")
                voice_instance.synthesize(text, temp_wav_path)
                
                # Verify the file exists and has content
                if not os.path.exists(temp_wav_path) or os.path.getsize(temp_wav_path) == 0:
                    raise Exception(f"Piper failed to generate audio file at {temp_wav_path}")
                
                print(f"Generated audio file size: {os.path.getsize(temp_wav_path)} bytes")
                
                # Create a temporary output file for the desired format
                with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_out:
                    temp_output_path = temp_out.name
                
                # Use ffmpeg directly to convert the file and apply speed adjustment
                speed_filter = f",atempo={speed}" if speed != 1.0 else ""
                cmd = [
                    "ffmpeg", "-y",
                    "-i", temp_wav_path,
                    "-filter:a", f"aresample=44100{speed_filter}",
                    "-f", format,
                    temp_output_path
                ]
                
                print(f"Running command: {' '.join(cmd)}")
                subprocess.run(cmd, check=True, capture_output=True)
                
                # Read the processed audio file
                with open(temp_output_path, "rb") as audio_file:
                    audio_data = audio_file.read()
                
                if response_format == "base64":
                    # Encode audio data as base64
                    audio_base64 = base64.b64encode(audio_data).decode("utf-8")
                    
                    return {
                        "audio_base64": audio_base64,
                        "format": format,
                        "voice": voice,
                        "speed": speed
                    }
                else:  # url - save temporarily and return URL
                    # Save to a temporary file
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}")
                    temp_file.write(audio_data)
                    temp_file.close()
                    
                    # For simplicity in this example, we'll just return the file path
                    return {
                        "audio_file_path": temp_file.name,
                        "format": format,
                        "voice": voice,
                        "speed": speed
                    }
                    
            except Exception as e:
                print(f"Error during synthesis: {str(e)}")
                raise Exception(f"Speech synthesis failed: {str(e)}")
            finally:
                # Clean up temporary files
                for temp_file in [temp_wav_path, temp_output_path]:
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.unlink(temp_file)
                            print(f"Removed temporary file: {temp_file}")
                        except Exception as e:
                            print(f"Failed to remove temporary file {temp_file}: {str(e)}")
                
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

    def synthesize_speech_by_sentences(
        self,
        text: str,
        voice: str = "lessac",
        format: str = "mp3",
        speed: float = 1.0,
        response_format: str = "base64"
    ) -> List[Dict[str, Any]]:
        """
        Synthesize speech sentence by sentence for streaming output
        
        Args:
            text: Text to convert to speech
            voice: Voice name to use (lessac)
            format: Audio format (mp3 or wav)
            speed: Speed of speech (0.5 to 2.0)
            response_format: How to return the audio (base64 or url)
            
        Returns:
            List of dictionaries with speech data for each sentence
        """
        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter out empty sentences
        sentences = [s for s in sentences if s.strip()]
        
        results = []
        
        # Process each sentence
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Synthesize this sentence
            result = self.synthesize_speech(
                text=sentence,
                voice=voice,
                format=format,
                speed=speed,
                response_format=response_format
            )
            
            # Add sentence to the result
            result["sentence"] = sentence
            results.append(result)
            
        return results 