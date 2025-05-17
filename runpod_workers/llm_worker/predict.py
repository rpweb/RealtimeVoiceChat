import os
import time
import json
from typing import Dict, List, Any, Optional, Union

import torch
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer

class LLMGenerator:
    def __init__(self, model_id: str = "meta-llama/Meta-Llama-3-8B-Instruct"):
        """
        Initialize the LLM generator with a specified model
        
        Args:
            model_id: Hugging Face model ID or local path
        """
        self.model_id = model_id
        print(f"Loading model {model_id}...")
        
        # Initialize vLLM engine
        self.llm = LLM(
            model=model_id,
            tensor_parallel_size=torch.cuda.device_count(),
            gpu_memory_utilization=0.9,
            trust_remote_code=True
        )
        
        # Load tokenizer for token counting
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        
        print(f"Model {model_id} loaded successfully")
    
    def _format_chat_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Format chat messages into a prompt string
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            
        Returns:
            Formatted prompt string
        """
        # Simple formatting for Llama 3 chat format
        prompt = ""
        for message in messages:
            role = message.get("role", "").lower()
            content = message.get("content", "")
            
            if role == "system":
                prompt += f"<|system|>\n{content}\n"
            elif role == "user":
                prompt += f"<|user|>\n{content}\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}\n"
            else:
                # Handle other roles (fallback to appending content)
                prompt += f"{content}\n"
        
        # Add final assistant prompt if last message is not from assistant
        if not messages or messages[-1].get("role", "").lower() != "assistant":
            prompt += "<|assistant|>\n"
            
        return prompt
    
    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
        top_p: float = 0.95,
        top_k: int = 50,
        repetition_penalty: float = 1.1,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Generate a response based on a chat message history
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling probability
            top_k: Top-k sampling parameter
            repetition_penalty: Penalty for repeating tokens
            presence_penalty: Penalty for token presence in prompt
            frequency_penalty: Penalty for token frequency in prompt
            stop: List of stop sequences
            
        Returns:
            Generated response text
        """
        # Format chat messages into prompt
        prompt = self._format_chat_messages(messages)
        
        # Generate response using the formatted prompt
        return self.generate_completion(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            repetition_penalty=repetition_penalty,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            stop=stop
        )
    
    def generate_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 512,
        top_p: float = 0.95,
        top_k: int = 50,
        repetition_penalty: float = 1.1,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Generate a completion for a given prompt
        
        Args:
            prompt: Input text prompt
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling probability
            top_k: Top-k sampling parameter
            repetition_penalty: Penalty for repeating tokens
            presence_penalty: Penalty for token presence in prompt
            frequency_penalty: Penalty for token frequency in prompt
            stop: List of stop sequences
            
        Returns:
            Generated text completion
        """
        # Configure sampling parameters
        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            repetition_penalty=repetition_penalty,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            stop=stop if stop else None
        )
        
        # Generate response
        outputs = self.llm.generate(prompt, sampling_params)
        
        # Extract generated text
        if outputs and len(outputs) > 0:
            generated_text = outputs[0].outputs[0].text
            return generated_text
        
        return "" 