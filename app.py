import pandas as pd
import requests
import streamlit as st

# Título y descripción
st.title("🧩 Calculadora de Media WCA (3x3x3)")
st.write(
    "Introduce un WCA ID para obtener todas las solves oficiales y su media."
)

# Entrada de texto para el WCA ID
wca_id = st.text_input("WCA ID:", value="").strip()

if st.button("Buscar") and wca_id:
    url = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/refs/heads/v1/persons/{wca_id}.json"
    respuesta = requests.get(url)

    if respuesta.status_code == 200:
        datos = respuesta.json()
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
            df = pd.DataFrame(filas)
            total_solves = len(df)
            media_total = df["tiempo_segundos"].mean()

            # Métricas en cajas grandes
            col1, col2 = st.columns(2)
            col1.metric("Solves encontradas", total_solves)
            col2.metric("Media oficial total", f"{media_total:.2f} s")

            # Mostrar tabla de datos
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("Este usuario no tiene solves válidas registradas en 3x3x3.")
    else:
        st.error(f"No se encontró el WCA ID '{wca_id}'.")
        