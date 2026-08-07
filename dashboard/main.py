import asyncio
import os
import re
from pathlib import Path
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

LOG_FILE_PATH = os.getenv("LOG_FILE", "/app/logs/bot.log")

app = FastAPI(title="Meshtastic AI Bot Monitor")

# Directory setup
STATIC_DIR = Path(__file__).parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def get_dashboard():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse("<h1>Dashboard index.html not found</h1>", status_code=404)


def read_last_lines(file_path: str, max_lines: int = 400) -> List[str]:
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            return [line.strip() for line in lines[-max_lines:]]
    except Exception:
        return []


@app.get("/api/logs")
async def get_initial_logs():
    lines = read_last_lines(LOG_FILE_PATH, max_lines=400)
    return {"logs": lines}


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


async def tail_log_file():
    """Background task to continuously tail bot.log and broadcast new lines."""
    last_position = 0
    if os.path.exists(LOG_FILE_PATH):
        try:
            last_position = os.path.getsize(LOG_FILE_PATH)
        except Exception:
            last_position = 0

    while True:
        try:
            if os.path.exists(LOG_FILE_PATH):
                current_size = os.path.getsize(LOG_FILE_PATH)
                if current_size < last_position:
                    # Log file was rotated or reset
                    last_position = 0

                if current_size > last_position:
                    with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(last_position)
                        new_lines = f.readlines()
                        last_position = f.tell()
                        for line in new_lines:
                            line_str = line.strip()
                            if line_str:
                                await manager.broadcast(line_str)
        except Exception:
            pass

        await asyncio.sleep(0.5)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(tail_log_file())


@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Maintain WebSocket connection ping/pong
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
