import os
import torch
import numpy as np
from typing import Dict, List, Optional, Union, Any
from faster_whisper import WhisperModel

class WhisperTranscriber:
    def __init__(self, model="base.en"):
        """
        Initialize the WhisperTranscriber
        
        Args:
            model: The name of the Whisper model to use
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "float32"
        
        print(f"Loading model {model} on {self.device}...")
        self.model = WhisperModel(model, device=self.device, compute_type=self.compute_type)
        print("Model loaded successfully")
    
    def transcribe(
        self, 
        audio_path: str, 
        params: Dict[str, Any] = {},
        transcription_format: str = "plain_text",
        translation_format: Optional[str] = None,
        vad_filter: bool = False
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper
        
        Args:
            audio_path: Path to the audio file
            params: Parameters for the Whisper model
            transcription_format: Output format for transcription
            translation_format: Output format for translation
            vad_filter: Whether to use VAD filtering
            
        Returns:
            Dict containing transcription results
        """
        segments, info = self.model.transcribe(
            audio_path,
            language=params.get("language"),
            task=params.get("task", "transcribe"),
            temperature=params.get("temperature", 0),
            best_of=params.get("best_of", 5),
            beam_size=params.get("beam_size", 5),
            patience=params.get("patience"),
            length_penalty=params.get("length_penalty"),
            suppress_tokens=params.get("suppress_tokens"),
            initial_prompt=params.get("initial_prompt"),
            condition_on_previous_text=params.get("condition_on_previous_text", True),
            temperature_increment_on_fallback=params.get("temperature_increment_on_fallback", 0.2),
            compression_ratio_threshold=params.get("compression_ratio_threshold", 2.4),
            logprob_threshold=params.get("logprob_threshold", -1.0),
            no_speech_threshold=params.get("no_speech_threshold", 0.6),
            word_timestamps=params.get("word_timestamps", False),
            vad_filter=vad_filter
        )
        
        # Process the segments
        result_segments = []
        for segment in segments:
            segment_dict = {
                "id": segment.id,
                "seek": segment.seek,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "tokens": segment.tokens,
                "temperature": segment.temperature,
                "avg_logprob": segment.avg_logprob,
                "compression_ratio": segment.compression_ratio,
                "no_speech_prob": segment.no_speech_prob
            }
            
            # Add word timestamps if available
            if hasattr(segment, "words") and segment.words:
                segment_dict["words"] = [
                    {
                        "start": word.start,
                        "end": word.end,
                        "word": word.word,
                        "probability": word.probability
                    }
                    for word in segment.words
                ]
            
            result_segments.append(segment_dict)
        
        # Format the transcription according to requested format
        transcription = self._format_output(result_segments, transcription_format)
        
        # Format translation if requested
        translation = None
        if params.get("task") == "translate" and translation_format:
            translation = self._format_output(result_segments, translation_format)
        
        return {
            "segments": result_segments,
            "detected_language": info.language,
            "transcription": transcription,
            "translation": translation,
            "device": self.device,
        }
    
    def _format_output(self, segments: List[Dict[str, Any]], format_type: str) -> str:
        """
        Format the output based on the requested format
        
        Args:
            segments: List of transcription segments
            format_type: Output format type
            
        Returns:
            Formatted output string
        """
        if format_type == "plain_text":
            return " ".join(segment["text"] for segment in segments)
        
        elif format_type == "formatted_text":
            return "\n".join(segment["text"] for segment in segments)
        
        elif format_type == "srt":
            srt_content = ""
            for i, segment in enumerate(segments, 1):
                start_time = self._format_timestamp(segment["start"], format="srt")
                end_time = self._format_timestamp(segment["end"], format="srt")
                srt_content += f"{i}\n{start_time} --> {end_time}\n{segment['text']}\n\n"
            return srt_content
        
        elif format_type == "vtt":
            vtt_content = "WEBVTT\n\n"
            for i, segment in enumerate(segments, 1):
                start_time = self._format_timestamp(segment["start"], format="vtt")
                end_time = self._format_timestamp(segment["end"], format="vtt")
                vtt_content += f"{i}\n{start_time} --> {end_time}\n{segment['text']}\n\n"
            return vtt_content
        
        else:
            return " ".join(segment["text"] for segment in segments)
    
    def _format_timestamp(self, seconds: float, format: str = "srt") -> str:
        """
        Format a timestamp in seconds to SRT or VTT format
        
        Args:
            seconds: Timestamp in seconds
            format: Output format (srt or vtt)
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds - int(seconds)) * 1000)
        
        if format == "srt":
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
        else:  # vtt
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}" 