from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from collections import deque
from typing import Any, Deque, Dict, Set

from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("dashboard")
logging.basicConfig(level=os.getenv("NIVEL_REGISTROS", "INFO").upper())

app = FastAPI(title="Tablero trafico tiempo real")
app.mount("/static", StaticFiles(directory="/app/static"), name="static")


class ConnectionManager:
    """Gestiona conexiones WebSocket y caché corta de eventos."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._cache: Deque[Dict[str, Any]] = deque(maxlen=200)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        for evento in list(self._cache):
            try:
                await websocket.send_text(json.dumps(evento))
            except WebSocketDisconnect:
                self.disconnect(websocket)
                break

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, mensaje: Dict[str, Any]) -> None:
        self._cache.append(mensaje)
        texto = json.dumps(mensaje)
        desconectados: Set[WebSocket] = set()
        for websocket in self._connections:
            try:
                await websocket.send_text(texto)
            except WebSocketDisconnect:
                desconectados.add(websocket)
        for websocket in desconectados:
            self.disconnect(websocket)


manager = ConnectionManager()


async def _crear_consumidor() -> AIOKafkaConsumer:
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    topico = os.getenv("KAFKA_TOPIC_DASHBOARD", "trafico.dashboard")
    grupo = os.getenv("KAFKA_GROUP_DASHBOARD", "dashboard-service")
    consumidor = AIOKafkaConsumer(
        topico,
        bootstrap_servers=bootstrap,
        group_id=grupo,
        enable_auto_commit=True,
        value_deserializer=lambda valor: json.loads(valor.decode("utf-8")),
        auto_offset_reset="latest",
    )
    await consumidor.start()
    logger.info("Consumiendo datos para tablero desde %s", topico)
    return consumidor


async def _loop_consumidor(consumidor: AIOKafkaConsumer) -> None:
    try:
        async for mensaje in consumidor:
            payload = mensaje.value
            payload["partition"] = mensaje.partition
            payload["offset"] = mensaje.offset
            await manager.broadcast(payload)
    except Exception:  # noqa: BLE001
        logger.exception("Fallo en el bucle del consumidor del tablero")
        await asyncio.sleep(5)
        nuevo = await _crear_consumidor()
        app.state.consumer_task = asyncio.create_task(_loop_consumidor(nuevo))
    finally:
        await consumidor.stop()


@app.on_event("startup")
async def iniciar() -> None:
    consumidor = await _crear_consumidor()
    app.state.consumer_task = asyncio.create_task(_loop_consumidor(consumidor))


@app.on_event("shutdown")
async def detener() -> None:
    task: asyncio.Task | None = getattr(app.state, "consumer_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(Exception):
            await task


@app.get("/")
async def pagina_principal() -> HTMLResponse:
    with open("/app/static/index.html", "r", encoding="utf-8") as pagina:
        return HTMLResponse(pagina.read())


@app.websocket("/stream")
async def flujo_eventos(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            # Mantener la conexión abierta; no recibimos mensajes del cliente.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PUERTO", "8090")), reload=False)
