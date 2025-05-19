# predict.py
import os
import time
import json
from typing import Dict, List, Any, Optional, Union, Iterator
import torch
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer

class LLMGenerator:
    def __init__(self, model_id: str = "mistralai/Mistral-7B-Instruct-v0.2"):
        """
        Initialize the LLM generator with a specified model
        
        Args:
            model_id: Hugging Face model ID or local path
        """
        self.model_id = model_id
        print(f"Loading model {model_id}...")
        gpu_count = int(os.environ.get("GPU_COUNT", torch.cuda.device_count()))
        gpu_memory_utilization = float(os.environ.get("GPU_MEMORY_UTILIZATION", 0.7))
        model_path = os.environ.get("MODEL_PATH", None)
        if model_path:
            print(f"Using custom model path: {model_path}")
            os.makedirs(model_path, exist_ok=True)
            os.environ["TRANSFORMERS_CACHE"] = model_path
            os.environ["HF_HOME"] = model_path
        hg_token = os.environ.get("HUGGINGFACE_API_KEY", None)
        self.llm = LLM(
            model=model_id,
            tensor_parallel_size=gpu_count,
            gpu_memory_utilization=gpu_memory_utilization,
            trust_remote_code=True
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            trust_remote_code=True,
            token=hg_token
        )
        print(f"Model {model_id} loaded successfully using {gpu_count} GPUs")
    
    def _format_chat_messages(self, messages: List[Dict[str, str]]) -> str:
        # Existing method (unchanged)
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
                prompt += f"{content}\n"
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
        stop: Optional[List[str]] = None,
        stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """
        Generate a response based on a chat message history, with optional streaming.
        """
        prompt = self._format_chat_messages(messages)
        return self.generate_completion(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            repetition_penalty=repetition_penalty,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            stop=stop,
            stream=stream
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
        stop: Optional[List[str]] = None,
        stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """
        Generate a completion for a given prompt, with optional streaming.
        """
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
        
        if stream:
            # Streaming generation
            def stream_generator() -> Iterator[str]:
                outputs = self.llm.generate(prompt, sampling_params, use_tqdm=False)
                for output in outputs:
                    for completion in output.outputs:
                        yield completion.text
            return stream_generator()
        else:
            # Non-streaming generation
            outputs = self.llm.generate(prompt, sampling_params)
            if outputs and len(outputs) > 0:
                return outputs[0].outputs[0].text
            return ""