#!/usr/bin/env python3
"""
Generador de datos de tráfico GPS de ejemplo
Ejecutar: python create-sample-data.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_traffic_data():
    """Genera datos simulados de tráfico GPS"""
    
    # Configuración
    n_records = 100000  # 100k registros para simular "big data"
    vehicles = [f"VEH_{i:05d}" for i in range(1, 1001)]  # 1000 vehículos
    routes = ["RUTA_A", "RUTA_B", "RUTA_C", "RUTA_D", "RUTA_E"]
    
    # Generar datos
    data = []
    start_time = datetime(2024, 1, 1, 6, 0, 0)
    
    for i in range(n_records):
        vehicle = np.random.choice(vehicles)
        route = np.random.choice(routes)
        
        # Coordenadas aproximadas de Bogotá
        latitude = 4.6 + np.random.uniform(-0.1, 0.1)
        longitude = -74.1 + np.random.uniform(-0.1, 0.1)
        
        # Velocidad simulada (km/h)
        speed = np.random.normal(30, 15)
        speed = max(0, min(120, speed))  # Límites realistas
        
        # Timestamp incremental
        timestamp = start_time + timedelta(minutes=i % 1440)
        
        data.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'vehicle_id': vehicle,
            'route_id': route,
            'latitude': round(latitude, 6),
            'longitude': round(longitude, 6),
            'speed_kmh': round(speed, 2),
            'engine_status': np.random.choice(['ACTIVE', 'IDLE', 'MOVING']),
            'fuel_level': round(np.random.uniform(10, 100), 1)
        })
    
    # Crear DataFrame
    df = pd.DataFrame(data)
    
    # Guardar como CSV
    filename = 'Data/dft_traffic_counts_raw_counts.csv'
    df.to_csv(filename, index=False)
    
    print(f"✅ Datos generados exitosamente: {filename}")
    print(f"📊 Total de registros: {len(df):,}")
    print(f"🚗 Vehículos únicos: {df['vehicle_id'].nunique()}")
    print(f"🕒 Rango temporal: {df['timestamp'].min()} a {df['timestamp'].max()}")
    print(f"💾 Tamaño del archivo: {len(df.to_csv(index=False)) / (1024*1024):.2f} MB")
    
    # Mostrar primeras filas
    print("\n📋 Primeras 5 filas:")
    print(df.head())

if __name__ == "__main__":
    generate_traffic_data()