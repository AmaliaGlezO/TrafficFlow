from __future__ import annotations

import itertools
import time
from typing import Iterable

from kafka.errors import KafkaError

from .config import Configuracion
from .logger import obtener_logger
from .producer import construir_productor, enviar_eventos, enviar_latido
from .synthesizer import GeneradorEventosTrafico

logger = obtener_logger(__name__)


class ServicioGenerador:
    """Gestiona el bucle continuo de generación y publicación de eventos."""

    def __init__(self, configuracion: Configuracion, sintetizador: GeneradorEventosTrafico) -> None:
        self.configuracion = configuracion
        self.sintetizador = sintetizador
        self._eventos_por_segundo = max(1, int(configuracion.eventos_por_minuto / 60))
        self._fabrica_productores = lambda: construir_productor(configuracion)

    def _flujo_eventos(self) -> Iterable[dict[str, object]]:
        while True:
            yield self.sintetizador.generar()

    def ejecutar(self) -> None:
        logger.info(
            "Iniciando generador con %s eventos/minuto sobre el tópico %s",
            self.configuracion.eventos_por_minuto,
            self.configuracion.topico_kafka,
        )

        flujo_eventos = self._flujo_eventos()
        tamano_lote = max(1, min(self.configuracion.tamano_lote, self._eventos_por_segundo * 2))
        segundos_por_lote = tamano_lote / max(1, self.configuracion.eventos_por_minuto / 60)
        productor_eventos = self._fabrica_productores()
        productor_telemetria = self._fabrica_productores()
        eventos_publicados = 0
        ultimo_latido = 0.0

        enviar_latido(lambda: productor_telemetria, self.configuracion, "arrancando", eventos_publicados)

        while True:
            lote = list(itertools.islice(flujo_eventos, tamano_lote))
            inicio = time.perf_counter()
            try:
                enviar_eventos(lambda: productor_eventos, lote, self.configuracion)
                eventos_publicados += len(lote)
            except KafkaError:
                if self.configuracion.habilitar_respaldo_stdout:
                    for evento in lote:
                        logger.info("%s", evento)
                else:
                    logger.exception("Error de Kafka al publicar lote; reintento tras espera")
                    time.sleep(5)
                    productor_eventos = self._fabrica_productores()
                    productor_telemetria = self._fabrica_productores()
                    continue
            duracion = time.perf_counter() - inicio
            pausa = max(0.0, segundos_por_lote - duracion)
            time.sleep(pausa)

            ahora = time.perf_counter()
            if ahora - ultimo_latido >= self.configuracion.intervalo_latido_segundos:
                enviar_latido(
                    lambda: productor_telemetria,
                    self.configuracion,
                    "activo",
                    eventos_publicados,
                )
                ultimo_latido = ahora
