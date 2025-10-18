from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict

from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=os.getenv("NIVEL_REGISTROS", "INFO").upper())
logger = logging.getLogger("control-center")

app = FastAPI(title="Centro de Control Trafico")
app.mount("/static", StaticFiles(directory="/app/static"), name="static")


@dataclass
class EstadoEntidad:
    entity_type: str
    entity_id: str
    status: str
    timestamp: str
    metrics: Dict[str, Any]
    last_seen: float

    def as_dict(self) -> Dict[str, Any]:
        datos = asdict(self)
        datos["last_seen_iso"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.last_seen))
        return datos


class ConnectionManager:
    def __init__(self) -> None:
        self._clientes: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clientes.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._clientes.discard(websocket)

    async def broadcast(self, mensaje: Dict[str, Any]) -> None:
        texto = json.dumps(mensaje)
        desconectados: set[WebSocket] = set()
        for cliente in self._clientes:
            try:
                await cliente.send_text(texto)
            except WebSocketDisconnect:
                desconectados.add(cliente)
        for cliente in desconectados:
            self.disconnect(cliente)


manager = ConnectionManager()
estados: Dict[str, EstadoEntidad] = {}


async def _crear_consumidor() -> AIOKafkaConsumer:
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    topico = os.getenv("KAFKA_TOPICO_TELEMETRIA", "trafico.telemetria")
    grupo = os.getenv("KAFKA_GRUPO_TELEMETRIA", "control-center")
    consumidor = AIOKafkaConsumer(
        topico,
        bootstrap_servers=bootstrap,
        group_id=grupo,
        enable_auto_commit=True,
        value_deserializer=lambda valor: json.loads(valor.decode("utf-8")),
        auto_offset_reset="latest",
    )
    await consumidor.start()
    logger.info("Centro de control escuchando telemetría en %s", topico)
    return consumidor


async def _procesar_actualizacion(evento: Dict[str, Any]) -> None:
    clave = f"{evento.get('entity_type')}::{evento.get('entity_id')}"
    estados[clave] = EstadoEntidad(
        entity_type=evento.get("entity_type", "desconocido"),
        entity_id=evento.get("entity_id", "-"),
        status=evento.get("status", "desconocido"),
        timestamp=evento.get("timestamp", ""),
        metrics=evento.get("metrics", {}),
        last_seen=time.time(),
    )
    await manager.broadcast({"type": "update", "payload": estados[clave].as_dict()})


async def _loop_consumidor(consumidor: AIOKafkaConsumer) -> None:
    try:
        async for mensaje in consumidor:
            await _procesar_actualizacion(mensaje.value)
    except Exception:  # noqa: BLE001
        logger.exception("Error escuchando telemetría, se recreará el consumidor")
        await asyncio.sleep(5)
        nuevo = await _crear_consumidor()
        app.state.consumer_task = asyncio.create_task(_loop_consumidor(nuevo))
    finally:
        await consumidor.stop()


async def _depurar_estados() -> None:
    while True:
        await asyncio.sleep(10)
        ahora = time.time()
        expirados = [clave for clave, estado in estados.items() if ahora - estado.last_seen > 60]
        for clave in expirados:
            estado = estados.pop(clave)
            await manager.broadcast({"type": "expired", "payload": estado.as_dict()})


@app.on_event("startup")
async def iniciar() -> None:
    consumidor = await _crear_consumidor()
    app.state.consumer_task = asyncio.create_task(_loop_consumidor(consumidor))
    app.state.cleaner_task = asyncio.create_task(_depurar_estados())


@app.on_event("shutdown")
async def detener() -> None:
    for atributo in ("consumer_task", "cleaner_task"):
        task: asyncio.Task | None = getattr(app.state, atributo, None)
        if task:
            task.cancel()
            with contextlib.suppress(Exception):
                await task


@app.get("/")
async def pagina_principal() -> HTMLResponse:
    with open("/app/static/index.html", "r", encoding="utf-8") as pagina:
        return HTMLResponse(pagina.read())


@app.get("/health")
async def healthcheck() -> JSONResponse:
    return JSONResponse({"status": "ok", "componentes_monitoreados": len(estados)})


@app.get("/estado")
async def obtener_estado() -> JSONResponse:
    datos = [estado.as_dict() for estado in estados.values()]
    datos.sort(key=lambda item: item["entity_type"])
    return JSONResponse({"items": datos})


@app.websocket("/telemetria")
async def telemetria(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        snapshot = [estado.as_dict() for estado in estados.values()]
        await websocket.send_text(json.dumps({"type": "snapshot", "payload": snapshot}))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PUERTO", "8091")), reload=False)
