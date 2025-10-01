# TrafficFlow: Análisis de Movilidad Urbana con Big Data

## 📋 Descripción del Proyecto

### Objetivo Central
**Analizar, predecir y visualizar patrones de tráfico en tiempo real e histórico** en la red vial de Gran Bretaña mediante procesamiento distribuido con Hadoop/Spark, con el fin de optimizar la movilidad urbana, identificar puntos críticos de congestión y proporcionar insights para la planificación del transporte.

### Dataset Seleccionado
- **Nombre:** DFT Road Traffic Counts
- **Fuente:** UK Department for Transport (DfT)
- **Formato:** CSV (745 MB, 4.3M registros, 32 columnas)
- **Enlace:** [DfT Road Traffic Statistics](https://www.gov.uk/government/statistical-data-sets/road-traffic-statistics)

### Justificación del Dataset

#### Volumen
- **4,337,137 registros** - volumen significativo que justifica el uso de Big Data
- **745 MB** de datos estructurados - ideal para distribución en HDFS
- **Datos horarios** durante múltiples años - permite análisis temporal complejo
- **Escalabilidad** demostrada para simular entornos de producción reales

#### Características
- **Atributos clave:** coordenadas GPS (lat/long), timestamp horario, volumen por tipo de vehículo, información geográfica detallada
- **Estructura temporal:** datos organizados por fecha, hora y ubicación
- **Categorías definidas:** 10 tipos de vehículos diferenciados, clasificación por región y autoridad local
- **Metadatos ricos:** longitud de enlaces, tipos de carretera, cruces de inicio/fin

#### Pertinencia
- **Relación directa** con el análisis de movilidad urbana
- **Permite múltiples enfoques:** espacial, temporal, predictivo
- **Ideal para** identificar patrones estacionales y de congestión
- **Base sólida** para extensiones en tiempo real

## 🏗️ Arquitectura Propuesta

### Diagrama del Pipeline

```mermaid
graph TB
    A[CSV Dataset DFT] --> B[HDFS Storage]
    B --> C[Spark Processing Engine]
    C --> D[Hive Metastore]
    C --> E[ML Models]
    D --> F[Visualization Dashboard]
    E --> F
    G[Kafka Streaming] --> C