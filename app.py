import pandas as pd
import requests
import streamlit as st

st.title("Evolución de Medias 3x3x3 WCA")
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
                solves_ronda = ronda.get("solves", [])
                for tiempo in solves_ronda:
                    if tiempo > 0:
                        año = comp[-4:]
                        solves.append({
                            "competición": comp,
                            "año": int(año),
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

        # 5. Pasamos el índice (Años/Total) a una columna llamada "Año"
        resumen_completo = resumen_completo.reset_index()

        # 6. Renombramos las columnas
        resumen_completo = resumen_completo.rename(columns={
            "index": "Año",
            "media": "Media",
            "total_solves": "Soluciones totales"
        })

        # 7. Formateamos la media a 2 decimales fijos
        resumen_completo["Media"] = resumen_completo["Media"].apply(lambda x: f"{x:.2f}")

        # 8. Mostramos la tabla (ocultando los índices numéricos por defecto) y el gráfico
        st.write("### Resumen histórico de medias por año:")
        st.dataframe(resumen_completo, hide_index=True)

        st.write("### Evolución de la media por años:")
        st.line_chart(datos_grafico["media"])









