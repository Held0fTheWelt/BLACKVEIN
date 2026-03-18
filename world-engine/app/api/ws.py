from __future__ import annotations

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from app.auth.tickets import TicketError

router = APIRouter(tags=["ws"])


@router.websocket("/ws")
async def runtime_socket(websocket: WebSocket) -> None:
    app = websocket.app
    ticket = websocket.query_params.get("ticket")
    if not ticket:
        await websocket.close(code=4401, reason="Missing ticket")
        return
    try:
        payload = app.state.ticket_manager.verify(ticket)
    except TicketError:
        await websocket.close(code=4403, reason="Invalid ticket")
        return

    run_id = payload["run_id"]
    participant_id = payload["participant_id"]
    manager = app.state.manager
    await manager.connect(run_id, participant_id, websocket)
    try:
        while True:
            message = await websocket.receive_json()
            await manager.process_command(run_id, participant_id, message)
    except WebSocketDisconnect:
        await manager.disconnect(run_id, participant_id)
