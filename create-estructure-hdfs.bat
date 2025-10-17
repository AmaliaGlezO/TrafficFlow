@echo off
chcp 65001 >nul
echo ==================================================
echo    CREAR ESTRUCTURA DE DIRECTORIOS HDFS
echo ==================================================
echo.

echo Esperando que Hadoop se inicie completamente...
timeout /t 30 /nobreak >nul

echo 1. Creando estructura de directorios en HDFS...
docker exec hadoop-traffic hdfs dfs -mkdir -p /datasets/traffic/raw
docker exec hadoop-traffic hdfs dfs -mkdir -p /datasets/traffic/processed
docker exec hadoop-traffic hdfs dfs -mkdir -p /datasets/traffic/results
docker exec hadoop-traffic hdfs dfs -mkdir -p /input
docker exec hadoop-traffic hdfs dfs -mkdir -p /output

echo 2. Verificando estructura creada...
docker exec hadoop-traffic hdfs dfs -ls -R /datasets

echo 3. Moviendo archivo a la nueva estructura...
docker exec hadoop-traffic hdfs dfs -mv /input/traffic_data.csv /datasets/traffic/raw/

echo 4. Verificando archivo movido...
docker exec hadoop-traffic hdfs dfs -ls -R /datasets

echo.
echo ==================================================
echo    ESTRUCTURA CREADA EXITOSAMENTE
echo ==================================================
echo Directorios creados:
echo - /datasets/traffic/raw
echo - /datasets/traffic/processed  
echo - /datasets/traffic/results
echo - /input
echo - /output
echo.
pause