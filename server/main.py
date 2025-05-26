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
    yield
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
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"🔌 Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"🔌 Client {client_id} disconnected")
    
    async def send_to_client(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"❌ Error sending to client {client_id}: {e}")
                self.disconnect(client_id)
    
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
                        logger.info(f"📝 Received text message: {json_message}")
                        
                        # Forward to RunPod function
                        runpod_payload = {
                            "input": {
                                "message": json_message,
                                "client_id": client_id,
                                "message_type": "text"
                            }
                        }
                        
                        result = await manager.call_runpod_function(runpod_payload)
                        
                        # Send result back to client
                        if "output" in result:
                            await manager.send_to_client(client_id, result["output"])
                        else:
                            await manager.send_to_client(client_id, {"error": "No output from RunPod function"})
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON: {e}")
                        await manager.send_to_client(client_id, {"error": "Invalid JSON format"})
                    except Exception as e:
                        logger.error(f"❌ Error processing text message: {e}")
                        await manager.send_to_client(client_id, {"error": str(e)})
                
                elif "bytes" in message:
                    # Handle binary audio data
                    audio_data = message["bytes"]
                    logger.debug(f"🎵 Received audio data: {len(audio_data)} bytes")
                    
                    # Forward audio to RunPod function
                    try:
                        import base64
                        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                        
                        runpod_payload = {
                            "input": {
                                "audio_data": audio_b64,
                                "client_id": client_id,
                                "message_type": "audio"
                            }
                        }
                        
                        result = await manager.call_runpod_function(runpod_payload)
                        
                        # Send result back to client
                        if "output" in result:
                            await manager.send_to_client(client_id, result["output"])
                            
                    except Exception as e:
                        logger.error(f"❌ Error processing audio: {e}")
                        await manager.send_to_client(client_id, {"error": str(e)})
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        manager.disconnect(client_id)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 