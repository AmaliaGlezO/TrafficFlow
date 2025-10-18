from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfiguracionReceptor:
    """Parámetros de configuración para los receptores de eventos."""

    servidores_kafka: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    topico_entrada: str = os.getenv("KAFKA_TOPIC_ENTRADA", "trafico.eventos")
    topico_detalle: str = os.getenv("KAFKA_TOPIC_DETALLE", "trafico.detalle")
    topico_dashboard: str = os.getenv("KAFKA_TOPIC_DASHBOARD", "trafico.dashboard")
    topico_telemetria: str = os.getenv("KAFKA_TOPICO_TELEMETRIA", "trafico.telemetria")
    grupo_consumo: str = os.getenv("KAFKA_GRUPO_CONSUMO", "trafico.receptores")
    receptor_id: str = os.getenv("RECEPTOR_ID", "receptor")
    tamano_lote_envio: int = int(os.getenv("TAMANO_LOTE_SALIDA", "50"))
    intervalo_commit: int = int(os.getenv("INTERVALO_COMMIT", "100"))
    intervalo_latido_segundos: int = int(os.getenv("INTERVALO_LATIDO_SEGUNDOS", "20"))


def obtener_configuracion() -> ConfiguracionReceptor:
    """Inicializa la configuración inmutable del receptor."""

    return ConfiguracionReceptor()
