@echo off
chcp 65001 >nul
echo ==================================================
echo    SUBIR DATOS DE TRAFICO A HDFS
echo ==================================================
echo.

echo Buscando archivos en carpeta Data...
dir Data\*.csv

echo.
echo USANDO ARCHIVO PRINCIPAL: dft_traffic_counts_raw_counts.csv
echo.

set FILE_PATH=Data\dft_traffic_counts_raw_counts.csv

if not exist "%FILE_PATH%" (
    echo ERROR: El archivo no existe en: %FILE_PATH%
    echo.
    echo Creando lista de archivos disponibles...
    if exist Data (
        echo Archivos en Data:
        dir Data\*.csv /B
    )
    if exist *.csv (
        echo Archivos en carpeta principal:
        dir *.csv /B
    )
    echo.
    pause
    exit /b 1
)

echo ✅ Archivo encontrado: %FILE_PATH%
echo.

echo 1. Verificando Docker...
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker no esta ejecutandose
    echo Inicia Docker Desktop primero
    pause
    exit /b 1
)

echo 2. Copiando archivo al contenedor...
docker cp "%FILE_PATH%" hadoop-traffic:/root/traffic_data.csv

if errorlevel 1 (
    echo ERROR: No se pudo copiar al contenedor
    echo Verificando contenedores...
    docker ps -a
    echo.
    echo Si el contenedor no existe, ejecuta: docker-hadoop-setup.bat
    pause
    exit /b 1
)

echo 3. Subiendo archivo a HDFS...
docker exec hadoop-traffic hdfs dfs -put -f /root/traffic_data.csv /input/

echo 4. Verificando...
echo === CONTENIDO DE HDFS ===
docker exec hadoop-traffic hdfs dfs -ls /input/

echo.
echo === INFORMACION DEL ARCHIVO ===
docker exec hadoop-traffic hdfs dfs -count /input/traffic_data.csv

echo.
echo ✅ ¡EXITO! Datos subidos a HDFS correctamente
echo.
echo Puedes verificar en la interfaz web: http://localhost:50070
echo.
pause