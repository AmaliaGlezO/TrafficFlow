"""Spark batch job for basic cleaning and normalization of the DfT traffic counts dataset."""
from __future__ import annotations

import argparse
from typing import List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


ESSENTIAL_COLUMNS: List[str] = [
    "count_point_id",
    "count_date",
    "hour",
    "region_id",
    "region_name",
    "local_authority_id",
    "local_authority_name",
    "road_name",
    "road_type",
    "link_length_km",
    "all_motor_vehicles",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean the raw DfT traffic dataset and store it in the silver zone")
    parser.add_argument("--input-path", required=True, help="HDFS path to the raw CSV dataset")
    parser.add_argument("--output-path", required=True, help="Destination path for the cleaned Parquet data")
    parser.add_argument(
        "--partition-columns",
        nargs="*",
        default=["year", "region_name"],
        help="Columns used to partition the silver dataset",
    )
    parser.add_argument(
        "--repartition",
        type=int,
        default=16,
        help="Number of partitions to use before writing the output",
    )
    return parser.parse_args()


def get_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("TfDataCleaning")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def cast_numeric_columns(df: DataFrame) -> DataFrame:
    vehicle_columns = [
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
    length_columns = ["link_length_km", "link_length_miles"]

    for column in vehicle_columns + length_columns:
        if column in df.columns:
            df = df.withColumn(column, F.col(column).cast("double"))
    return df


def enrich_columns(df: DataFrame) -> DataFrame:
    df = df.filter(F.col("all_motor_vehicles").isNotNull())

    df = df.withColumn("event_timestamp", F.to_timestamp("count_date"))
    df = df.withColumn("year", F.year("event_timestamp"))
    df = df.withColumn(
        "vehicles_per_km",
        F.when(F.col("link_length_km") > 0, F.col("all_motor_vehicles") / F.col("link_length_km")).otherwise(None),
    )
    df = df.withColumn(
        "heavy_vehicle_share",
        F.when(F.col("all_motor_vehicles") > 0, F.col("all_hgvs") / F.col("all_motor_vehicles")).otherwise(None),
    )
    return df


def select_columns(df: DataFrame) -> DataFrame:
    base_cols = [col for col in df.columns if col in ESSENTIAL_COLUMNS]
    additional_cols = [
        "event_timestamp",
        "year",
        "vehicles_per_km",
        "heavy_vehicle_share",
        "latitude",
        "longitude",
    ]
    selected = list(dict.fromkeys(base_cols + additional_cols))
    return df.select(*selected)


def main() -> None:
    args = parse_args()
    spark = get_spark()

    df = (
        spark.read.option("header", True)
        .option("inferSchema", False)
        .option("timestampFormat", "yyyy-MM-dd")
        .csv(args.input_path)
    )

    df = cast_numeric_columns(df)
    df = enrich_columns(df)

    for column in ESSENTIAL_COLUMNS:
        if column in df.columns:
            df = df.filter(F.col(column).isNotNull())

    df = select_columns(df)

    if args.repartition > 0:
        df = df.repartition(args.repartition)

    df.write.mode("overwrite").partitionBy(*args.partition_columns).parquet(args.output_path)


if __name__ == "__main__":
    main()
