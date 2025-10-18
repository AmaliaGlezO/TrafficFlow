from __future__ import annotations

from .config import obtener_configuracion
from .logger import obtener_logger
from .service import ServicioReceptor

logger = obtener_logger(__name__)


def main() -> None:
    configuracion = obtener_configuracion()
    logger.info("Iniciando receptor %s", configuracion.receptor_id)
    servicio = ServicioReceptor(configuracion)
    servicio.ejecutar()


if __name__ == "__main__":
    main()
