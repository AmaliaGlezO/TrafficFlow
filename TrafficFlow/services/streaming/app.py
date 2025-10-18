from __future__ import annotations

import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import (avg, col, from_json, sum as spark_sum, to_timestamp,
                                   window)
from pyspark.sql.types import (DoubleType, IntegerType, StringType, StructField,
                               StructType)


def obtener_configuracion() -> dict[str, str]:
    """Recupera parámetros de entorno con valores por defecto."""

    return {
        "bootstrap": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        "topico": os.getenv(
            "KAFKA_TOPIC",
            os.getenv("KAFKA_TOPIC_ENTRADA", "trafico.detalle"),
        ),
        "ruta_detalle": os.getenv(
            "HDFS_RUTA_DETALLE",
            os.getenv("HDFS_BRONCE_PATH", "hdfs://namenode:9000/datalake/bronze/eventos"),
        ),
        "ruta_metricas": os.getenv(
            "HDFS_RUTA_METRICAS",
            os.getenv("HDFS_PLATA_PATH", "hdfs://namenode:9000/datalake/silver/metricas"),
        ),
        "ruta_checkpoint": os.getenv(
            "HDFS_RUTA_CHECKPOINT",
            os.getenv(
                "STREAM_CHECKPOINT_PATH",
                "hdfs://namenode:9000/datalake/checkpoints/streaming",
            ),
        ),
    }


def crear_sesion_spark() -> SparkSession:
    """Configura una sesión Spark lista para streaming estructurado."""

    return (
        SparkSession.builder.appName("IngestaTraficoTiempoReal")
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_PARTITIONS", "4"))
        .config("spark.sql.streaming.schemaInference", "false")
        .getOrCreate()
    )


def construir_esquema_evento() -> StructType:
    """Esquema estricto que describe el JSON de los eventos de tráfico."""

    vehiculos_schema = StructType(
        [
            StructField("pedal_cycles", IntegerType()),
            StructField("two_wheeled_motor_vehicles", IntegerType()),
            StructField("cars_and_taxis", IntegerType()),
            StructField("buses_and_coaches", IntegerType()),
            StructField("lgvs", IntegerType()),
            StructField("all_hgvs", IntegerType()),
        ]
    )

    return StructType(
        [
            StructField("event_id", StringType(), False),
            StructField("timestamp", StringType(), False),
            StructField("processed_at", StringType(), False),
            StructField("sensor_id", StringType(), False),
            StructField("receiver_id", StringType(), False),
            StructField("region", StringType(), False),
            StructField("local_authority", StringType(), False),
            StructField("road_category", StringType(), False),
            StructField("road_description", StringType(), True),
            StructField("latitude", DoubleType(), False),
            StructField("longitude", DoubleType(), False),
            StructField("average_speed_kph", DoubleType(), False),
            StructField("congestion_level", StringType(), False),
            StructField("vehicle_counts", vehiculos_schema, False),
            StructField("total_vehicles", IntegerType(), False),
        ]
    )


def preparar_eventos(df_raw, esquema: StructType):
    """Convierte el flujo Kafka en columnas tipadas."""

    return (
        df_raw.select(from_json(col("value").cast("string"), esquema).alias("evento"))
        .select("evento.*")
        .withColumn("registro_ts", to_timestamp(col("timestamp")))
        .withColumn("procesado_ts", to_timestamp(col("processed_at")))
    )


def construir_metricas(df_eventos):
    """Calcula agregados por región y nivel de congestión cada minuto."""

    return (
        df_eventos.withWatermark("registro_ts", "2 minutes")
        .groupBy(
            window(col("registro_ts"), "1 minute"),
            col("region"),
            col("congestion_level"),
        )
        .agg(
            spark_sum("total_vehicles").alias("vehiculos_totales"),
            avg("average_speed_kph").alias("velocidad_media"),
        )
    )


def main() -> None:
    configuracion = obtener_configuracion()
    spark = crear_sesion_spark()
    spark.sparkContext.setLogLevel("WARN")

    esquema = construir_esquema_evento()

    flujo_crudo = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", configuracion["bootstrap"])
        .option("subscribe", configuracion["topico"])
        .option("startingOffsets", "latest")
        .load()
    )

    eventos = preparar_eventos(flujo_crudo, esquema)
    metricas = construir_metricas(eventos)

    consulta_detalle = (
        eventos.writeStream.format("parquet")
        .option("path", configuracion["ruta_detalle"])
        .option("checkpointLocation", os.path.join(configuracion["ruta_checkpoint"], "detalle"))
        .outputMode("append")
        .start()
    )

    consulta_metricas = (
        metricas.writeStream.format("parquet")
        .option("path", configuracion["ruta_metricas"])
        .option("checkpointLocation", os.path.join(configuracion["ruta_checkpoint"], "metricas"))
        .outputMode("update")
        .start()
    )

    spark.streams.awaitAnyTermination()
    consulta_detalle.awaitTermination()
    consulta_metricas.awaitTermination()


if __name__ == "__main__":
    main()
