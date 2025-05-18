import os
from typing import Dict, List, Any, Optional
import torch
import whisper
from faster_whisper import WhisperModel

class WhisperTranscriber:
    def __init__(self, model="base.en"):
        """
        Initialize the WhisperTranscriber
        
        Args:
            model: The name of the Whisper model to use
        """
        # Get GPU device from environment (useful for multi-GPU setups)
        device_id = os.environ.get("CUDA_VISIBLE_DEVICES", "0")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "float32"
        
        # Get model path from environment variable or use default cache
        model_path = os.environ.get("MODEL_PATH", None)
        if model_path:
            print(f"Using custom model path: {model_path}")
            # If using custom path, ensure it exists
            os.makedirs(model_path, exist_ok=True)
            os.environ["WHISPER_CACHE"] = model_path
        
        print(f"Loading model {model} on {self.device} (device {device_id})...")
        self.model = WhisperModel(model, device=self.device, compute_type=self.compute_type, download_root=model_path)
        print("Model loaded successfully")
    
    def transcribe(
        self, 
        audio_path: str, 
        params: Dict[str, Any] = {},
        transcription_format: str = "plain_text",
        translation_format: Optional[str] = None,
        vad_filter: bool = False,
        incremental: bool = False
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper
        
        Args:
            audio_path: Path to the audio file
            params: Parameters for the Whisper model
            transcription_format: Output format for transcription
            translation_format: Output format for translation
            vad_filter: Whether to use VAD filtering
            incremental: Whether to return results incrementally during processing
            
        Returns:
            Dict containing transcription results
        """
        # Set callback for incremental results if requested
        incremental_callback = None
        if incremental:
            previous_text = ""
            
            def callback(segment):
                nonlocal previous_text
                # Get new text from this segment
                new_text = segment.text
                if new_text != previous_text:
                    # Update previous text
                    previous_text = new_text
                    # Return the segment for the caller to use
                    return segment
                return None
                
            incremental_callback = callback
            
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
            vad_filter=vad_filter,
            callback=incremental_callback if incremental else None
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