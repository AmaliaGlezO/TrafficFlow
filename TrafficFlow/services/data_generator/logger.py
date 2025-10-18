from __future__ import annotations

import logging
import os

_NIVEL_REGISTROS = os.getenv("NIVEL_REGISTROS", "INFO").upper()


def configurar_registros() -> None:
    """Configura el formateo estándar de registros en español."""

    logging.basicConfig(
        level=_NIVEL_REGISTROS,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def obtener_logger(nombre: str) -> logging.Logger:
    """Devuelve un logger listo para usar."""

    configurar_registros()
    return logging.getLogger(nombre)
