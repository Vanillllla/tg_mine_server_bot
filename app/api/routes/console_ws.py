import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.server import ConsoleCommandRequest

router = APIRouter(tags=["console"])


@router.websocket("/ws/servers/active/console")
async def active_console(websocket: WebSocket) -> None:
    await websocket.accept()
    log_buffer = websocket.app.state.log_buffer
    manager = websocket.app.state.minecraft_manager
    queue = log_buffer.subscribe()

    for item in log_buffer.recent(limit=300):
        await websocket.send_json(item)

    try:
        while True:
            receive_task = asyncio.create_task(websocket.receive_json())
            log_task = asyncio.create_task(queue.get())
            done, pending = await asyncio.wait(
                {receive_task, log_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

            if log_task in done:
                await websocket.send_json(log_task.result())

            if receive_task in done:
                message = receive_task.result()
                if message.get("type") == "command":
                    payload = ConsoleCommandRequest(command=str(message.get("command", "")))
                    try:
                        await manager.send_stdin_command(payload.command)
                    except RuntimeError as exc:
                        await websocket.send_json(
                            {"type": "error", "code": "command_rejected", "message": str(exc)}
                        )
    except WebSocketDisconnect:
        pass
    finally:
        log_buffer.unsubscribe(queue)
