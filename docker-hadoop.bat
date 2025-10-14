@echo off
chcp 65001 >nul
echo ==================================================
echo    HADOOP CON PUERTOS ALTOS (SOLUCION DEFINITIVA)
echo ==================================================
echo.

echo 1. Limpiando contenedores anteriores...
docker stop hadoop-traffic 2>nul
docker rm hadoop-traffic 2>nul

echo 2. Usando puertos altos (menos conflictivos)...
echo Puerto 50070 -> 51000
echo Puerto 8088  -> 51001
echo Puerto 9000  -> 51002

echo 3. Creando contenedor...
docker run -itd -p 51000:50070 -p 51001:8088 -p 51002:9000 --name hadoop-traffic kiwenlau/hadoop:1.0

if %errorlevel% neq 0 (
    echo ❌ Error grave de puertos
    echo.
    echo SOLUCIONES MANUALES:
    echo 1. Reinicia Docker Desktop
    echo 2. Ejecuta PowerShell como Administrador
    echo 3. Reinicia tu computadora
    pause
    exit /b 1
)

echo 4. Esperando inicio (25 segundos)...
timeout /t 25 /nobreak >nul

echo 5. Verificando contenedor...
docker ps | find "hadoop-traffic" >nul
if %errorlevel% neq 0 (
    echo ❌ Contenedor no iniciado
    echo Verificando estado...
    docker ps -a | find "hadoop-traffic"
    pause
    exit /b 1
)

echo ✅ Contenedor ejecutandose correctamente

echo 6. Configurando HDFS...
docker exec hadoop-traffic hdfs dfs -mkdir -p /input
docker exec hadoop-traffic hdfs dfs -mkdir -p /output
docker exec hadoop-traffic hdfs dfs -mkdir -p /scripts

echo.
echo ==================================================
echo    ¡HADOOP LISTO CON PUERTOS ALTOS!
echo ==================================================
echo.
echo URLs de acceso:
echo - HDFS NameNode: http://localhost:51000
echo - YARN ResourceManager: http://localhost:51001
echo.
echo Para acceder: docker exec -it hadoop-traffic bash
echo.
pause