"""Batch cleaning job for synthetic traffic flow data."""
from __future__ import annotations

import argparse
import logging
import sys
from typing import List

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

LOGGER = logging.getLogger("trafficflow.cleaning")


NUMERIC_COLUMNS = [
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


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TrafficFlow bronze-to-silver cleaning pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input-path", required=True, help="Input Parquet path in HDFS (bronze zone)")
    parser.add_argument("--output-path", required=True, help="Output Parquet path in HDFS (silver zone)")
    parser.add_argument(
        "--shuffle-partitions",
        type=int,
        default=12,
        help="Spark shuffle partitions for aggregations",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    spark = (
        SparkSession.builder.appName("TrafficFlowCleaningJob")
        .config("spark.sql.shuffle.partitions", args.shuffle_partitions)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    LOGGER.info("Reading bronze dataset from %s", args.input_path)
    bronze_df = spark.read.option("mergeSchema", True).parquet(args.input_path)

    LOGGER.info("Applying quality filters and standardising schema")

    cleaned = bronze_df.dropDuplicates(["event_time", "count_point_id", "direction_of_travel"])

    # Guard against negative or missing values introduced by the producer noise
    quality_condition = F.lit(True)
    for column in NUMERIC_COLUMNS:
        quality_condition = quality_condition & F.col(column).isNotNull() & (F.col(column) >= 0)

    cleaned = cleaned.filter(quality_condition)

    cleaned = (
        cleaned.withColumn("event_date", F.to_date("event_time"))
        .withColumn("event_hour", F.col("hour").cast("int"))
        .withColumn("weekday", F.date_format("event_date", "E"))
        .withColumn(
            "total_motor_traffic",
            F.col("all_motor_vehicles"),
        )
        .withColumn(
            "heavy_goods_share",
            F.when(F.col("all_motor_vehicles") > 0, F.col("all_hgvs") / F.col("all_motor_vehicles")).otherwise(0.0),
        )
    )

    LOGGER.info("Writing curated silver dataset to %s", args.output_path)
    (
        cleaned.repartition("event_date")
        .write.mode("overwrite")
        .partitionBy("event_date")
        .parquet(args.output_path)
    )

    LOGGER.info("Cleaning job completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
