import runpod
import os
import time
import base64
import json
from typing import Dict, Any
from predict import TTSProcessor

# Initialize the TTS processor
tts_processor = TTSProcessor()

def handler(job):
    """
    Handle the TTS request
    """
    job_input = job["input"]
    
    start_time = time.time()
    
    # Get the text input
    try:
        text = job_input.get("text")
        if not text:
            return {"error": "No text provided. Please include a 'text' field."}
        
        # Get TTS parameters
        voice = job_input.get("voice", "lessac")  # Default to lessac voice
        speed = job_input.get("speed", 1.0)
        format = job_input.get("format", "mp3")
        response_format = job_input.get("response_format", "base64")  # 'base64' or 'url'
        
        # Process the request
        result = tts_processor.synthesize_speech(
            text=text,
            voice=voice,
            format=format,
            speed=speed,
            response_format=response_format
        )
        
        # Add available voices to the response
        result["available_voices"] = tts_processor.get_available_voices()
        
        # Calculate processing time
        processing_time = time.time() - start_time
        result["processing_time"] = processing_time
        
        return result
    
    except Exception as e:
        return {"error": str(e)}

# Start the runpod handler
runpod.serverless.start({"handler": handler}) 