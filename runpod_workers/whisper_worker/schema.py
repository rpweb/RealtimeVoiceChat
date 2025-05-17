INPUT_SCHEMA = {
    "audio": {
        "type": "string",
        "description": "URL to the audio file to transcribe",
        "required": False
    },
    "audio_base64": {
        "type": "string",
        "description": "Base64-encoded audio file to transcribe",
        "required": False
    },
    "model": {
        "type": "string",
        "description": "Whisper model to use (default is set in the worker)",
        "required": False,
        "default": "base.en"
    },
    "language": {
        "type": "string",
        "description": "Language spoken in the audio (specify None for auto-detection)",
        "required": False
    },
    "translate": {
        "type": "boolean",
        "description": "Whether to translate the transcription to English",
        "required": False,
        "default": False
    },
    "transcription": {
        "type": "string",
        "description": "Format for the transcription output",
        "required": False,
        "default": "plain_text",
        "enum": ["plain_text", "formatted_text", "srt", "vtt"]
    },
    "translation": {
        "type": "string",
        "description": "Format for the translation output (if translate=True)",
        "required": False,
        "default": "plain_text",
        "enum": ["plain_text", "formatted_text", "srt", "vtt"]
    },
    "temperature": {
        "type": "number",
        "description": "Temperature to use for sampling",
        "required": False,
        "default": 0
    },
    "best_of": {
        "type": "integer",
        "description": "Number of candidates when sampling with non-zero temperature",
        "required": False,
        "default": 5
    },
    "beam_size": {
        "type": "integer",
        "description": "Number of beams in beam search (only when temperature=0)",
        "required": False,
        "default": 5
    },
    "patience": {
        "type": "number",
        "description": "Patience value to use in beam decoding",
        "required": False
    },
    "length_penalty": {
        "type": "number",
        "description": "Length penalty coefficient (alpha) in beam search",
        "required": False
    },
    "suppress_tokens": {
        "type": "string",
        "description": "Comma-separated list of token IDs to suppress during sampling",
        "required": False,
        "default": "-1"
    },
    "initial_prompt": {
        "type": "string",
        "description": "Optional text to provide as a prompt for the first window",
        "required": False
    },
    "condition_on_previous_text": {
        "type": "boolean",
        "description": "Whether to use previous output as prompt for next window",
        "required": False,
        "default": True
    },
    "temperature_increment_on_fallback": {
        "type": "number",
        "description": "Temperature increment when falling back due to decoding failure",
        "required": False,
        "default": 0.2
    },
    "compression_ratio_threshold": {
        "type": "number",
        "description": "Gzip compression ratio threshold for failed decoding detection",
        "required": False,
        "default": 2.4
    },
    "logprob_threshold": {
        "type": "number",
        "description": "Average log probability threshold for failed decoding detection",
        "required": False,
        "default": -1.0
    },
    "no_speech_threshold": {
        "type": "number",
        "description": "Probability threshold for classifying a segment as silence",
        "required": False,
        "default": 0.6
    },
    "enable_vad": {
        "type": "boolean",
        "description": "Whether to use Voice Activity Detection to filter out non-speech",
        "required": False,
        "default": False
    },
    "word_timestamps": {
        "type": "boolean",
        "description": "Whether to include word-level timestamps in the output",
        "required": False,
        "default": False
    }
} 