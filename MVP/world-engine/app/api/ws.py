from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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
    try:
        participant = manager.get_instance(run_id).participants[participant_id]
    except KeyError:
        await websocket.close(code=4404, reason="Run or participant not found")
        return

    if payload.get("account_id") and participant.account_id and payload.get("account_id") != participant.account_id:
        await websocket.close(code=4403, reason="Ticket identity mismatch")
        return
    if payload.get("character_id") and participant.character_id and payload.get("character_id") != participant.character_id:
        await websocket.close(code=4403, reason="Ticket character mismatch")
        return
    if payload.get("role_id") and payload.get("role_id") != participant.role_id:
        await websocket.close(code=4403, reason="Ticket role mismatch")
        return

    await manager.connect(run_id, participant_id, websocket)
    try:
        while True:
            message = await websocket.receive_json()
            await manager.process_command(run_id, participant_id, message)
    except WebSocketDisconnect:
        await manager.disconnect(run_id, participant_id)
