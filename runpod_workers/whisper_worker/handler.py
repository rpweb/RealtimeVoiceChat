import runpod
import os
import time
import base64
import tempfile
import json
from typing import Dict, Any
from predict import WhisperTranscriber

# Initialize the transcriber
model_name = os.environ.get("MODEL", "base.en")
transcriber = WhisperTranscriber(model=model_name)

def save_base64_audio(audio_base64: str) -> str:
    """
    Save base64 encoded audio to a temporary file
    """
    audio_data = base64.b64decode(audio_base64.split(",")[-1] if "," in audio_base64 else audio_base64)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_file.write(audio_data)
    temp_file.close()
    return temp_file.name

def download_audio(url: str) -> str:
    """
    Download audio from URL to a temporary file
    """
    import requests
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    for chunk in response.iter_content(chunk_size=8192):
        temp_file.write(chunk)
    temp_file.close()
    return temp_file.name

def handler(job):
    """
    Handle the transcription request
    """
    job_input = job["input"]
    
    start_time = time.time()
    
    # Get the audio file
    audio_path = None
    try:
        if "audio" in job_input:
            audio_path = download_audio(job_input["audio"])
        elif "audio_base64" in job_input:
            audio_path = save_base64_audio(job_input["audio_base64"])
        else:
            return {"error": "No audio input provided. Please provide 'audio' URL or 'audio_base64'."}
        
        # Prepare parameters for transcription
        params = {
            "language": job_input.get("language", None),
            "task": "translate" if job_input.get("translate", False) else "transcribe",
            "temperature": job_input.get("temperature", 0),
            "best_of": job_input.get("best_of", 5),
            "beam_size": job_input.get("beam_size", 5),
            "patience": job_input.get("patience", None),
            "length_penalty": job_input.get("length_penalty", None),
            "suppress_tokens": job_input.get("suppress_tokens", "-1"),
            "initial_prompt": job_input.get("initial_prompt", None),
            "condition_on_previous_text": job_input.get("condition_on_previous_text", True),
            "temperature_increment_on_fallback": job_input.get("temperature_increment_on_fallback", 0.2),
            "compression_ratio_threshold": job_input.get("compression_ratio_threshold", 2.4),
            "logprob_threshold": job_input.get("logprob_threshold", -1.0),
            "no_speech_threshold": job_input.get("no_speech_threshold", 0.6),
            "word_timestamps": job_input.get("word_timestamps", False),
        }
        
        # Get the requested output format
        transcription_format = job_input.get("transcription", "plain_text")
        translation_format = job_input.get("translation", "plain_text")
        
        # Enable VAD if requested
        vad_filter = job_input.get("enable_vad", False)
        
        # Perform transcription
        result = transcriber.transcribe(
            audio_path, 
            params=params,
            transcription_format=transcription_format,
            translation_format=translation_format if params["task"] == "translate" else None,
            vad_filter=vad_filter
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        result["translation_time"] = processing_time
        result["model"] = model_name
        
        # Return the result
        return result
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        # Clean up temporary files
        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)

# Start the runpod handler
runpod.serverless.start({"handler": handler}) 