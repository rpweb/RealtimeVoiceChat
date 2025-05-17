import runpod
import os
import json
import time
from typing import Dict, Any, List, Optional
from predict import LLMGenerator

# Initialize the LLM generator with pre-loaded model
model_id = os.environ.get("MODEL_ID", "meta-llama/Meta-Llama-3-8B-Instruct")
llm_generator = LLMGenerator(model_id=model_id)
    
def handler(job):
    """
    Handle the serverless request
    """
    job_input = job["input"]
    
    start_time = time.time()
    
    try:
        prompt = job_input.get("prompt", "")
        if not prompt:
            return {"error": "No prompt provided. Please include a 'prompt' field."}
        
        # Get parameters for the LLM
        temperature = job_input.get("temperature", 0.7)
        max_tokens = job_input.get("max_tokens", 512)
        top_p = job_input.get("top_p", 0.95)
        top_k = job_input.get("top_k", 50)
        repetition_penalty = job_input.get("repetition_penalty", 1.1)
        presence_penalty = job_input.get("presence_penalty", 0.0)
        frequency_penalty = job_input.get("frequency_penalty", 0.0)
        stop_sequences = job_input.get("stop", [])
        
        # Extract conversation history if provided
        messages = job_input.get("messages", [])
        
        # Process the request
        if messages:
            # Process using chat-style API
            response = llm_generator.generate_chat_response(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                stop=stop_sequences,
            )
        else:
            # Process using completion-style API
            response = llm_generator.generate_completion(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                stop=stop_sequences,
            )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Add metadata to response
        result = {
            "response": response,
            "model": llm_generator.model_id,
            "processing_time": processing_time
        }
        
        return result
    
    except Exception as e:
        return {"error": str(e)}

# Start the runpod handler
runpod.serverless.start({"handler": handler}) 