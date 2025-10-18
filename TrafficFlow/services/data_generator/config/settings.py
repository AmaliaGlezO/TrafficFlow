from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Configuracion:
    """Parámetros de ejecución para el servicio generador."""

    servidores_kafka: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    topico_kafka: str = os.getenv("KAFKA_TOPIC", "trafico.eventos")
    topico_telemetria: str = os.getenv("KAFKA_TOPICO_TELEMETRIA", "trafico.telemetria")
    eventos_por_minuto: int = int(os.getenv("EVENTOS_POR_MINUTO", "150"))
    tamano_lote: int = int(os.getenv("TAMANO_LOTE_EVENTOS", "100"))
    directorio_datos: Path = Path(os.getenv("DIRECTORIO_DATOS", "/app/datos/referencia"))
    pesos_autoridades: str = os.getenv(
        "ARCHIVO_PESOS_AUTORIDADES", "local_authority_weights.csv"
    )
    pesos_categorias_viales: str = os.getenv(
        "ARCHIVO_PESOS_VIALES", "road_category_weights.csv"
    )
    limites_regiones: str = os.getenv("ARCHIVO_LIMITES_REGIONES", "region_bounds.json")
    productor_linger_ms: int = int(os.getenv("PRODUCER_LINGER_MS", "50"))
    productor_batch_bytes: int = int(os.getenv("PRODUCER_BATCH_BYTES", "65536"))
    habilitar_respaldo_stdout: bool = os.getenv("RESPALDO_STDOUT", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    identificador_sensor: str = os.getenv("IDENTIFICADOR_SENSOR", "generador")
    intervalo_latido_segundos: int = int(os.getenv("INTERVALO_LATIDO_SEGUNDOS", "20"))

    @property
    def ruta_autoridades(self) -> Path:
        return (self.directorio_datos / self.pesos_autoridades).resolve()

    @property
    def ruta_categorias(self) -> Path:
        return (self.directorio_datos / self.pesos_categorias_viales).resolve()

    @property
    def ruta_regiones(self) -> Path:
        return (self.directorio_datos / self.limites_regiones).resolve()


def obtener_configuracion() -> Configuracion:
    """Expone una instancia inmutable de configuración."""

    return Configuracion()
