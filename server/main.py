import logging
import asyncio
import json
import os
import time
from typing import Dict, Any
from contextlib import asynccontextmanager

import uvicorn
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import HTMLResponse, FileResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RunPod configuration
RUNPOD_ENDPOINT = os.getenv("RUNPOD_ENDPOINT", "")
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")

# Audio processing configuration
BATCH_SAMPLES = 2400   # 100ms at 24kHz (matches client, ultra-low latency)
HEADER_BYTES = 8      # Match client's header size
FRAME_BYTES = BATCH_SAMPLES * 2  # 16-bit samples = 2 bytes per sample
MIN_BUFFER_SIZE = FRAME_BYTES + HEADER_BYTES  # Total expected message size: 4808 bytes

if not RUNPOD_ENDPOINT or not RUNPOD_API_KEY:
    logger.warning("⚠️ RunPod endpoint or API key not configured. Set RUNPOD_ENDPOINT and RUNPOD_API_KEY environment variables.")

class NoCacheStaticFiles(StaticFiles):
    """Serves static files without allowing client-side caching."""
    async def get_response(self, path: str, scope: Dict[str, Any]):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        if "etag" in response.headers:
            response.headers.__delitem__("etag")
        if "last-modified" in response.headers:
            response.headers.__delitem__("last-modified")
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application's lifespan."""
    logger.info("🚀 Railway server starting up")
    
    # Start the audio buffer flusher task
    manager._flusher_task = asyncio.create_task(manager._audio_buffer_flusher())
    logger.info("🧹 Started audio buffer flusher task")
    
    yield
    
    # Clean up on shutdown
    await manager.cleanup()
    logger.info("⏹️ Railway server shutting down")

# FastAPI app instance
app = FastAPI(lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", NoCacheStaticFiles(directory="static"), name="static")

@app.get("/favicon.ico")
async def favicon():
    """Serves the favicon.ico file."""
    return FileResponse("static/favicon.ico")

@app.get("/")
async def get_index() -> HTMLResponse:
    """Serves the main index.html page."""
    with open("static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    return {"status": "healthy", "service": "realtime-voice-chat-server"}

class ConnectionManager:
    """Manages WebSocket connections and RunPod communication."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.http_client = httpx.AsyncClient(timeout=30.0)
        # Client state tracking
        self.client_states: Dict[str, dict] = {}
        # Audio buffering for session management
        self.audio_buffers: Dict[str, bytearray] = {}
        self.last_request_time: Dict[str, float] = {}
        self.min_request_interval = 2.0  # Minimum 2 seconds between RunPod requests
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        # Initialize client state
        self.client_states[client_id] = {
            "is_recording": False,
            "tts_playing": False,
            "last_audio_time": 0
        }
        self.audio_buffers[client_id] = bytearray()
        self.last_request_time[client_id] = 0
        logger.info(f"🔌 Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        # Clean up client state
        if client_id in self.client_states:
            del self.client_states[client_id]
        if client_id in self.audio_buffers:
            del self.audio_buffers[client_id]
        if client_id in self.last_request_time:
            del self.last_request_time[client_id]
        logger.info(f"🔌 Client {client_id} disconnected")
    
    async def send_to_client(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"❌ Error sending to client {client_id}: {e}")
                self.disconnect(client_id)
        else:
            logger.debug(f"🔇 Attempted to send to disconnected client: {client_id}")
    
    async def process_audio_chunk(self, client_id: str, audio_data: bytes):
        """Process audio chunks with intelligent buffering and throttling."""
        # Check if client is still connected
        if client_id not in self.active_connections:
            logger.warning(f"⚠️ Received audio for disconnected client: {client_id}")
            return
            
        # Verify chunk size
        if len(audio_data) != MIN_BUFFER_SIZE:
            logger.warning(f"⚠️ Received unexpected audio chunk size: {len(audio_data)} bytes")
            return
            
        try:
            # Extract header information (timestamp and flags)
            import struct
            timestamp, flags = struct.unpack('>II', audio_data[:HEADER_BYTES])
            is_tts_playing = bool(flags & 1)
            
            # Update client state
            self.client_states[client_id]["tts_playing"] = is_tts_playing
            self.client_states[client_id]["last_audio_time"] = timestamp
            
            # Extract audio samples and add to buffer
            audio_samples = audio_data[HEADER_BYTES:]
            self.audio_buffers[client_id].extend(audio_samples)
            
            current_time = time.time()
            last_request = self.last_request_time[client_id]
            time_since_last = current_time - last_request
            buffer_size = len(self.audio_buffers[client_id])
            
            # Decide whether to send to RunPod based on:
            # 1. Minimum time interval (2 seconds)
            # 2. Buffer size (at least 2 seconds of audio = 96000 bytes)
            # 3. TTS not playing (don't interrupt)
            min_buffer_size = 96000  # 2 seconds at 24kHz, 16-bit
            should_send = (
                time_since_last >= self.min_request_interval and
                buffer_size >= min_buffer_size and
                not is_tts_playing
            )
            
            if should_send:
                # Send accumulated audio to RunPod
                buffered_audio = bytes(self.audio_buffers[client_id])
                self.audio_buffers[client_id].clear()
                self.last_request_time[client_id] = current_time
                
                try:
                    import base64
                    audio_b64 = base64.b64encode(buffered_audio).decode('utf-8')
                    
                    runpod_payload = {
                        "input": {
                            "audio_data": audio_b64,
                            "client_id": client_id,
                            "message_type": "audio_batch",
                            "audio_length": len(buffered_audio),
                            "tts_playing": is_tts_playing,
                            "timestamp": timestamp
                        }
                    }
                    
                    logger.info(f"🎵 Sending {len(buffered_audio)} bytes to RunPod (buffered from {buffer_size} bytes)")
                    # Use streaming call - this will handle sending chunks to client
                    await self.call_runpod_function(runpod_payload)
                        
                except Exception as e:
                    logger.error(f"❌ Error processing audio batch: {e}")
                    if client_id in self.active_connections:
                        await self.send_to_client(client_id, {"type": "error", "message": str(e)})
            else:
                logger.debug(f"🔄 Buffering audio: {buffer_size} bytes, time since last: {time_since_last:.1f}s")
                
        except Exception as e:
            logger.error(f"❌ Error parsing audio chunk: {e}")
            if client_id in self.active_connections:
                await self.send_to_client(client_id, {"type": "error", "message": str(e)})
    
    async def handle_control_message(self, client_id: str, message: dict):
        """Handle control messages like tts_start, tts_stop, etc."""
        message_type = message.get("type", "")
        
        if message_type == "tts_start":
            self.client_states[client_id]["tts_playing"] = True
            logger.info(f"🔊 Client {client_id} started TTS playback")
            
        elif message_type == "tts_stop":
            self.client_states[client_id]["tts_playing"] = False
            logger.info(f"🔇 Client {client_id} stopped TTS playback")
            
        elif message_type == "clear_history":
            logger.info(f"🗑️ Client {client_id} cleared chat history")
            
        elif message_type == "set_speed":
            speed = message.get("speed", 1)
            logger.info(f"⚡ Client {client_id} set speed to {speed}")
            
        # Forward control messages to RunPod with streaming
        try:
            runpod_payload = {
                "input": {
                    "message": message,
                    "client_id": client_id,
                    "message_type": "control"
                }
            }
            
            # Use streaming call
            await self.call_runpod_function(runpod_payload)
                
        except Exception as e:
            logger.error(f"❌ Error processing control message: {e}")
            await self.send_to_client(client_id, {"type": "error", "message": str(e)})

    async def cleanup(self):
        """Clean up resources."""
        # Cancel the flusher task if it exists
        if hasattr(self, '_flusher_task'):
            self._flusher_task.cancel()
            try:
                await self._flusher_task
            except asyncio.CancelledError:
                pass
        await self.http_client.aclose()

    async def _audio_buffer_flusher(self):
        """Background task to flush old audio buffers."""
        while True:
            try:
                await asyncio.sleep(5.0)  # Check every 5 seconds
                current_time = time.time()
                
                for client_id in list(self.audio_buffers.keys()):
                    if client_id not in self.active_connections:
                        continue
                        
                    last_request = self.last_request_time.get(client_id, 0)
                    buffer_size = len(self.audio_buffers[client_id])
                    time_since_last = current_time - last_request
                    
                    # Flush if buffer has audio and it's been too long
                    if buffer_size > 0 and time_since_last >= 10.0:  # 10 seconds max wait
                        logger.info(f"🧹 Flushing stale audio buffer for {client_id}: {buffer_size} bytes")
                        
                        buffered_audio = bytes(self.audio_buffers[client_id])
                        self.audio_buffers[client_id].clear()
                        self.last_request_time[client_id] = current_time
                        
                        try:
                            import base64
                            audio_b64 = base64.b64encode(buffered_audio).decode('utf-8')
                            
                            runpod_payload = {
                                "input": {
                                    "audio_data": audio_b64,
                                    "client_id": client_id,
                                    "message_type": "audio_batch",
                                    "audio_length": len(buffered_audio),
                                    "tts_playing": False,
                                    "timestamp": int(current_time * 1000)
                                }
                            }
                            
                            await self.call_runpod_function(runpod_payload)
                            
                        except Exception as e:
                            logger.error(f"❌ Error flushing audio buffer: {e}")
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in audio buffer flusher: {e}")

    async def call_runpod_function(self, payload: dict) -> dict:
        """Call the RunPod serverless function with streaming support."""
        if not RUNPOD_ENDPOINT or not RUNPOD_API_KEY:
            raise HTTPException(status_code=500, detail="RunPod not configured")
        
        # RUNPOD_ENDPOINT is just the endpoint ID
        endpoint_id = RUNPOD_ENDPOINT
        base_url = 'https://api.runpod.ai/v2'
        
        headers = {
            "Authorization": f"Bearer {RUNPOD_API_KEY}",
            "Content-Type": "application/json"
        }
        
        client_id = payload.get("input", {}).get("client_id")
        
        try:
            # Step 1: Start the async job (reduced timeout)
            response = await self.http_client.post(
                f"{base_url}/{endpoint_id}/run",
                json=payload,
                headers=headers,
                timeout=3.0  # Reduced from 5.0s to 3.0s
            )
            response.raise_for_status()
            job_data = response.json()
            job_id = job_data.get('id')
            
            if not job_id:
                raise ValueError("No job ID returned from RunPod")
            
            logger.info(f"🚀 Started streaming job: {job_id}")
            
            # Step 2: Stream results with optimized timeout
            stream_response = await self.http_client.get(
                f"{base_url}/{endpoint_id}/stream/{job_id}",
                headers=headers,
                timeout=15.0  # Reduced from 30.0s to 15.0s
            )
            stream_response.raise_for_status()
            
            # Parse the streaming response
            stream_data = stream_response.json()
            
            # Send each chunk to the client as it arrives
            if isinstance(stream_data, list):
                for chunk in stream_data:
                    if "output" in chunk:
                        await self.send_to_client(client_id, {
                            "type": "stream_chunk",
                            "data": chunk["output"]
                        })
            
            # Send completion message
            await self.send_to_client(client_id, {
                "type": "stream_complete",
                "job_id": job_id
            })
            
            return {
                "type": "streaming_complete",
                "job_id": job_id,
                "status": "success"
            }
            
        except httpx.TimeoutException:
            logger.error("❌ RunPod request timed out")
            await self.send_to_client(client_id, {
                "type": "error",
                "message": "Request timed out"
            })
            raise HTTPException(status_code=504, detail="RunPod request timed out")
        except httpx.RequestError as e:
            logger.error(f"❌ RunPod request error: {e}")
            await self.send_to_client(client_id, {
                "type": "error", 
                "message": f"Request failed: {str(e)}"
            })
            raise HTTPException(status_code=500, detail=f"RunPod request failed: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ RunPod HTTP error: {e}")
            await self.send_to_client(client_id, {
                "type": "error",
                "message": f"HTTP error: {str(e)}"
            })
            raise HTTPException(status_code=500, detail=f"RunPod HTTP error: {str(e)}")

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice chat."""
    client_id = f"client_{id(websocket)}"
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message from client (can be text or binary)
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "text" in message:
                    # Handle JSON text messages (control messages)
                    try:
                        json_message = json.loads(message["text"])
                        logger.info(f"📝 Received control message: {json_message}")
                        
                        # Process control message through the new handler
                        await manager.handle_control_message(client_id, json_message)
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON: {e}")
                        await manager.send_to_client(client_id, {"error": "Invalid JSON format"})
                    except Exception as e:
                        logger.error(f"❌ Error processing control message: {e}")
                        await manager.send_to_client(client_id, {"error": str(e)})
                
                elif "bytes" in message:
                    # Handle binary audio data - buffer it instead of immediately sending
                    audio_data = message["bytes"]
                    logger.debug(f"🎵 Buffering audio chunk: {len(audio_data)} bytes")
                    
                    # Process audio through the new buffering system
                    try:
                        await manager.process_audio_chunk(client_id, audio_data)
                    except Exception as e:
                        logger.error(f"❌ Error processing audio chunk: {e}")
                        await manager.send_to_client(client_id, {"error": str(e)})
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        manager.disconnect(client_id)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 