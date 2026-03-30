from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.dependencies import market_service, state_store

router = APIRouter(tags=["market-stream"])


@router.websocket("/markets")
async def markets_ws(websocket: WebSocket) -> None:
    await state_store.connect(websocket)
    try:
        snapshot = await market_service.get_snapshot()
        await websocket.send_json(snapshot.model_dump(mode="json"))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state_store.disconnect(websocket)
