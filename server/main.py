import logging
import asyncio
import json
import os
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
BATCH_SAMPLES = 2048  # Match client's batch size
HEADER_BYTES = 8      # Match client's header size
FRAME_BYTES = BATCH_SAMPLES * 2  # 16-bit samples = 2 bytes per sample
MIN_BUFFER_SIZE = FRAME_BYTES + HEADER_BYTES  # Total expected message size

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
        # Audio buffering per client
        self.audio_buffers: Dict[str, bytearray] = {}
        self.client_states: Dict[str, dict] = {}
        self._flusher_task = None  # Will be set when the app starts
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        # Initialize client buffers and state
        self.audio_buffers[client_id] = bytearray()
        self.client_states[client_id] = {
            "is_recording": False,
            "tts_playing": False,
            "last_audio_time": 0
        }
        logger.info(f"🔌 Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        # Clean up client buffers and state
        if client_id in self.audio_buffers:
            del self.audio_buffers[client_id]
        if client_id in self.client_states:
            del self.client_states[client_id]
        logger.info(f"🔌 Client {client_id} disconnected")
    
    async def send_to_client(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"❌ Error sending to client {client_id}: {e}")
                self.disconnect(client_id)
    
    async def process_audio_chunk(self, client_id: str, audio_data: bytes):
        """Process fixed-size audio chunks with header information."""
        if client_id not in self.audio_buffers:
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
            
            # Extract audio samples
            audio_samples = audio_data[HEADER_BYTES:]
            
            # Send to RunPod immediately since we have a complete batch
            try:
                import base64
                audio_b64 = base64.b64encode(audio_samples).decode('utf-8')
                
                runpod_payload = {
                    "input": {
                        "audio_data": audio_b64,
                        "client_id": client_id,
                        "message_type": "audio_batch",
                        "audio_length": len(audio_samples),
                        "tts_playing": is_tts_playing,
                        "timestamp": timestamp
                    }
                }
                
                logger.info(f"🎵 Processing audio batch: {len(audio_samples)} bytes, TTS playing: {is_tts_playing}")
                result = await self.call_runpod_function(runpod_payload)
                
                # Send result back to client
                if "output" in result:
                    await self.send_to_client(client_id, result["output"])
                    
            except Exception as e:
                logger.error(f"❌ Error processing audio batch: {e}")
                await self.send_to_client(client_id, {"error": str(e)})
                
        except Exception as e:
            logger.error(f"❌ Error parsing audio chunk: {e}")
            await self.send_to_client(client_id, {"error": str(e)})
    
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
            # Clear any buffered audio too
            if client_id in self.audio_buffers:
                self.audio_buffers[client_id].clear()
                
        elif message_type == "set_speed":
            speed = message.get("speed", 1)
            logger.info(f"⚡ Client {client_id} set speed to {speed}")
            
        # Forward control messages to RunPod
        try:
            runpod_payload = {
                "input": {
                    "message": message,
                    "client_id": client_id,
                    "message_type": "control"
                }
            }
            
            result = await self.call_runpod_function(runpod_payload)
            
            # Send result back to client
            if "output" in result:
                await self.send_to_client(client_id, result["output"])
                
        except Exception as e:
            logger.error(f"❌ Error processing control message: {e}")
            await self.send_to_client(client_id, {"error": str(e)})

    async def cleanup(self):
        """Clean up resources."""
        if self._flusher_task:
            self._flusher_task.cancel()
            try:
                await self._flusher_task
            except asyncio.CancelledError:
                pass
        await self.http_client.aclose()

    async def _audio_buffer_flusher(self):
        """Background task to flush audio buffers after timeout."""
        while True:
            try:
                await asyncio.sleep(2)  # Check every 2 seconds
                current_time = __import__('time').time()
                
                for client_id in list(self.client_states.keys()):
                    if client_id not in self.audio_buffers:
                        continue
                        
                    last_audio_time = self.client_states[client_id].get("last_audio_time", 0)
                    buffer_size = len(self.audio_buffers[client_id])
                    
                    # If buffer has data and hasn't received audio for 3 seconds, flush it
                    if buffer_size > 0 and (current_time - last_audio_time) > 3.0:
                        logger.info(f"⏰ Flushing audio buffer for {client_id} after timeout: {buffer_size} bytes")
                        
                        buffered_audio = bytes(self.audio_buffers[client_id])
                        self.audio_buffers[client_id].clear()
                        
                        try:
                            import base64
                            audio_b64 = base64.b64encode(buffered_audio).decode('utf-8')
                            
                            runpod_payload = {
                                "input": {
                                    "audio_data": audio_b64,
                                    "client_id": client_id,
                                    "message_type": "audio_batch_timeout",
                                    "audio_length": len(buffered_audio),
                                    "tts_playing": self.client_states[client_id].get("tts_playing", False)
                                }
                            }
                            
                            result = await self.call_runpod_function(runpod_payload)
                            
                            if "output" in result:
                                await self.send_to_client(client_id, result["output"])
                                
                        except Exception as e:
                            logger.error(f"❌ Error flushing audio buffer: {e}")
                            
            except Exception as e:
                logger.error(f"❌ Error in audio buffer flusher: {e}")

    async def call_runpod_function(self, payload: dict) -> dict:
        """Call the RunPod serverless function."""
        if not RUNPOD_ENDPOINT or not RUNPOD_API_KEY:
            raise HTTPException(status_code=500, detail="RunPod not configured")
        
        headers = {
            "Authorization": f"Bearer {RUNPOD_API_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.http_client.post(
                RUNPOD_ENDPOINT,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"❌ RunPod request error: {e}")
            raise HTTPException(status_code=500, detail=f"RunPod request failed: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ RunPod HTTP error: {e}")
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