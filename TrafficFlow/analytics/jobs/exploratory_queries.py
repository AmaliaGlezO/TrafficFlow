"""Initial analytical queries over the curated traffic dataset."""
from __future__ import annotations

import argparse
import logging
import sys
from typing import List

from pyspark.sql import SparkSession
from pyspark.sql.window import Window
from pyspark.sql import functions as F

LOGGER = logging.getLogger("trafficflow.queries")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exploratory analytics on TrafficFlow silver data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input-path", required=True, help="Input Parquet path in HDFS (silver zone)")
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of rows to display for ranking queries",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    spark = SparkSession.builder.appName("TrafficFlowExploratoryQueries").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    LOGGER.info("Reading curated dataset from %s", args.input_path)
    df = spark.read.parquet(args.input_path)
    df.createOrReplaceTempView("traffic")

    LOGGER.info("Daily totals by road type")
    daily_by_road = (
        df.groupBy("event_date", "road_type")
        .agg(F.sum("total_motor_traffic").alias("vehicles"))
        .orderBy(F.desc("event_date"), F.desc("vehicles"))
    )
    daily_by_road.show(args.top_n, truncate=False)

    LOGGER.info("Top regions by heavy goods share")
    hgvs_share = (
        df.groupBy("region_name")
        .agg(
            F.avg("heavy_goods_share").alias("avg_hgvs_share"),
            F.sum("total_motor_traffic").alias("total_flow"),
        )
        .filter("total_flow > 0")
        .orderBy(F.desc("avg_hgvs_share"))
    )
    hgvs_share.show(args.top_n, truncate=False)

    LOGGER.info("Peak hour demand by local authority")
    windowed = (
        df.groupBy("local_authority_name", "event_hour")
        .agg(F.sum("total_motor_traffic").alias("vehicles"))
        .withColumn(
            "rank",
            F.dense_rank().over(
                Window.partitionBy("local_authority_name").orderBy(F.desc("vehicles"))
            ),
        )
        .filter(F.col("rank") == 1)
        .orderBy(F.desc("vehicles"))
    )
    windowed.select("local_authority_name", "event_hour", "vehicles").show(args.top_n, truncate=False)

    LOGGER.info("Exploratory queries completed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
