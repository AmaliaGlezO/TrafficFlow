from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np

from .constants import MEZCLA_VEHICULAR, UMBRAL_CONGESTION
from .utils import TablaProbabilidades, cargar_tabla_probabilidades


@dataclass
@dataclass
class RecursosSintetizador:
    autoridades: TablaProbabilidades
    vias: TablaProbabilidades
    limites_regionales: Dict[str, Dict[str, float]]


class GeneradorEventosTrafico:
    """Genera eventos sintéticos que imitan el comportamiento histórico."""

    def __init__(self, recursos: RecursosSintetizador, rng: np.random.Generator | None = None) -> None:
        self._recursos = recursos
        self._rng = rng or np.random.default_rng()

    @classmethod
    def desde_archivos(
        cls,
        ruta_autoridades: Path,
        ruta_categorias: Path,
        ruta_regiones: Path,
    ) -> "GeneradorEventosTrafico":
        autoridades = cargar_tabla_probabilidades(
            ruta_autoridades,
            campo_etiqueta="local_authority_name",
            campo_peso="weight",
            campos_adicionales=("local_authority_id", "region_name"),
        )
        vias = cargar_tabla_probabilidades(
            ruta_categorias,
            campo_etiqueta="road_category",
            campo_peso="weight",
            campos_adicionales=("description",),
        )
        with open(ruta_regiones, "r", encoding="utf-8") as descriptor:
            limites: Dict[str, Dict[str, float]] = json.load(descriptor)
        recursos = RecursosSintetizador(autoridades, vias, limites)
        return cls(recursos)

    def generar(self) -> Dict[str, object]:
        autoridad = self._recursos.autoridades.seleccionar(self._rng)
        via = self._recursos.vias.seleccionar(self._rng)
        region = autoridad.metadatos.get("region_name", "Desconocida")
        limites = self._recursos.limites_regionales.get(region)
        if not limites:
            limites = {"lat_min": 53.0, "lat_max": 54.0, "lon_min": -2.0, "lon_max": -1.0}

        latitud = self._rng.uniform(limites["lat_min"], limites["lat_max"])
        longitud = self._rng.uniform(limites["lon_min"], limites["lon_max"])

        peso_autoridad = float(autoridad.probabilidad * 10_000)
        peso_via = float(via.probabilidad * 10_000)
        indice_demanda = max(20.0, self._rng.normal(peso_autoridad + peso_via, 15.0))

        vehiculos = self._construir_conteos(indice_demanda)
        volumen_total = sum(vehiculos.values())
        velocidad_media = self._estimar_velocidad(volumen_total, indice_demanda)
        congestion = self._determinar_congestion(velocidad_media)

        return {
            "event_id": f"evt-{int(time.time() * 1_000)}-{self._rng.integers(1_000_000):06d}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "region": region,
            "local_authority": autoridad.etiqueta,
            "road_category": via.etiqueta,
            "road_description": via.metadatos.get("description"),
            "latitude": round(latitud, 6),
            "longitude": round(longitud, 6),
            "average_speed_kph": round(velocidad_media, 2),
            "congestion_level": congestion,
            "vehicle_counts": vehiculos,
            "total_vehicles": volumen_total,
        }

    def _construir_conteos(self, indice_demanda: float) -> Dict[str, int]:
        conteos: Dict[str, int] = {}
        base = max(5.0, indice_demanda)
        for tipo, peso in MEZCLA_VEHICULAR.items():
            media = base * peso
            desviacion = max(media * 0.35, 1.0)
            conteos[tipo] = int(max(0.0, self._rng.normal(media, desviacion)))
        return conteos

    def _estimar_velocidad(self, volumen_total: int, indice_demanda: float) -> float:
        factor_volumen = math.log1p(volumen_total)
        velocidad_base = max(8.0, self._rng.normal(48.0, 12.0))
        ajuste = min(22.0, factor_volumen + indice_demanda * 0.02)
        return max(5.0, velocidad_base - ajuste)

    def _determinar_congestion(self, velocidad_media: float) -> str:
        if velocidad_media >= UMBRAL_CONGESTION["baja"]:
            return "baja"
        if velocidad_media >= UMBRAL_CONGESTION["media"]:
            return "media"
        if velocidad_media >= UMBRAL_CONGESTION["alta"]:
            return "alta"
        return "critica"
