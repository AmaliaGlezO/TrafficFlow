# Informe Semi-proyecto: Análisis de Movilidad Urbana

## 1. Descripción del Proyecto
Analizar patrones de movilidad urbana mediante datos GPS históricos para predecir congestionamientos y optimizar rutas vehiculares. El objetivo final es desarrollar un sistema de recomendación de rutas que evite zonas críticas de tráfico.

Nombre: Road Traffic Dataset

Fuente: Kaggle

Formato: CSV (datos temporales y geoespaciales)

Características clave:

Timestamps (minuto a minuto)

Coordenadas GPS/ubicaciones de sensores

Volumen vehicular por intervalo temporal

Velocidades promedio

Identificación de segmentos viales

Volumen:
+1 millón de registros mensuales (simula "Grandes Volúmenes de Datos")

Cobertura temporal extensa (múltiples meses/años)

Escalabilidad: Permite procesamiento distribuido con HDFS/Spark

Características:
Atributos clave: timestamp, coordenadas, volumen vehicular, velocidad, tipo de vía

Temporalidad: Datos en intervalos de 1-5 minutos

Etiquetas: Segmentos viales identificados, tipos de vehículos

Ruido: Datos GPS incompletos que requieren limpieza

Pertinencia:
Relación directa con el objetivo: Los datos de volumen y velocidad permiten identificar patrones de congestión

Preparación para fase 2: La estructura temporal facilita la transición a análisis en tiempo real

Capacidad geoespacial: Ideal para mapas de calor y análisis de flujos

## 2. Arquitectura Propuesta
graph TD
    A[Fuente de Datos<br/>Road Traffic Dataset] --> B[HDFS<br/>Almacenamiento distribuido];
    B --> C[Spark DataFrames<br/>Limpieza y transformación];
    C --> D[Análisis Exploratorio<br/>Estadísticas y patrones];
    D --> E[Feature Engineering<br/>Preparación para ML];
    E --> F[Modelado Batch<br/>Entrenamiento de modelos];
    F --> G[Visualizaciones Estáticas<br/>Mapas de calor batch];
    C --> H[Spark Streaming<br/>Preparación tiempo real];
    H --> I[Kafka<br/>Streaming de datos];
    I --> J[Visualizaciones Tiempo Real<br/>Fase 2];
    
    style G fill:#e1f5fe
    style J fill:#f3e5f5

## 3. Avances Logrados
### 3.1 Infraestructura
- HDFS configurado y operativo
- Spark/PySpark instalado
- Subset de datos cargado (ejemplo: 100,000 registros)

### 3.2 Procesamiento de Datos
- Script de limpieza implementado
- Transformaciones geoespaciales aplicadas
- Ejemplo de consultas Spark SQL ejecutadas

### 3.3 Resultados Preliminares
- Tablas con estadísticas básicas
- Capturas de pantalla de primeros análisis
- Ejemplo de mapa de calor estático

## 4. Preparación para Fase 2
- Diseño de arquitectura de streaming
- Plan de implementación para visualizaciones en tiempo real
