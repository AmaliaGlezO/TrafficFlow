from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Tuple

from .config import ConfiguracionReceptor


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def preparar_detalle(evento: Dict[str, object], configuracion: ConfiguracionReceptor) -> Dict[str, object]:
    """Construye un registro enriquecido que será persistido."""

    detalle = dict(evento)
    detalle.setdefault("sensor_id", evento.get("sensor_id", "desconocido"))
    detalle["receiver_id"] = configuracion.receptor_id
    detalle["processed_at"] = _ahora_iso()
    return detalle


def preparar_dashboard(detalle: Dict[str, object]) -> Dict[str, object]:
    """Extrae la información relevante para el tablero en tiempo real."""

    return {
        "receiver_id": detalle.get("receiver_id"),
        "sensor_id": detalle.get("sensor_id"),
        "timestamp": detalle.get("timestamp"),
        "processed_at": detalle.get("processed_at"),
        "region": detalle.get("region"),
        "local_authority": detalle.get("local_authority"),
        "road_category": detalle.get("road_category"),
        "road_description": detalle.get("road_description"),
        "latitude": detalle.get("latitude"),
        "longitude": detalle.get("longitude"),
        "average_speed_kph": detalle.get("average_speed_kph"),
        "congestion_level": detalle.get("congestion_level"),
        "total_vehicles": detalle.get("total_vehicles"),
        "vehicle_counts": detalle.get("vehicle_counts"),
    }


def procesar_evento(
    evento: Dict[str, object], configuracion: ConfiguracionReceptor
) -> Tuple[Dict[str, object], Dict[str, object]]:
    """Devuelve el detalle persistible y la vista para tablero."""

    detalle = preparar_detalle(evento, configuracion)
    dashboard = preparar_dashboard(detalle)
    return detalle, dashboard
