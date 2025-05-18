import runpod
import os
import json
import time
from typing import Dict, Any, List, Optional
from predict import LLMGenerator

# Initialize the LLM generator with pre-loaded model
# Using TinyLlama for testing as it's only ~2GB and initializes quickly
model_id = os.environ.get("MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.2")
llm_generator = LLMGenerator(model_id=model_id)
    
def handler(job):
    """
    Handle the serverless request
    """
    print(f"[DEBUG] Received job: {job}")
    
    job_input = job["input"]
    
    start_time = time.time()
    
    try:
        print(f"[DEBUG] Processing job input: {job_input}")
        
        # Check if we have messages (Vercel AI SDK format)
        messages = job_input.get("messages", [])
        
        # Get prompt if provided
        prompt = job_input.get("prompt", "")
        
        # Ensure we have either messages or a prompt
        if not messages and not prompt:
            print("[DEBUG] No prompt or messages provided")
            return {"error": "No prompt or messages provided. Please include either 'prompt' or 'messages' field."}
        
        # Get parameters for the LLM
        temperature = job_input.get("temperature", 0.7)
        max_tokens = job_input.get("max_tokens", 512)
        top_p = job_input.get("top_p", 0.95)
        top_k = job_input.get("top_k", 50)
        repetition_penalty = job_input.get("repetition_penalty", 1.1)
        presence_penalty = job_input.get("presence_penalty", 0.0)
        frequency_penalty = job_input.get("frequency_penalty", 0.0)
        stop_sequences = job_input.get("stop", [])
        
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
        print(f"[ERROR] Exception in handler: {str(e)}")
        return {"error": str(e)}

# Start the runpod handler
runpod.serverless.start({"handler": handler}) 