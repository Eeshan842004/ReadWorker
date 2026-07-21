from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, doc_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active.setdefault(doc_id, []).append(ws)

    def disconnect(self, doc_id: str, ws: WebSocket) -> None:
        conns = self.active.get(doc_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns and doc_id in self.active:
            del self.active[doc_id]

    async def broadcast(self, doc_id: str, message: dict) -> None:
        for ws in list(self.active.get(doc_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(doc_id, ws)


connection_manager = ConnectionManager()


@router.websocket("/ws/ingest/{doc_id}")
async def ingest_ws(websocket: WebSocket, doc_id: str):
    await connection_manager.connect(doc_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(doc_id, websocket)
