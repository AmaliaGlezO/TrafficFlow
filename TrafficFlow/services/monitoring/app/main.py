"""TrafficFlow Monitoring Console implemented with Streamlit.

Features:
- Producer status panel powered by YARN ResourceManager REST API.
- Near real-time exploratory analytics over the synthetic streaming (bronze) layer.
- Comparative exploratory analytics over the original static dataset.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pandas as pd
import requests
import streamlit as st
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from streamlit_autorefresh import st_autorefresh

SPARK_MASTER_URL = os.getenv("SPARK_MASTER_URL", "spark://spark-master:7077")
HDFS_DEFAULT_FS = os.getenv("HDFS_NAMENODE_URL", "hdfs://namenode:8020")
BRONZE_PARQUET_PATH = os.getenv(
    "BRONZE_PARQUET_PATH", "hdfs://namenode:8020/data/bronze/trafficflow"
)
RAW_DATASET_PATH = os.getenv(
    "RAW_DATASET_PATH", "hdfs://namenode:8020/data/raw/dft_traffic_counts_raw_counts.csv"
)
YARN_RESOURCE_MANAGER_URL = os.getenv(
    "YARN_RESOURCE_MANAGER_URL", "http://resourcemanager:8088"
)
PRODUCER_APP_NAME = os.getenv("PRODUCER_APP_NAME", "TrafficFlowDistributedProducer")
STATIC_SAMPLE_FRACTION = float(os.getenv("STATIC_SAMPLE_FRACTION", "0.05"))


@st.cache_resource(show_spinner=False)
def get_spark_session() -> SparkSession:
    """Initialise or reuse a SparkSession for analytics queries."""
    spark = (
        SparkSession.builder.appName("TrafficFlowMonitoring")
        .master(SPARK_MASTER_URL)
        .config("spark.hadoop.fs.defaultFS", HDFS_DEFAULT_FS)
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SQL_PARTITIONS", "8"))
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def _format_epoch_millis(value: Optional[int]) -> str:
    if value in (None, -1, 0):
        return "N/D"
    return (
        datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        .strftime("%Y-%m-%d %H:%M:%S %Z")
    )


def fetch_producer_status() -> Dict[str, Any]:
    """Fetch producer application status from YARN."""
    endpoint = YARN_RESOURCE_MANAGER_URL.rstrip("/") + "/ws/v1/cluster/apps"
    params = {"states": "ALL", "applicationTypes": "SPARK", "limit": 200}
    try:
        response = requests.get(endpoint, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        apps = data.get("apps", {}).get("app", [])
        for app in apps:
            if app.get("name") == PRODUCER_APP_NAME:
                return {
                    "state": app.get("state", "UNKNOWN"),
                    "final_status": app.get("finalStatus", "UNKNOWN"),
                    "progress": float(app.get("progress", 0.0)),
                    "tracking_url": app.get("trackingUrl"),
                    "started": _format_epoch_millis(app.get("startedTime")),
                    "finished": _format_epoch_millis(app.get("finishedTime")),
                    "elapsed_ms": app.get("elapsedTime", 0),
                    "user": app.get("user", "-"),
                    "queue": app.get("queue", "default"),
                }
    except requests.RequestException as exc:  # network error
        return {
            "state": "UNREACHABLE",
            "final_status": "N/D",
            "progress": 0.0,
            "tracking_url": None,
            "started": "N/D",
            "finished": "N/D",
            "elapsed_ms": 0,
            "user": "-",
            "queue": "-",
            "error": str(exc),
        }

    return {
        "state": "NOT_FOUND",
        "final_status": "N/D",
        "progress": 0.0,
        "tracking_url": None,
        "started": "N/D",
        "finished": "N/D",
        "elapsed_ms": 0,
        "user": "-",
        "queue": "default",
    }


@st.cache_data(show_spinner=False, ttl=60)
def load_bronze_metrics(window_hours: int) -> Dict[str, Any]:
    spark = get_spark_session()
    df = spark.read.parquet(BRONZE_PARQUET_PATH)

    if df.rdd.isEmpty():
        return {
            "row_count": 0,
            "total_vehicles": 0,
            "latest_event_time": "N/D",
            "hourly": pd.DataFrame(columns=["event_hour", "vehicles"]),
            "regions": pd.DataFrame(columns=["region_name", "vehicles"]),
            "hgvs_share": pd.DataFrame(columns=["region_name", "avg_hgvs_share", "total_flow"]),
            "authorities": pd.DataFrame(columns=["local_authority_name", "vehicles"]),
        }

    lower_bound = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    df_recent = (
        df.withColumn("event_hour", F.date_trunc("hour", F.col("event_time")))
        .filter(F.col("event_time") >= F.lit(lower_bound))
        .cache()
    )

    row_count = df_recent.count()
    total_vehicles = df_recent.agg(F.sum("all_motor_vehicles").alias("vehicles")).collect()[0][0] or 0
    latest_event = df.agg(F.max("event_time").alias("latest")).collect()[0][0]

    hourly = (
        df_recent.groupBy("event_hour")
        .agg(F.sum("all_motor_vehicles").alias("vehicles"))
        .orderBy("event_hour")
        .toPandas()
    )

    regions = (
        df_recent.groupBy("region_name")
        .agg(F.sum("all_motor_vehicles").alias("vehicles"))
        .orderBy(F.desc("vehicles"))
        .limit(10)
        .toPandas()
    )

    hgvs_share = (
        df_recent.groupBy("region_name")
        .agg(
            F.avg(
                F.when(
                    F.col("all_motor_vehicles") > 0,
                    F.col("all_hgvs") / F.col("all_motor_vehicles"),
                ).otherwise(0.0)
            ).alias("avg_hgvs_share"),
            F.sum("all_motor_vehicles").alias("total_flow"),
        )
        .filter(F.col("total_flow") > 0)
        .orderBy(F.desc("avg_hgvs_share"))
        .limit(10)
        .toPandas()
    )

    authorities = (
        df_recent.groupBy("local_authority_name")
        .agg(F.sum("all_motor_vehicles").alias("vehicles"))
        .orderBy(F.desc("vehicles"))
        .limit(10)
        .toPandas()
    )

    df_recent.unpersist()

    if latest_event is not None:
        if getattr(latest_event, "tzinfo", None) is None:
            latest_event = latest_event.replace(tzinfo=timezone.utc)
        latest_formatted = latest_event.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    else:
        latest_formatted = "N/D"

    return {
        "row_count": row_count,
        "total_vehicles": int(total_vehicles),
        "latest_event_time": latest_formatted,
        "hourly": hourly,
        "regions": regions,
        "hgvs_share": hgvs_share,
        "authorities": authorities,
    }


@st.cache_data(show_spinner=False, ttl=300)
def load_static_metrics(sample_fraction: float) -> Dict[str, Any]:
    spark = get_spark_session()
    df = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(RAW_DATASET_PATH)
        .withColumn("hour", F.col("hour").cast("int"))
    )

    if 0 < sample_fraction < 1:
        df = df.sample(withReplacement=False, fraction=sample_fraction, seed=42)

    df = df.withColumn(
        "event_time",
        F.to_timestamp(
            F.concat_ws(
                " ",
                F.col("count_date"),
                F.format_string("%02d:00:00", F.col("hour")),
            )
        ),
    )

    df = df.withColumn("event_hour", F.date_trunc("hour", F.col("event_time")))

    row_count = df.count()
    total_vehicles = df.agg(F.sum("all_motor_vehicles").alias("vehicles")).collect()[0][0] or 0

    hourly = (
        df.groupBy("event_hour")
        .agg(F.sum("all_motor_vehicles").alias("vehicles"))
        .orderBy("event_hour")
        .limit(500)
        .toPandas()
    )

    regions = (
        df.groupBy("region_name")
        .agg(F.sum("all_motor_vehicles").alias("vehicles"))
        .orderBy(F.desc("vehicles"))
        .limit(10)
        .toPandas()
    )

    hgvs_share = (
        df.groupBy("region_name")
        .agg(
            F.avg(
                F.when(
                    F.col("all_motor_vehicles") > 0,
                    F.col("all_hgvs") / F.col("all_motor_vehicles"),
                ).otherwise(0.0)
            ).alias("avg_hgvs_share"),
            F.sum("all_motor_vehicles").alias("total_flow"),
        )
        .filter(F.col("total_flow") > 0)
        .orderBy(F.desc("avg_hgvs_share"))
        .limit(10)
        .toPandas()
    )

    authorities = (
        df.groupBy("local_authority_name")
        .agg(F.sum("all_motor_vehicles").alias("vehicles"))
        .orderBy(F.desc("vehicles"))
        .limit(10)
        .toPandas()
    )

    return {
        "row_count": row_count,
        "total_vehicles": int(total_vehicles),
        "hourly": hourly,
        "regions": regions,
        "hgvs_share": hgvs_share,
        "authorities": authorities,
    }


def draw_producer_status():
    status = fetch_producer_status()
    state = status.get("state", "UNKNOWN")
    progress = status.get("progress", 0.0)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("State", state)
    col2.metric("Progress", f"{progress:.1f}%")
    col3.metric("Started", status.get("started", "N/D"))
    col4.metric("Finished", status.get("finished", "N/D"))

    col5, col6, col7 = st.columns(3)
    col5.metric("Final Status", status.get("final_status", "N/D"))
    col6.metric("User", status.get("user", "-"))
    col7.metric("Queue", status.get("queue", "default"))

    tracking_url = status.get("tracking_url")
    if tracking_url:
        st.markdown(f"- Tracking URL: [{tracking_url}]({tracking_url})")
    if status.get("state") == "UNREACHABLE":
        st.warning("ResourceManager API is unreachable. Check networking or container health.")
    if status.get("state") == "NOT_FOUND":
        st.info(
            "Producer job is not currently registered in YARN. Launch the streaming job to begin production."
        )
    if "error" in status:
        st.error(f"YARN API error: {status['error']}")


def draw_live_dashboard(window_hours: int):
    st.subheader("Live Synthetic Stream (Bronze Layer)")
    try:
        metrics = load_bronze_metrics(window_hours)
    except Exception as exc:  # pylint: disable=broad-except
        st.error(f"No se pudieron cargar los datos de la capa bronze: {exc}")
        return

    if metrics["row_count"] == 0:
        st.info("Sin datos recientes en la ventana seleccionada. Verifique que el productor este activo.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Filas recientes", f"{metrics['row_count']:,}")
    col2.metric("Vehiculos recientes", f"{metrics['total_vehicles']:,}")
    col3.metric("Ultimo evento", metrics["latest_event_time"])

    hourly = metrics["hourly"]
    if not hourly.empty:
        hourly["event_hour"] = pd.to_datetime(hourly["event_hour"])
        st.plotly_chart(
            {
                "data": [
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "x": hourly["event_hour"],
                        "y": hourly["vehicles"],
                        "name": "Vehiculos",
                    }
                ],
                "layout": {"title": "Flujo por hora", "xaxis": {"title": "Hora"}, "yaxis": {"title": "Vehiculos"}},
            },
            use_container_width=True,
        )

    cols = st.columns(2)
    regions = metrics["regions"]
    if not regions.empty:
        cols[0].plotly_chart(
            {
                "data": [
                    {
                        "type": "bar",
                        "x": regions["region_name"],
                        "y": regions["vehicles"],
                        "name": "Vehiculos",
                    }
                ],
                "layout": {"title": "Top regiones por flujo", "xaxis": {"title": "Region"}, "yaxis": {"title": "Vehiculos"}},
            },
            use_container_width=True,
        )

    hgvs_share = metrics["hgvs_share"]
    if not hgvs_share.empty:
        cols[1].plotly_chart(
            {
                "data": [
                    {
                        "type": "bar",
                        "x": hgvs_share["region_name"],
                        "y": hgvs_share["avg_hgvs_share"],
                        "name": "Participacion HGV",
                    }
                ],
                "layout": {
                    "title": "Participacion promedio de vehiculos pesados",
                    "xaxis": {"title": "Region"},
                    "yaxis": {"title": "Proporcion"},
                },
            },
            use_container_width=True,
        )

    st.markdown("#### Autoridades locales con mayor flujo")
    st.dataframe(metrics["authorities"], use_container_width=True)


def draw_static_dashboard(sample_fraction: float):
    st.subheader("Dataset Estatico (Subconjunto de Referencia)")
    try:
        metrics = load_static_metrics(sample_fraction)
    except Exception as exc:  # pylint: disable=broad-except
        st.error(f"No se pudieron cargar las metricas del dataset estatico: {exc}")
        return

    if metrics["row_count"] == 0:
        st.info("No se encontraron filas en el dataset estatico. Verifique la carga en HDFS.")
        return

    col1, col2 = st.columns(2)
    col1.metric("Filas muestreadas", f"{metrics['row_count']:,}")
    col2.metric("Vehiculos totales (muestra)", f"{metrics['total_vehicles']:,}")

    hourly = metrics["hourly"]
    if not hourly.empty:
        hourly["event_hour"] = pd.to_datetime(hourly["event_hour"])
        st.plotly_chart(
            {
                "data": [
                    {
                        "type": "scatter",
                        "mode": "lines",
                        "x": hourly["event_hour"],
                        "y": hourly["vehicles"],
                        "name": "Vehiculos",
                    }
                ],
                "layout": {"title": "Flujo historico por hora (muestra)", "xaxis": {"title": "Hora"}, "yaxis": {"title": "Vehiculos"}},
            },
            use_container_width=True,
        )

    cols = st.columns(2)
    regions = metrics["regions"]
    if not regions.empty:
        cols[0].plotly_chart(
            {
                "data": [
                    {
                        "type": "bar",
                        "x": regions["region_name"],
                        "y": regions["vehicles"],
                        "name": "Vehiculos",
                    }
                ],
                "layout": {"title": "Top regiones historicas", "xaxis": {"title": "Region"}, "yaxis": {"title": "Vehiculos"}},
            },
            use_container_width=True,
        )

    hgvs_share = metrics["hgvs_share"]
    if not hgvs_share.empty:
        cols[1].plotly_chart(
            {
                "data": [
                    {
                        "type": "bar",
                        "x": hgvs_share["region_name"],
                        "y": hgvs_share["avg_hgvs_share"],
                        "name": "Participacion HGV",
                    }
                ],
                "layout": {
                    "title": "Participacion promedio de vehiculos pesados (historico)",
                    "xaxis": {"title": "Region"},
                    "yaxis": {"title": "Proporcion"},
                },
            },
            use_container_width=True,
        )

    st.markdown("#### Autoridades locales con mayor flujo historico")
    st.dataframe(metrics["authorities"], use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="TrafficFlow Monitoring", layout="wide", page_icon="TF")
    st.title("TrafficFlow Monitoring Console")
    st.caption("Vigila el productor distribuido y explora las metricas clave del trafico sintetico y del dataset original.")

    with st.sidebar:
        st.header("Configuracion")
        auto_refresh = st.checkbox("Auto refrescar", value=True)
        refresh_interval = st.slider("Intervalo (segundos)", min_value=10, max_value=120, value=30, step=5)
        window_hours = st.select_slider("Ventana de analisis en streaming (horas)", options=[1, 3, 6, 12, 24], value=6)
        sample_fraction = st.slider(
            "Fraccion de muestreo dataset estatico", min_value=0.01, max_value=1.0, value=STATIC_SAMPLE_FRACTION, step=0.01
        )
        st.markdown("---")
        st.markdown("**Parametros**")
        st.write(f"Spark master: `{SPARK_MASTER_URL}`")
        st.write(f"Bronze path: `{BRONZE_PARQUET_PATH}`")
        st.write(f"Dataset estatico: `{RAW_DATASET_PATH}`")

        if auto_refresh:
            st_autorefresh(interval=refresh_interval * 1000, key="trafficflow-monitoring-refresh")

    st.subheader("Estado del productor")
    draw_producer_status()

    draw_live_dashboard(window_hours)
    draw_static_dashboard(sample_fraction)


if __name__ == "__main__":
    main()
