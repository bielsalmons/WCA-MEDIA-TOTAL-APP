import pandas as pd
import requests
import streamlit as st

# Configuración de página y título
st.title("🧩 Estadísticas WCA (3x3x3)")
st.write(
    "Introduce un WCA ID para obtener todas las solves oficiales y su media."
)


# Función con caché para optimizar las peticiones a la API
@st.cache_data(ttl=3600)
def obtener_datos_wca(wca_id_input):
    url = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/refs/heads/v1/persons/{wca_id_input}.json"
    respuesta = requests.get(url)
    if respuesta.status_code == 200:
        return respuesta.json()
    return None


# Entrada de texto para el WCA ID
wca_id = st.text_input("WCA ID:", value="").strip()

# Botón para activar la búsqueda
if st.button("Buscar") and wca_id:
    datos = obtener_datos_wca(wca_id)

    if datos:
        resultados = datos.get("results", {})
        filas = []

        for comp_id, eventos in resultados.items():
            if "333" in eventos:
                rondas = eventos["333"]
                for ronda in rondas:
                    nombre_ronda = ronda.get("round", "Desconocida")
                    solves_ronda = ronda.get("solves", [])

                    for tiempo in solves_ronda:
                        if tiempo > 0:
                            filas.append(
                                {
                                    "torneo": comp_id,
                                    "año": comp_id[-4:],
                                    "ronda": nombre_ronda,
                                    "tiempo_segundos": tiempo / 100.0,
                                }
                            )

        if filas:
            # Guardamos el DataFrame en la sesión activa de Streamlit
            st.session_state["df_solves"] = pd.DataFrame(filas)
        else:
            st.session_state["df_solves"] = None
            st.warning(
                "Este usuario no tiene solves válidas registradas en 3x3x3."
            )
    else:
        st.session_state["df_solves"] = None
        st.error(f"No se encontró el WCA ID '{wca_id}'.")

# Renderizado de los resultados si existen en el estado
if "df_solves" in st.session_state and st.session_state["df_solves"] is not None:
    df = st.session_state["df_solves"]
    total_solves = len(df)
    media_total = df["tiempo_segundos"].mean()

    # Métricas principales
    col1, col2 = st.columns(2)
    col1.metric("Solves encontradas", total_solves)
    col2.metric("Media oficial total", f"{media_total:.2f} s")

    # Muestra la tabla de tiempos
    st.dataframe(df, use_container_width=True)

    st.divider()

    # --- Contador de Solves Sub-X ---
    st.subheader("⏱️ Contador de Solves Sub-X")

    limite_tiempo = st.number_input(
        "Introduce un tiempo en segundos (ej. 6 para Sub-6):",
        min_value=0.0,
        max_value=100.0,
        value=6.0,
        step=0.5,
    )

    solves_sub = df[df["tiempo_segundos"] < limite_tiempo]
    cantidad_sub = len(solves_sub)

    st.success(
        f"🎯 **{cantidad_sub}** solves **Sub-{limite_tiempo:.2f}** registradas en la historia."
    )

    if cantidad_sub > 0:
        with st.expander(
            f"Ver detalles de las {cantidad_sub} solves Sub-{limite_tiempo:.2f}"
        ):
            st.dataframe(solves_sub, use_container_width=True)
        
