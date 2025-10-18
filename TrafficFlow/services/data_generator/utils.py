from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class SeleccionPonderada:
    etiqueta: str
    metadatos: Dict[str, object]
    probabilidad: float


class TablaProbabilidades:
    """Representa una distribución discreta para muestreo aleatorio."""

    def __init__(self, candidatos: List[SeleccionPonderada]):
        if not candidatos:
            raise ValueError("La tabla de probabilidades requiere al menos un elemento")
        total = sum(c.probabilidad for c in candidatos)
        if total <= 0:
            raise ValueError("Las ponderaciones deben ser positivas")
        self._candidatos = candidatos
        self._probabilidades = np.array([c.probabilidad for c in candidatos], dtype=float) / total

    def seleccionar(self, rng: np.random.Generator | None = None) -> SeleccionPonderada:
        rng = rng or np.random.default_rng()
        indice = rng.choice(len(self._candidatos), p=self._probabilidades)
        return self._candidatos[indice]


def cargar_tabla_probabilidades(
    ruta_csv: Path,
    campo_etiqueta: str,
    campo_peso: str,
    campos_adicionales: Tuple[str, ...] | None = None,
) -> TablaProbabilidades:
    campos_adicionales = campos_adicionales or tuple()
    df = pd.read_csv(ruta_csv)
    candidatos = [
        SeleccionPonderada(
            etiqueta=str(fila[campo_etiqueta]),
            metadatos={campo: fila[campo] for campo in campos_adicionales},
            probabilidad=float(fila[campo_peso]),
        )
        for _, fila in df.iterrows()
    ]
    return TablaProbabilidades(candidatos)
