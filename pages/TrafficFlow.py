import streamlit as st
from Analisis_exploratorio import analisis_exploratorio
from Mapas_estaticos import mapas_estaticos
from Zonas_criticas import zonas_criticas
# from Patrones_temporales import patrones_temporales


def main():
    # Configuración de página
    st.set_page_config(
        page_title="Análisis de Movilidad Urbana",
        page_icon="🚦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS personalizado
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1E88E5;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # HEADER PRINCIPAL
    st.markdown('<h1 class="main-header">🚦 Análisis de Movilidad Urbana - Fase 1</h1>', unsafe_allow_html=True)
    
    # SIDEBAR - Navegación y Filtros Globales
    with st.sidebar:
        st.title("Navegación")
        
        st.subheader("Filtros Globales")
        fecha_inicio = st.date_input("Fecha inicial")
        fecha_fin = st.date_input("Fecha final")
        zona_seleccionada = st.selectbox("Zona de análisis", ["Toda la ciudad", "Norte", "Sur", "Este", "Oeste"])
        
        st.divider()
        st.info("**Equipo:** Diego & Amalia")
        st.info("**Dataset:** Road Traffic - Kaggle")
    
    # SECCIÓN: MÉTRICAS PRINCIPALES
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="📊 Total de Registros",
            value="4,000,000+",
            delta="100K procesados"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="🚗 Velocidad Promedio",
            value="45 km/h",
            delta="-5% vs promedio"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="⚠️ Zonas Críticas",
            value="15",
            delta="+2 esta semana"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="⏰ Hora Pico",
            value="7:00-9:00 AM",
            delta="Principal congestión"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # SECCIÓN: VISUALIZACIONES RÁPIDAS
    st.divider()
    st.subheader("📈 Vista Rápida del Análisis")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.info("**Mapa de Calor de Congestión**")
        # ESPACIO PARA IMPLEMENTACIÓN: Mapa de calor estático
        st.write("🔘 **Aquí irá el mapa de calor** con las zonas más congestionadas")
        st.write("• Zonas rojas: Alta congestión")
        st.write("• Zonas verdes: Fluidez vehicular")
        st.write("• Círculos: Puntos de medición")
    
    with col_right:
        st.info("**Evolución Horaria del Tráfico**")
        # ESPACIO PARA IMPLEMENTACIÓN: Gráfico de líneas temporal
        st.write("📊 **Aquí irá el gráfico temporal** de volumen vehicular")
        st.write("• Línea azul: Volumen actual")
        st.write("• Área gris: Rango histórico")
        st.write("• Puntos rojos: Horas pico identificadas")
    
    # SECCIÓN: ACCESO RÁPIDO A MÓDULOS
    st.divider()
    st.subheader("🔍 Módulos de Análisis Disponibles")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Análisis Exploratorio", 
        "🗺️ Mapas Estáticos", 
        "🔍 Zonas Críticas", 
        "📈 Patrones Temporales"
    ])
    
    with tab1:
        st.write("**Análisis completo de calidad de datos y distribuciones**")
        if st.button("Ir al Análisis Exploratorio →", use_container_width=True, key = "btn_ae"):
            analisis_exploratorio()
    
    with tab2:
        st.write("**Visualización geoespacial de datos de tráfico**")
        if st.button("Ir a Mapas Estáticos →", use_container_width=True, key="btn_mapas"):
            mapas_estaticos()
            
    
    with tab3:
        st.write("**Identificación y análisis de zonas problemáticas**")
        if st.button("Ir a Zonas Críticas →", use_container_width=True, key = "btn_zc" ):
            zonas_criticas()
    
    with tab4:
        st.write("**Patrones horarios, diarios y semanales**")
        st.button("Ir a Patrones Temporales →", use_container_width=True)

if __name__ == "__main__":
    main()