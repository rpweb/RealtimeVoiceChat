INPUT_SCHEMA = {
    "prompt": {
        "type": "string",
        "description": "Input text for the LLM to complete",
        "required": True
    },
    "messages": {
        "type": "array",
        "description": "Chat message history (preferred over 'prompt' if both are provided)",
        "required": False,
        "items": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["system", "user", "assistant"],
                    "description": "Role of the message sender"
                },
                "content": {
                    "type": "string",
                    "description": "Content of the message"
                }
            },
            "required": ["role", "content"]
        }
    },
    "temperature": {
        "type": "number",
        "description": "Sampling temperature (higher = more random)",
        "required": False,
        "default": 0.7
    },
    "max_tokens": {
        "type": "integer",
        "description": "Maximum number of tokens to generate",
        "required": False,
        "default": 512
    },
    "top_p": {
        "type": "number",
        "description": "Nucleus sampling probability threshold",
        "required": False,
        "default": 0.95
    },
    "top_k": {
        "type": "integer",
        "description": "Top-k sampling parameter (keep only top k tokens)",
        "required": False,
        "default": 50
    },
    "repetition_penalty": {
        "type": "number",
        "description": "Penalty for repeating tokens",
        "required": False,
        "default": 1.1
    },
    "presence_penalty": {
        "type": "number",
        "description": "Penalty for token presence in input",
        "required": False,
        "default": 0.0
    },
    "frequency_penalty": {
        "type": "number",
        "description": "Penalty for token frequency in input",
        "required": False,
        "default": 0.0
    },
    "stop": {
        "type": "array",
        "description": "List of sequences that trigger end of generation",
        "required": False,
        "items": {
            "type": "string"
        }
    }
} 