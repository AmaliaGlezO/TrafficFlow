# **Arquitectura del Sistema: Análisis de Movilidad Urbana con Hadoop/Spark**

## **Descripción General**
Esta arquitectura implementa un clúster Hadoop-Spark completamente containerizado para el procesamiento de grandes volúmenes de datos de movilidad urbana y GPS, específicamente diseñado para el proyecto de análisis de tráfico y optimización de rutas.

---

## **Componentes de la Arquitectura**

### **1. Namenode (Hadoop Master)**
```yaml
namenode:
  image: bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8
  container_name: namenode
  hostname: hadoop-master
  ports:
    - "9870:9870"  # UI HDFS
    - "9000:9000"  # Servicio HDFS
    - "8088:8088"  # YARN UI
```

**Función:** 
- **Metadatos de HDFS**: Gestiona el namespace del sistema de archivos y regula el acceso a los archivos por parte de los clientes.
- **Coordinación de Datanodes**: Supervisa el estado de los nodos de datos y replica bloques según sea necesario.

**Importancia para el Proyecto:**
- **Centralización de Datos GPS**: Todos los datos de movilidad (coordenadas, timestamps, velocidades) se almacenan de manera unificada.
- **Alta Disponibilidad**: Permite el acceso concurrente a datasets masivos de tráfico desde múltiples nodos de procesamiento.
- **Escalabilidad**: Facilita la incorporación de nuevos datasets de GPS sin interrumpir el sistema.

---

### **2. Datanodes (Hadoop Workers)**
```yaml
datanode1:
  image: bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8
  hostname: datanode1
  environment:
    - CORE_CONF_fs_defaultFS=hdfs://hadoop-master:9000
```

**Función:**
- **Almacenamiento Distribuido**: Almacenan los bloques reales de datos de HDFS.
- **Procesamiento Local**: Ejecutan tasks de MapReduce en los datos locales (principio de data locality).

**Importancia para el Proyecto:**
- **Distribución de Carga**: Los datos de GPS (que pueden ser terabytes de registros de ubicación) se distribuyen automáticamente.
- **Tolerancia a Fallos**: Replicación automática de datos de tráfico críticos.
- **Procesamiento Paralelo**: Análisis simultáneo de diferentes segmentos geográficos o temporales.

---

### **3. Spark Master**
```yaml
spark-master:
  image: bde2020/spark-master:3.0.0-hadoop3.2
  hostname: spark-master
  ports:
    - "8080:8080"  # Spark UI
    - "7077:7077"  # Spark Master
```

**Función:**
- **Coordinación de Recursos**: Gestiona la asignación de recursos del clúster Spark.
- **Orquestación de Jobs**: Coordina la ejecución de aplicaciones Spark distribuidas.

**Importancia para el Proyecto:**
- **Procesamiento en Memoria**: Acelera significativamente los algoritmos de análisis de rutas y patrones de movilidad.
- **Streaming en Tiempo Real**: Permite procesar flujos continuos de datos GPS para monitoreo en tiempo real.
- **MLlib Integration**: Facilita la implementación de modelos predictivos para tiempos de viaje.

---

### **4. Spark Worker**
```yaml
spark-worker:
  image: bde2020/spark-worker:3.0.0-hadoop3.2
  hostname: spark-worker
  environment:
    - SPARK_MASTER_URL=spark://spark-master:7077
```

**Función:**
- **Ejecución de Tasks**: Ejecuta las tareas de procesamiento asignadas por el Spark Master.
- **Cálculo Distribuido**: Realiza transformaciones y acciones sobre los datos distribuidos.

**Importancia para el Proyecto:**
- **Procesamiento Masivo Paralelo**: Capaz de procesar millones de registros GPS simultáneamente.
- **Análisis Geoespacial**: Ejecuta operaciones complejas de geolocalización en paralelo.
- **Agregaciones Temporales**: Calcula métricas de tráfico por intervalos de tiempo de forma distribuida.

---

## **Flujo de Datos en el Pipeline**

### **Arquitectura Propuesta:**
```
[Dataset GPS] → [HDFS Storage] → [Spark ETL] → [Análisis] → [Visualización]
     ↓              ↓               ↓            ↓            ↓
  Archivos       Namenode        Spark        Modelos      Dashboard
   CSV/JSON     + Datanodes     Workers      Predictivos   Tiempo Real
```

### **Enfoque: Combinación Batch + Streaming**
- **Batch**: Procesamiento histórico de datos para identificar patrones estacionales
- **Streaming**: Análisis en tiempo real para monitoreo activo de tráfico

---

## **Ventajas Específicas para Análisis de Movilidad**

### **1. Manejo de Grandes Volúmenes**
- **Escenario**: Datos GPS de flotas completas de vehículos (coordenadas cada 10-30 segundos)
- **Capacidad**: El clúster puede escalar horizontalmente añadiendo más datanodes

### **2. Procesamiento Geoespacial Eficiente**
- **Operaciones**: Cálculo de distancias, agrupamiento por zonas, detección de rutas frecuentes
- **Optimización**: Data locality minimiza transferencia de datos en la red

### **3. Tolerancia a Fallos Crítica**
- **Importancia**: Datos de movilidad urbana son valiosos para planificación ciudadana
- **Protección**: Replicación automática en múltiples nodos

### **4. Integración con Ecosistema Big Data**
- **Futuras Mejoras**: Posibilidad de integrar Kafka para streaming, Hive para consultas SQL
- **Flexibilidad**: Compatibilidad con herramientas de visualización como Tableau, Grafana

---

## **Próximos Pasos Arquitectónicos Recomendados**

1. **Implementar Kafka** para ingesta de datos GPS en tiempo real
2. **Agregar Hive** para consultas SQL sobre datos históricos
3. **Incorporar Grafana** para dashboards de visualización
4. **Configurar Airflow** para orquestación de pipelines ETL

Esta arquitectura proporciona una base sólida y escalable para el análisis de movilidad urbana, permitiendo desde procesamiento batch histórico hasta análisis en tiempo real de flujos vehiculares.
