"""Synthetic traffic data producer container entrypoint."""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import signal
import sys
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

LOG = logging.getLogger("producer")
STOP_REQUESTED = False


def _handle_stop(signum: int, frame: object) -> None:  # pragma: no cover - signal handler
    global STOP_REQUESTED
    STOP_REQUESTED = True
    LOG.info("Termination signal received; shutting down producer loop")


DEFAULT_NUMERIC_PROFILE = {
    "log_mean": math.log1p(2500.0),
    "log_std": 0.6,
    "p05": 50.0,
    "p95": 90000.0,
}


DEFAULT_PROFILES = {
    "meta": {
        "generated_at": None,
        "source": "embedded defaults",
    },
    "region_distribution": {
        "South East": {"probability": 0.28, "region_id": "9"},
        "North West": {"probability": 0.18, "region_id": "5"},
        "East Midlands": {"probability": 0.14, "region_id": "2"},
        "London": {"probability": 0.16, "region_id": "7"},
        "West Midlands": {"probability": 0.12, "region_id": "4"},
        "South West": {"probability": 0.12, "region_id": "1"},
    },
    "local_authority_distribution": {
        "South East": [
            {
                "id": "E10000002",
                "name": "Buckinghamshire",
                "probability": 0.45,
                "latitude_mean": 51.76,
                "latitude_std": 0.12,
                "longitude_mean": -0.81,
                "longitude_std": 0.12,
            },
            {
                "id": "E10000016",
                "name": "West Sussex",
                "probability": 0.55,
                "latitude_mean": 50.92,
                "latitude_std": 0.10,
                "longitude_mean": -0.52,
                "longitude_std": 0.11,
            },
        ],
        "North West": [
            {
                "id": "E11000001",
                "name": "Manchester",
                "probability": 0.5,
                "latitude_mean": 53.48,
                "latitude_std": 0.08,
                "longitude_mean": -2.24,
                "longitude_std": 0.09,
            },
            {
                "id": "E10000017",
                "name": "Lancashire",
                "probability": 0.5,
                "latitude_mean": 53.86,
                "latitude_std": 0.12,
                "longitude_mean": -2.66,
                "longitude_std": 0.12,
            },
        ],
        "East Midlands": [
            {
                "id": "E10000013",
                "name": "Nottinghamshire",
                "probability": 0.6,
                "latitude_mean": 53.13,
                "latitude_std": 0.09,
                "longitude_mean": -1.17,
                "longitude_std": 0.09,
            },
            {
                "id": "E10000018",
                "name": "Leicestershire",
                "probability": 0.4,
                "latitude_mean": 52.64,
                "latitude_std": 0.09,
                "longitude_mean": -1.14,
                "longitude_std": 0.08,
            },
        ],
        "London": [
            {
                "id": "E09000020",
                "name": "City of Westminster",
                "probability": 0.4,
                "latitude_mean": 51.51,
                "latitude_std": 0.05,
                "longitude_mean": -0.15,
                "longitude_std": 0.05,
            },
            {
                "id": "E09000033",
                "name": "Wandsworth",
                "probability": 0.6,
                "latitude_mean": 51.46,
                "latitude_std": 0.05,
                "longitude_mean": -0.19,
                "longitude_std": 0.05,
            },
        ],
        "West Midlands": [
            {
                "id": "E08000025",
                "name": "Birmingham",
                "probability": 0.6,
                "latitude_mean": 52.48,
                "latitude_std": 0.07,
                "longitude_mean": -1.89,
                "longitude_std": 0.08,
            },
            {
                "id": "E08000028",
                "name": "Wolverhampton",
                "probability": 0.4,
                "latitude_mean": 52.59,
                "latitude_std": 0.07,
                "longitude_mean": -2.13,
                "longitude_std": 0.08,
            },
        ],
        "South West": [
            {
                "id": "E06000022",
                "name": "Bath and North East Somerset",
                "probability": 0.45,
                "latitude_mean": 51.38,
                "latitude_std": 0.08,
                "longitude_mean": -2.36,
                "longitude_std": 0.09,
            },
            {
                "id": "E06000026",
                "name": "Plymouth",
                "probability": 0.55,
                "latitude_mean": 50.38,
                "latitude_std": 0.07,
                "longitude_mean": -4.15,
                "longitude_std": 0.08,
            },
        ],
    },
    "road_type_distribution": {
        "Motorway": 0.24,
        "Trunk Road": 0.26,
        "Primary A Road": 0.2,
        "Secondary B Road": 0.18,
        "Minor Road": 0.12,
    },
    "hour_distribution": {
        "0": 0.013,
        "1": 0.01,
        "2": 0.009,
        "3": 0.009,
        "4": 0.012,
        "5": 0.02,
        "6": 0.045,
        "7": 0.075,
        "8": 0.095,
        "9": 0.07,
        "10": 0.062,
        "11": 0.06,
        "12": 0.06,
        "13": 0.06,
        "14": 0.062,
        "15": 0.07,
        "16": 0.082,
        "17": 0.09,
        "18": 0.06,
        "19": 0.045,
        "20": 0.033,
        "21": 0.023,
        "22": 0.016,
        "23": 0.018,
    },
    "day_of_week_distribution": {
        "1": 0.1,
        "2": 0.14,
        "3": 0.15,
        "4": 0.15,
        "5": 0.16,
        "6": 0.15,
        "7": 0.15,
    },
    "link_length_profiles": {
        "Motorway": {
            "log_mean": math.log1p(6.0),
            "log_std": 0.35,
            "p05": 0.5,
            "p95": 25.0,
        },
        "Trunk Road": {
            "log_mean": math.log1p(4.5),
            "log_std": 0.4,
            "p05": 0.3,
            "p95": 18.0,
        },
        "Primary A Road": {
            "log_mean": math.log1p(3.5),
            "log_std": 0.38,
            "p05": 0.2,
            "p95": 15.0,
        },
        "Secondary B Road": {
            "log_mean": math.log1p(2.0),
            "log_std": 0.42,
            "p05": 0.1,
            "p95": 10.0,
        },
        "Minor Road": {
            "log_mean": math.log1p(1.5),
            "log_std": 0.45,
            "p05": 0.05,
            "p95": 6.0,
        },
    },
    "density_profiles": {
        "Motorway": {
            "log_mean": math.log1p(12000.0),
            "log_std": 0.35,
            "p05": 1500.0,
            "p95": 28000.0,
        },
        "Trunk Road": {
            "log_mean": math.log1p(9000.0),
            "log_std": 0.38,
            "p05": 1200.0,
            "p95": 21000.0,
        },
        "Primary A Road": {
            "log_mean": math.log1p(7000.0),
            "log_std": 0.4,
            "p05": 900.0,
            "p95": 18000.0,
        },
        "Secondary B Road": {
            "log_mean": math.log1p(4200.0),
            "log_std": 0.42,
            "p05": 450.0,
            "p95": 12000.0,
        },
        "Minor Road": {
            "log_mean": math.log1p(2400.0),
            "log_std": 0.45,
            "p05": 200.0,
            "p95": 8500.0,
        },
    },
    "heavy_vehicle_share_profile": {
        "Motorway": {
            "log_mean": math.log1p(0.18),
            "log_std": 0.22,
            "p05": 0.05,
            "p95": 0.35,
        },
        "Trunk Road": {
            "log_mean": math.log1p(0.15),
            "log_std": 0.24,
            "p05": 0.04,
            "p95": 0.32,
        },
        "Primary A Road": {
            "log_mean": math.log1p(0.12),
            "log_std": 0.25,
            "p05": 0.03,
            "p95": 0.28,
        },
        "Secondary B Road": {
            "log_mean": math.log1p(0.09),
            "log_std": 0.26,
            "p05": 0.02,
            "p95": 0.22,
        },
        "Minor Road": {
            "log_mean": math.log1p(0.07),
            "log_std": 0.28,
            "p05": 0.01,
            "p95": 0.18,
        },
    },
    "vehicle_profiles": {
        "South East": {
            "log_mean": math.log1p(34000.0),
            "log_std": 0.42,
            "p05": 4500.0,
            "p95": 110000.0,
        },
        "North West": {
            "log_mean": math.log1p(28000.0),
            "log_std": 0.44,
            "p05": 3500.0,
            "p95": 95000.0,
        },
        "East Midlands": {
            "log_mean": math.log1p(24000.0),
            "log_std": 0.46,
            "p05": 3000.0,
            "p95": 88000.0,
        },
        "London": {
            "log_mean": math.log1p(38000.0),
            "log_std": 0.4,
            "p05": 5500.0,
            "p95": 125000.0,
        },
        "West Midlands": {
            "log_mean": math.log1p(26000.0),
            "log_std": 0.45,
            "p05": 3200.0,
            "p95": 90000.0,
        },
        "South West": {
            "log_mean": math.log1p(21000.0),
            "log_std": 0.47,
            "p05": 2500.0,
            "p95": 78000.0,
        },
    },
}


@dataclass
class Profiles:
    data: Dict[str, object]

    @property
    def region_distribution(self) -> Dict[str, Dict[str, float]]:
        return self.data.get("region_distribution", {})  # type: ignore[return-value]

    @property
    def local_authorities(self) -> Dict[str, List[Dict[str, float]]]:
        return self.data.get("local_authority_distribution", {})  # type: ignore[return-value]

    @property
    def road_type_distribution(self) -> Dict[str, float]:
        return self.data.get("road_type_distribution", {})  # type: ignore[return-value]

    @property
    def hour_distribution(self) -> Dict[str, float]:
        return self.data.get("hour_distribution", {})  # type: ignore[return-value]

    @property
    def day_of_week_distribution(self) -> Dict[str, float]:
        return self.data.get("day_of_week_distribution", {})  # type: ignore[return-value]

    @property
    def link_length_profiles(self) -> Dict[str, Dict[str, float]]:
        return self.data.get("link_length_profiles", {})  # type: ignore[return-value]

    @property
    def density_profiles(self) -> Dict[str, Dict[str, float]]:
        return self.data.get("density_profiles", {})  # type: ignore[return-value]

    @property
    def heavy_share_profiles(self) -> Dict[str, Dict[str, float]]:
        return self.data.get("heavy_vehicle_share_profile", {})  # type: ignore[return-value]

    @property
    def vehicle_profiles(self) -> Dict[str, Dict[str, float]]:
        return self.data.get("vehicle_profiles", {})  # type: ignore[return-value]


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthetic traffic producer")
    parser.add_argument(
        "--profile-path",
        default=os.environ.get("PROFILES_PATH", "/opt/producer/profiles/distributions.json"),
        help="Path to JSON file with probability distributions",
    )
    parser.add_argument(
        "--output-path",
        default=os.environ.get("OUTPUT_PATH", "/opt/producer/output/traffic_stream.jsonl"),
        help="Destination file for newline-delimited JSON output",
    )
    parser.add_argument(
        "--rate-per-minute",
        type=float,
        default=float(os.environ.get("RATE_PER_MINUTE", 1500.0)),
        help="Target emission rate (records per minute)",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=os.environ.get("MAX_RECORDS"),
        help="Optional cap used for dry runs or diagnostics",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    parser.add_argument(
        "--preview-records",
        type=int,
        default=int(os.environ.get("PREVIEW_RECORDS", 3)),
        help="Number of generated records echoed to stdout for sanity checks",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=os.environ.get("RANDOM_SEED"),
        help="Optional random seed for repeatability",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def load_profiles(path: str) -> Profiles:
    base = deepcopy(DEFAULT_PROFILES)
    candidate = Path(path)
    if candidate.exists():
        try:
            with candidate.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                base.update(data)
                LOG.info("Loaded profiles from %s", candidate)
        except (json.JSONDecodeError, OSError) as exc:
            LOG.warning("Failed to load profiles from %s (%s); using defaults", candidate, exc)
    else:
        LOG.warning("Profile file %s not found; using embedded defaults", candidate)
    return Profiles(base)


def weighted_choice_from_mapping(mapping: Dict[str, object]) -> Tuple[str, object]:
    if not mapping:
        raise ValueError("Empty distribution provided")
    total = 0.0
    items: List[Tuple[str, object]] = []
    for key, raw_value in mapping.items():
        prob = 0.0
        if isinstance(raw_value, dict):
            prob = float(raw_value.get("probability", 0.0))
        elif isinstance(raw_value, (int, float)):
            prob = float(raw_value)
        total += max(prob, 0.0)
        items.append((key, raw_value))
    if total <= 0.0:
        return random.choice(items)
    target = random.random() * total
    cumulative = 0.0
    for key, raw_value in items:
        prob = 0.0
        if isinstance(raw_value, dict):
            prob = float(raw_value.get("probability", 0.0))
        elif isinstance(raw_value, (int, float)):
            prob = float(raw_value)
        cumulative += max(prob, 0.0)
        if cumulative >= target:
            return key, raw_value
    return items[-1]


def weighted_choice_from_list(options: List[Dict[str, float]]) -> Dict[str, float]:
    if not options:
        raise ValueError("Empty distribution list provided")
    total = sum(max(float(option.get("probability", 0.0)), 0.0) for option in options)
    if total <= 0.0:
        return random.choice(options)
    target = random.random() * total
    cumulative = 0.0
    for option in options:
        cumulative += max(float(option.get("probability", 0.0)), 0.0)
        if cumulative >= target:
            return option
    return options[-1]


def sample_numeric(profile_map: Dict[str, Dict[str, float]], key: str) -> float:
    profile = profile_map.get(key)
    if profile is None and profile_map:
        profile = next(iter(profile_map.values()))
    if profile is None:
        profile = DEFAULT_NUMERIC_PROFILE
    mu = float(profile.get("log_mean", DEFAULT_NUMERIC_PROFILE["log_mean"]))
    sigma = max(float(profile.get("log_std", DEFAULT_NUMERIC_PROFILE["log_std"])), 1e-3)
    raw = math.exp(random.gauss(mu, sigma)) - 1.0
    lower = float(profile.get("p05", DEFAULT_NUMERIC_PROFILE["p05"]))
    upper = float(profile.get("p95", DEFAULT_NUMERIC_PROFILE["p95"]))
    if lower > upper:
        lower, upper = upper, lower
    return min(max(raw, lower), upper)


class JsonlWriter:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._file: Optional[object] = None

    def __enter__(self) -> "JsonlWriter":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self._path.open("a", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if self._file:
            self._file.flush()
            self._file.close()
            self._file = None

    def write(self, payload: Dict[str, object]) -> None:
        if self._file is None:
            raise RuntimeError("Writer is not opened")
        self._file.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self._file.flush()


class SyntheticRecordGenerator:
    def __init__(self, profiles: Profiles) -> None:
        self.profiles = profiles

    def _pick_region(self) -> Tuple[str, Dict[str, float]]:
        name, payload = weighted_choice_from_mapping(self.profiles.region_distribution)
        if not isinstance(payload, dict):
            payload = {"probability": payload, "region_id": "0"}
        return name, payload

    def _pick_authority(self, region: str) -> Dict[str, float]:
        options = self.profiles.local_authorities.get(region) or []
        if not options:
            options = [
                {
                    "id": "UNKNOWN",
                    "name": f"{region} Authority",
                    "probability": 1.0,
                    "latitude_mean": 53.0,
                    "latitude_std": 0.2,
                    "longitude_mean": -1.5,
                    "longitude_std": 0.2,
                }
            ]
        return weighted_choice_from_list(options)

    def _pick_road_type(self) -> str:
        road_type, _ = weighted_choice_from_mapping(self.profiles.road_type_distribution)
        return road_type

    def _pick_hour(self) -> int:
        hour_key, _ = weighted_choice_from_mapping(self.profiles.hour_distribution or {str(i): 1 / 24 for i in range(24)})
        return int(hour_key)

    def _pick_day_of_week(self) -> int:
        day_key, _ = weighted_choice_from_mapping(
            self.profiles.day_of_week_distribution or {str(i): 1 / 7 for i in range(1, 8)}
        )
        return int(day_key)

    def _build_timestamp(self, base_time: datetime, hour: int, target_day: int) -> datetime:
        iso_today = base_time.isoweekday()
        spark_today = (iso_today % 7) + 1
        delta_days = (target_day - spark_today) % 7
        date_target = (base_time + timedelta(days=delta_days)).date()
        minute = random.randint(0, 59)
        return datetime(
            date_target.year,
            date_target.month,
            date_target.day,
            hour,
            minute,
            tzinfo=timezone.utc,
        )

    @staticmethod
    def _sample_coordinate(mean: float, std: float) -> float:
        std = max(std, 0.01)
        return random.gauss(mean, std)

    def sample(self, base_time: Optional[datetime] = None) -> Dict[str, object]:
        base_time = base_time or datetime.now(timezone.utc)
        region_name, region_payload = self._pick_region()
        authority = self._pick_authority(region_name)
        road_type = self._pick_road_type()
        hour = self._pick_hour()
        day = self._pick_day_of_week()
        event_ts = self._build_timestamp(base_time, hour, day)

        link_length = sample_numeric(self.profiles.link_length_profiles, road_type)
        density = sample_numeric(self.profiles.density_profiles, road_type)
        regional_volume = sample_numeric(self.profiles.vehicle_profiles, region_name)
        heavy_share = sample_numeric(self.profiles.heavy_share_profiles, road_type)
        heavy_share = max(min(heavy_share, 0.95), 0.0)

        vehicles = max((density * link_length + regional_volume) / 2.0, 1.0)
        hgvs = vehicles * heavy_share
        vehicles_per_km = vehicles / link_length if link_length > 0 else density

        latitude = self._sample_coordinate(float(authority.get("latitude_mean", 53.0)), float(authority.get("latitude_std", 0.1)))
        longitude = self._sample_coordinate(float(authority.get("longitude_mean", -1.5)), float(authority.get("longitude_std", 0.1)))

        road_prefix = {
            "Motorway": "M",
            "Trunk Road": "A",
            "Primary A Road": "A",
            "Secondary B Road": "B",
            "Minor Road": "C",
        }.get(road_type, "R")
        road_name = f"{road_prefix}{random.randint(1, 9999)}"

        record = {
            "count_point_id": f"CP-{uuid.uuid4().hex[:10].upper()}",
            "count_date": event_ts.date().isoformat(),
            "hour": f"{hour:02d}",
            "region_id": region_payload.get("region_id", "0"),
            "region_name": region_name,
            "local_authority_id": authority.get("id", "UNKNOWN"),
            "local_authority_name": authority.get("name", f"{region_name} Authority"),
            "road_name": road_name,
            "road_type": road_type,
            "link_length_km": round(link_length, 3),
            "all_motor_vehicles": int(round(vehicles)),
            "all_hgvs": int(round(hgvs)),
            "event_timestamp": event_ts.isoformat(),
            "year": event_ts.year,
            "vehicles_per_km": round(vehicles_per_km, 3),
            "heavy_vehicle_share": round(heavy_share, 4),
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
        }
        return record


class ProducerRunner:
    def __init__(self, generator: SyntheticRecordGenerator, writer: JsonlWriter, rate_per_minute: float) -> None:
        self.generator = generator
        self.writer = writer
        self.interval = 60.0 / max(rate_per_minute, 1.0)

    def run(self, max_records: Optional[int], preview_records: int) -> None:
        produced = 0
        next_emit = time.perf_counter()
        preview_remaining = max(preview_records, 0)
        with self.writer as out:
            while not STOP_REQUESTED:
                if max_records is not None and produced >= max_records:
                    break
                now = time.perf_counter()
                if now < next_emit:
                    time.sleep(min(self.interval, next_emit - now))
                record = self.generator.sample()
                out.write(record)
                produced += 1
                if preview_remaining > 0:
                    LOG.info("Preview record: %s", record)
                    preview_remaining -= 1
                next_emit += self.interval
                if produced % 500 == 0:
                    LOG.info("Generated %s records", produced)
        LOG.info("Producer stopped after emitting %s records", produced)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level)
    if args.seed is not None:
        random.seed(int(args.seed))
        LOG.info("Random seed set to %s", args.seed)

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    profiles = load_profiles(args.profile_path)
    generator = SyntheticRecordGenerator(profiles)
    writer = JsonlWriter(args.output_path)
    runner = ProducerRunner(generator, writer, rate_per_minute=args.rate_per_minute)
    try:
        runner.run(
            max_records=int(args.max_records) if args.max_records is not None else None,
            preview_records=args.preview_records,
        )
    except ValueError as exc:
        LOG.error("Producer halted due to invalid configuration: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
