from __future__ import annotations

import logging
import os

_NIVEL = os.getenv("NIVEL_REGISTROS", "INFO").upper()


def configurar_registros() -> None:
    logging.basicConfig(
        level=_NIVEL,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def obtener_logger(nombre: str) -> logging.Logger:
    configurar_registros()
    return logging.getLogger(nombre)
