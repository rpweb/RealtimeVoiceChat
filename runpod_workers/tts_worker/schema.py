INPUT_SCHEMA = {
    "text": {
        "type": "string",
        "description": "Text to convert to speech",
        "required": True
    },
    "voice": {
        "type": "string",
        "description": "Voice to use for speech synthesis",
        "required": False,
        "default": "jenny",
        "enum": ["jenny", "lessac"]
    },
    "speed": {
        "type": "number",
        "description": "Speed of speech (0.5 to 2.0)",
        "required": False,
        "default": 1.0,
        "minimum": 0.5,
        "maximum": 2.0
    },
    "format": {
        "type": "string",
        "description": "Audio format",
        "required": False,
        "default": "mp3",
        "enum": ["mp3", "wav"]
    },
    "response_format": {
        "type": "string",
        "description": "How to return the audio data",
        "required": False,
        "default": "base64",
        "enum": ["base64", "url"]
    }
} 