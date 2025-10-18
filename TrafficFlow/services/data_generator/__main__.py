from __future__ import annotations

from .config import obtener_configuracion
from .logger import obtener_logger
from .service import ServicioGenerador
from .synthesizer import GeneradorEventosTrafico

logger = obtener_logger(__name__)


def main() -> None:
    configuracion = obtener_configuracion()
    logger.info("Cargando recursos desde %s", configuracion.directorio_datos)
    sintetizador = GeneradorEventosTrafico.desde_archivos(
        configuracion.ruta_autoridades,
        configuracion.ruta_categorias,
        configuracion.ruta_regiones,
    )
    servicio = ServicioGenerador(configuracion, sintetizador)
    servicio.ejecutar()


if __name__ == "__main__":
    main()
