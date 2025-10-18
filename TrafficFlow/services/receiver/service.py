from __future__ import annotations

import json
import time
from typing import Callable

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

from .config import ConfiguracionReceptor
from .logger import obtener_logger
from .processor import procesar_evento

logger = obtener_logger(__name__)


def _crear_productor(configuracion: ConfiguracionReceptor) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=configuracion.servidores_kafka,
        value_serializer=lambda valor: json.dumps(valor).encode("utf-8"),
        linger_ms=30,
        retries=5,
    )


def _crear_consumidor(configuracion: ConfiguracionReceptor) -> KafkaConsumer:
    return KafkaConsumer(
        configuracion.topico_entrada,
        bootstrap_servers=configuracion.servidores_kafka,
        group_id=configuracion.grupo_consumo,
        value_deserializer=lambda valor: json.loads(valor.decode("utf-8")),
        enable_auto_commit=False,
        auto_offset_reset="latest",
        max_poll_records=200,
        session_timeout_ms=30000,
        heartbeat_interval_ms=10000,
    )


class ServicioReceptor:
    """Gestiona la ingesta, procesamiento y redistribución de eventos."""

    def __init__(self, configuracion: ConfiguracionReceptor) -> None:
        self.configuracion = configuracion
        self._productor_factory: Callable[[], KafkaProducer] = lambda: _crear_productor(configuracion)
        self._productor_telemetria: KafkaProducer | None = None
        self._ultimo_latido: float = 0.0
        self._eventos_procesados: int = 0

    def _enviar_latido(self, estado: str) -> None:
        productor = self._productor_telemetria or self._productor_factory()
        self._productor_telemetria = productor
        payload = {
            "entity_type": "receptor",
            "entity_id": self.configuracion.receptor_id,
            "status": estado,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "metrics": {
                "eventos_procesados": self._eventos_procesados,
                "topico_entrada": self.configuracion.topico_entrada,
            },
        }
        try:
            productor.send(self.configuracion.topico_telemetria, value=payload)
            productor.flush(timeout=5)
        except KafkaError as error:
            logger.warning("No fue posible emitir el latido del receptor", exc_info=error)

    def ejecutar(self) -> None:
        consumidor = _crear_consumidor(self.configuracion)
        productor_detalle = self._productor_factory()
        productor_dashboard = self._productor_factory()
        self._enviar_latido("arrancando")

        logger.info(
            "Receptor %s asignado al tópico %s dentro del grupo %s",
            self.configuracion.receptor_id,
            self.configuracion.topico_entrada,
            self.configuracion.grupo_consumo,
        )

        mensajes_desde_commit = 0

        try:
            while True:
                try:
                    mensajes = consumidor.poll(timeout_ms=1000)
                except KafkaError:
                    logger.exception("Error al obtener mensajes; reintentando tras breve pausa")
                    time.sleep(5)
                    consumidor = _crear_consumidor(self.configuracion)
                    continue

                if not mensajes:
                    self._emitir_latido_si_corresponde()
                    continue

                error_reintento = False
                for registros in mensajes.values():
                    for registro in registros:
                        detalle, resumen = procesar_evento(registro.value, self.configuracion)
                        try:
                            productor_detalle.send(self.configuracion.topico_detalle, value=detalle)
                            productor_dashboard.send(self.configuracion.topico_dashboard, value=resumen)
                            self._eventos_procesados += 1
                        except KafkaError:
                            logger.exception(
                                "Fallo al reenviar evento procesado; el mensaje se reintentará"
                            )
                            time.sleep(2)
                            productor_detalle = self._productor_factory()
                            productor_dashboard = self._productor_factory()
                            error_reintento = True
                            break
                        mensajes_desde_commit += 1
                    if error_reintento:
                        break
                if error_reintento:
                    continue

                if mensajes_desde_commit >= self.configuracion.intervalo_commit:
                    try:
                        consumidor.commit()
                        mensajes_desde_commit = 0
                    except KafkaError:
                        logger.exception(
                            "No fue posible confirmar offsets; se intentará nuevamente"
                        )

                self._emitir_latido_si_corresponde()
        except KeyboardInterrupt:
            logger.info("Receptor detenido manualmente")
        finally:
            self._enviar_latido("detenido")
            try:
                consumidor.commit()
            except KafkaError:
                logger.warning("No fue posible confirmar offsets en la detención", exc_info=True)
            consumidor.close()
            for productor in {productor_detalle, productor_dashboard, self._productor_telemetria}:
                if productor:
                    try:
                        productor.flush(timeout=5)
                        productor.close()
                    except KafkaError:
                        logger.warning("Error al cerrar productor de Kafka", exc_info=True)

    def _emitir_latido_si_corresponde(self) -> None:
        ahora = time.time()
        if ahora - self._ultimo_latido >= self.configuracion.intervalo_latido_segundos:
            self._enviar_latido("activo")
            self._ultimo_latido = ahora
