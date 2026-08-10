import pandas as pd
import requests
import streamlit as st

st.title("🧩 Estadísticas oficiales de 3x3x3")
wca_id = st.text_input("Escribe un WCA ID:")

@st.cache_data
def obtener_solves_wca(wca_id_input):
    wca_id_clean = wca_id_input.strip().upper()
    URL = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/refs/heads/v1/persons/{wca_id_clean}.json"
    respuesta = requests.get(URL)
    
    if respuesta.status_code != 200:
        return None
        
    datos = respuesta.json()
    results = datos.get("results", {})
    solves = []
    
    for comp, event in results.items():
        if "333" in event:
            rondas = event["333"] 
            for ronda in rondas:
                nombre_ronda = ronda.get("round", "Desconocida")
                solves_ronda = ronda.get("solves", [])
                for tiempo in solves_ronda:
                    if tiempo > 0:
                        año = comp[-4:]
                        solves.append({
                            "competición": comp,
                            "año": int(año),
                            "ronda": nombre_ronda,
                            "solves segundos": tiempo / 100.0
                        })
                        
    if not solves:
        return pd.DataFrame()
        
    return pd.DataFrame(solves)

if wca_id:
    df_resultado = obtener_solves_wca(wca_id)
    
    if df_resultado is None:
        st.error("No se encontró ese WCA ID.")
    elif df_resultado.empty:
        st.warning("Ese competidor no tiene solves registradas en 3x3.")
    else:
        # Creamos 2 pestañas distintas
        tab1, tab2 = st.tabs(["📊 Evolución de Medias", "⏱️ Solves Sub-X"])

        # ==================== PESTAÑA 1 ====================
        with tab1:
            # 1. Agrupamos por año
            resumen_medias = (
                df_resultado.groupby("año")["solves segundos"]
                .agg(media="mean", total_solves="count")
                .round(2)
                .sort_index(ascending=False)
            )

            # 2. Guardamos datos del gráfico (orden cronológico y años como texto)
            datos_grafico = resumen_medias.sort_index(ascending=True)
            datos_grafico.index = datos_grafico.index.astype(str)

            # 3. Calculamos totales globales
            total_solves_global = len(df_resultado)
            media_global = df_resultado["solves segundos"].mean()

            # 4. Creamos fila "Total General"
            fila_total = pd.DataFrame(
                {"media": [round(media_global, 2)], "total_solves": [total_solves_global]},
                index=["Total General"]
            )
            
            resumen_medias.index = resumen_medias.index.astype(str)
            resumen_completo = pd.concat([resumen_medias, fila_total])

            # 5. Pasamos el índice a columna y renombramos
            resumen_completo = resumen_completo.reset_index()
            resumen_completo = resumen_completo.rename(columns={
                "index": "Año",
                "media": "Media",
                "total_solves": "Soluciones totales"
            })

            # 6. Formateamos la media a 2 decimales fijos
            resumen_completo["Media"] = resumen_completo["Media"].apply(lambda x: f"{x:.2f}")

            # 7. Mostramos la tabla y el gráfico
            st.write("### Resumen histórico de medias por año:")
            st.dataframe(resumen_completo, hide_index=True)

            st.write("### Evolución de la media por años:")
            st.line_chart(datos_grafico["media"])

        # ==================== PESTAÑA 2 ====================
        with tab2:
            st.write("### Contador de Solves Sub-X")
            
            limite_tiempo = st.number_input(
                "Introduce un tiempo en segundos (ej. 6.0 para Sub-6):",
                min_value=0.0,
                max_value=100.0,
                value=6.0,
                step=0.5,
            )

            solves_sub = df_resultado[df_resultado["solves segundos"] < limite_tiempo]
            cantidad_sub = len(solves_sub)

            st.success(
                f"🎯 **{cantidad_sub}** solves **Sub-{limite_tiempo:.2f}** registradas en la historia."
            )

            if cantidad_sub > 0:
                with st.expander(f"Ver detalles de las {cantidad_sub} solves Sub-{limite_tiempo:.2f}"):
                    st.dataframe(solves_sub, hide_index=True)









