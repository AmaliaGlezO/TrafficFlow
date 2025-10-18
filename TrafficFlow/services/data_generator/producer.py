from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable

from kafka import KafkaProducer
from kafka.errors import KafkaError

from .config import Configuracion
from .logger import obtener_logger

logger = obtener_logger(__name__)


def construir_productor(configuracion: Configuracion) -> KafkaProducer:
    """Inicializa un productor Kafka configurado para JSON."""

    return KafkaProducer(
        bootstrap_servers=configuracion.servidores_kafka,
        value_serializer=lambda valor: json.dumps(valor).encode("utf-8"),
        linger_ms=configuracion.productor_linger_ms,
        batch_size=configuracion.productor_batch_bytes,
        retries=5,
    )


def enviar_eventos(
    fabrica_productores: Callable[[], KafkaProducer],
    eventos: Iterable[Dict[str, object]],
    configuracion: Configuracion,
) -> None:
    """Envía un lote de eventos al tópico configurado."""

    productor = fabrica_productores()
    for evento in eventos:
        evento.setdefault("sensor_id", configuracion.identificador_sensor)
        try:
            futuro = productor.send(configuracion.topico_kafka, value=evento)
            futuro.get(timeout=10)
        except KafkaError as error:
            logger.error("No fue posible publicar un evento", exc_info=error)
            raise
    productor.flush(timeout=10)


def enviar_latido(
    fabrica_productores: Callable[[], KafkaProducer],
    configuracion: Configuracion,
    estado: str,
    eventos_publicados: int,
) -> None:
    """Emite un mensaje de telemetría para el panel de control."""

    payload = {
        "entity_type": "generador",
        "entity_id": configuracion.identificador_sensor,
        "status": estado,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "eventos_por_minuto": configuracion.eventos_por_minuto,
            "tamano_lote": configuracion.tamano_lote,
            "eventos_publicados": eventos_publicados,
        },
    }

    productor = fabrica_productores()
    try:
        productor.send(configuracion.topico_telemetria, value=payload)
        productor.flush(timeout=5)
    except KafkaError as error:
        logger.warning("No fue posible enviar el latido de telemetría", exc_info=error)
