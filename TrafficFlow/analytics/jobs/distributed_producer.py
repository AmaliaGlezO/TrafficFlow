"""Spark Structured Streaming job that generates synthetic traffic counts.

The job samples the baseline DfT traffic counts dataset and continuously produces
new observations with stochastic perturbations. Output is written to HDFS in
Parquet format at roughly the requested rate (default ~1500 rows/minute).
"""
from __future__ import annotations

import argparse
import logging
import sys
import uuid
from typing import List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


LOGGER = logging.getLogger("trafficflow.producer")


def parse_args(argv: List[str]) -> argparse.Namespace:
    """CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Distributed streaming producer for the DfT traffic dataset",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-path",
        required=True,
        help="Input CSV path in HDFS (raw DfT dataset).",
    )
    parser.add_argument(
        "--output-path",
        required=True,
        help="Output directory in HDFS where synthetic data will be appended.",
    )
    parser.add_argument(
        "--checkpoint-path",
        required=True,
        help="HDFS path for the Structured Streaming checkpoint state.",
    )
    parser.add_argument(
        "--rows-per-second",
        type=int,
        default=25,
        help="Target throughput (rows per second).",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=100_000,
        help="Number of baseline rows to sample as template pool. Set to 0 to use the full dataset (can be very large).",
    )
    parser.add_argument(
        "--variation-scale",
        type=float,
        default=0.18,
        help="Scale of Gaussian noise applied to traffic counts (fractional).",
    )
    parser.add_argument(
        "--shuffle-partitions",
        type=int,
        default=8,
        help="Number of shuffle partitions to use inside Spark.",
    )
    parser.add_argument(
        "--query-name",
        default="trafficflow_producer",
        help="Name assigned to the streaming query (for monitoring).",
    )
    return parser.parse_args(argv)


def build_base_pool(raw_df: DataFrame, sample_size: int) -> DataFrame:
    """Prepare the baseline pool of rows used to mimic the original distribution."""
    available_rows = raw_df.count()
    LOGGER.info("Baseline dataset contains %s rows", available_rows)

    if sample_size <= 0 or sample_size >= available_rows:
        LOGGER.info("Using entire dataset as generation pool")
        selected = raw_df
    else:
        fraction = min(1.0, sample_size / available_rows)
        LOGGER.info("Sampling approximately %s rows (fraction %.4f)", sample_size, fraction)
        sampled = raw_df.sample(withReplacement=False, fraction=fraction, seed=41)
        current = sampled.count()
        if current < sample_size:
            deficit = sample_size - current
            LOGGER.info("Sampling additional %s rows with replacement to fill the deficit", deficit)
            supplemental_fraction = min(1.0, float(deficit) / available_rows)
            supplemental = raw_df.sample(withReplacement=True, fraction=supplemental_fraction, seed=73)
            selected = sampled.unionByName(supplemental).limit(sample_size)
        else:
            selected = sampled.limit(sample_size)

    window = Window.orderBy(F.rand(seed=91))
    indexed = selected.withColumn("base_row_id", F.row_number().over(window) - 1)
    return indexed.select("base_row_id", *raw_df.columns)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    spark = (
        SparkSession.builder.appName("TrafficFlowDistributedProducer")
        .config("spark.sql.shuffle.partitions", args.shuffle_partitions)
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    numeric_columns = [
        "pedal_cycles",
        "two_wheeled_motor_vehicles",
        "cars_and_taxis",
        "buses_and_coaches",
        "lgvs",
        "hgvs_2_rigid_axle",
        "hgvs_3_rigid_axle",
        "hgvs_4_or_more_rigid_axle",
        "hgvs_3_or_4_articulated_axle",
        "hgvs_5_articulated_axle",
        "hgvs_6_articulated_axle",
        "all_hgvs",
        "all_motor_vehicles",
    ]

    LOGGER.info("Reading baseline dataset from %s", args.input_path)
    baseline_df = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(args.input_path)
        .dropna(subset=["count_point_id", "count_date", "hour"])
    )

    for column in numeric_columns:
        baseline_df = baseline_df.withColumn(column, F.col(column).cast("double"))

    baseline_df = baseline_df.persist()

    base_pool = build_base_pool(baseline_df, args.sample_size).persist()
    base_size = base_pool.count()
    LOGGER.info("Generation pool size: %s rows", base_size)

    if base_size == 0:
        LOGGER.error("No rows available in the generation pool. Aborting.")
        return 1

    base_pool = F.broadcast(base_pool)
    baseline_df.unpersist()

    run_id = str(uuid.uuid4())
    LOGGER.info("Producer run id: %s", run_id)

    rate_stream = (
        spark.readStream.format("rate").option("rowsPerSecond", args.rows_per_second).load()
    )

    enriched = (
        rate_stream.withColumn("base_row_id", F.col("value") % F.lit(base_size))
        .join(base_pool, on="base_row_id", how="left")
        .drop("value")
        .withColumnRenamed("timestamp", "event_time")
        .withColumn("producer_run_id", F.lit(run_id))
        .withColumn("ingestion_time", F.current_timestamp())
    )

    def apply_noise(col_name: str):
        seed = abs(hash(col_name)) % (2**31)
        raw_col = F.col(col_name).cast("double")
        noisy = raw_col * (1 + F.randn(seed) * F.lit(args.variation_scale))
        return F.round(F.greatest(noisy, F.lit(0.0))).cast("integer").alias(col_name)

    mutated = enriched
    for column in numeric_columns:
        mutated = mutated.withColumn(column, apply_noise(column))

    output_columns = [
        "event_time",
        "producer_run_id",
        "ingestion_time",
        "count_point_id",
        "direction_of_travel",
        "year",
        "count_date",
        "hour",
        "region_id",
        "region_name",
        "local_authority_id",
        "local_authority_name",
        "road_name",
        "road_type",
        "start_junction_road_name",
        "end_junction_road_name",
        "easting",
        "northing",
        "latitude",
        "longitude",
        "link_length_km",
        "link_length_miles",
        *numeric_columns,
    ]

    query = (
        mutated.select(*output_columns)
        .writeStream.format("parquet")
        .outputMode("append")
        .option("path", args.output_path)
        .option("checkpointLocation", args.checkpoint_path)
        .queryName(args.query_name)
        .trigger(processingTime="20 seconds")
        .start()
    )

    LOGGER.info(
        "Streaming query %s started. Writing to %s with checkpoint %s.",
        args.query_name,
        args.output_path,
        args.checkpoint_path,
    )

    try:
        query.awaitTermination()
    except KeyboardInterrupt:
        LOGGER.warning("Termination signal received; stopping query...")
        query.stop()
    finally:
        base_pool.unpersist()

    LOGGER.info("Query stopped cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
