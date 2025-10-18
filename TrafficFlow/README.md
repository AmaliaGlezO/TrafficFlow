# TrafficFlow Distributed Pipeline

This repository provides a minimal Hadoop + Spark environment together with PySpark jobs to ingest the Department for Transport traffic counts dataset, generate distributed synthetic traffic measurements, and run simple cleaning and analytical queries.

## Requirements

- Docker 24+
- Docker Compose v2
- Python 3.12+ (only for local helper scripts, Spark runs inside Docker)
- Dataset files placed under `data/raw` (see below)

## Project layout

```
TrafficFlow/
  analytics/
    jobs/
      distributed_producer.py   # Structured Streaming producer (Spark on YARN)
      data_cleaning.py          # Batch cleaning job
      exploratory_queries.py    # Basic analytical queries
  data/
    raw/                        # Place the CSV sources here
    checkpoints/                # Structured Streaming checkpoints
  docs/
    report.tex                  # Project documentation (LaTeX)
  docker-compose.yml            # Hadoop + Spark stack
  README.md
```

## Getting started

1. Copy the dataset files into `data/raw/`. The expected filenames are:
   - `dft_traffic_counts_raw_counts.csv`
   - `local_authority_traffic.csv`
   - `region_traffic.csv`

2. Bootstrap the cluster:

   ```powershell
   docker compose up -d
   ```

3. Once the cluster is healthy, load the raw counts dataset into HDFS:

   ```powershell
   docker compose exec namenode hdfs dfs -mkdir -p /data/raw
   docker compose exec namenode hdfs dfs -put -f /data/raw/dft_traffic_counts_raw_counts.csv /data/raw/
   docker compose exec namenode hdfs dfs -put -f /data/raw/local_authority_traffic.csv /data/raw/
   docker compose exec namenode hdfs dfs -put -f /data/raw/region_traffic.csv /data/raw/
   ```

## Streaming producer (1500 rows per minute)

The producer runs as a Spark Structured Streaming job on YARN. It repeatedly samples the raw dataset, applies stochastic perturbations to mimic realistic traffic flow, and writes the generated records to HDFS in Parquet format.

```powershell
$rowsPerSecond = 25            # 25 rows/s ≈ 1500 rows/min
$checkpointDir = "/data/checkpoints/trafficflow-producer"
$outputDir = "/data/bronze/trafficflow"

# Ensure the output and checkpoint directories exist in HDFS once per environment
docker compose exec namenode hdfs dfs -mkdir -p $checkpointDir
docker compose exec namenode hdfs dfs -mkdir -p $outputDir

docker compose exec spark-master \
  spark-submit \
    --master yarn \
    --deploy-mode client \
    --conf spark.sql.shuffle.partitions=4 \
    /opt/spark-apps/distributed_producer.py \
    --input-path hdfs:///data/raw/dft_traffic_counts_raw_counts.csv \
    --checkpoint-path hdfs://namenode:8020$checkpointDir \
    --output-path hdfs://namenode:8020$outputDir \
    --rows-per-second $rowsPerSecond \
    --sample-size 100000 \
    --variation-scale 0.18
```

The `jobs.zip` archive is built automatically by the container entrypoint and bundles the shared helper code.

> The job keeps running until it is manually stopped. Use `docker compose exec spark-master bash` and press `Ctrl+C` to terminate it gracefully.

## Batch cleaning job

After generating data, run the cleaning batch job to move the synthetic bronze data into a curated silver zone:

```powershell
docker compose exec spark-master \
  spark-submit \
    --master yarn \
    --deploy-mode client \
    /opt/spark-apps/data_cleaning.py \
    --input-path hdfs:///data/bronze/trafficflow \
    --output-path hdfs:///data/silver/trafficflow
```

## Exploratory queries

Execute first analytical queries for validation and reporting:

```powershell
docker compose exec spark-master \
  spark-submit \
    --master yarn \
    --deploy-mode client \
    /opt/spark-apps/exploratory_queries.py \
    --input-path hdfs:///data/silver/trafficflow
```

The script prints aggregated metrics (daily volumes by road type, top congested regions, etc.) to stdout.

## Monitoring endpoints

- HDFS NameNode UI: http://localhost:9870
- YARN ResourceManager UI: http://localhost:8088
- Spark Master UI: http://localhost:8080
- Spark Worker UI: http://localhost:8081
- MapReduce Job History: http://localhost:8188
- TrafficFlow Monitoring Console: http://localhost:8501

Start the monitoring console separately if needed:

```powershell
docker compose up -d monitoring
```

## Stopping the platform

```powershell
docker compose down -v
```

This removes the containers and persistent volumes. Generated data in HDFS will be discarded; copy it out beforehand if you need to keep it.
