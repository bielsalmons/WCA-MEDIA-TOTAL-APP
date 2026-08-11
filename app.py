import altair as alt
import pandas as pd
import requests
import streamlit as st

st.title("🧩 Estadísticas oficiales de 3x3x3")

# ==================== BARRA LATERAL (ENTRADAS) ====================
st.sidebar.header("🔍 Buscar Competidores")
wca_id_1 = st.sidebar.text_input("WCA ID 1 (Obligatorio):").strip().upper()
wca_id_2 = st.sidebar.text_input("WCA ID 2 (Opcional):").strip().upper()


@st.cache_data
def obtener_solves_wca(wca_id_input):
    if not wca_id_input:
        return None

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
                        solves.append(
                            {
                                "competición": comp,
                                "año": int(año),
                                "ronda": nombre_ronda,
                                "solves segundos": tiempo / 100.0,
                            }
                        )

    if not solves:
        return pd.DataFrame()

    return pd.DataFrame(solves)


# Función para renderizar gráficos de líneas sin fallos de índice/melt
def mostrar_grafico_lineas(df, titulo_eje_y="Valor"):
    df_reset = df.reset_index()
    nombre_col_index = df_reset.columns[0]

    df_melted = df_reset.melt(
        id_vars=[nombre_col_index], var_name="Competidor", value_name="Valor"
    ).rename(columns={nombre_col_index: "Año"})

    chart = (
        alt.Chart(df_melted)
        .mark_line(point=True)
        .encode(
            x=alt.X("Año:N", sort=None, title="Año"),
            y=alt.Y("Valor:Q", title=titulo_eje_y),
            color=alt.Color(
                "Competidor:N",
                scale=alt.Scale(range=["#00B4D8", "#FF4B4B"]),
            ),
            tooltip=["Año", "Competidor", "Valor"],
        )
        .properties(height=350)
    )

    st.altair_chart(chart, use_container_width=True)


# ==================== CARGA DE DATOS ====================
df_comp1 = obtener_solves_wca(wca_id_1) if wca_id_1 else None
df_comp2 = obtener_solves_wca(wca_id_2) if wca_id_2 else None

if not wca_id_1:
    st.info("👈 Por favor, introduce al menos un WCA ID en la barra lateral para empezar.")
elif df_comp1 is None:
    st.error(f"No se encontró el WCA ID: **{wca_id_1}**")
elif df_comp1.empty:
    st.warning(f"El competidor **{wca_id_1}** no tiene solves registradas en 3x3.")
else:
    tiene_comp2 = False
    if wca_id_2:
        if df_comp2 is None:
            st.sidebar.error(f"No se encontró el WCA ID opcional: {wca_id_2}")
        elif df_comp2.empty:
            st.sidebar.warning(f"{wca_id_2} no tiene solves en 3x3.")
        else:
            tiene_comp2 = True

    tab1, tab2 = st.tabs(["📊 Evolución de Medias", "⏱️ Tasa sub-X"])

    # ==================== PESTAÑA 1 ====================
    with tab1:
        st.write("### 📊 Evolución de la Media por Años")

        resumen_1 = (
            df_comp1.groupby("año")["solves segundos"]
            .agg(media="mean", total_solves="count")
            .round(2)
        )

        df_grafico_medias = pd.DataFrame({wca_id_1: resumen_1["media"]})

        if tiene_comp2:
            resumen_2 = (
                df_comp2.groupby("año")["solves segundos"]
                .agg(media="mean", total_solves="count")
                .round(2)
            )
            df_grafico_medias[wca_id_2] = resumen_2["media"]

        df_grafico_medias_ordenado = df_grafico_medias.sort_index(ascending=True)
        df_grafico_medias_ordenado.index = df_grafico_medias_ordenado.index.astype(str)

        if tiene_comp2:
            mostrar_grafico_lineas(df_grafico_medias_ordenado, titulo_eje_y="Media (s)")
        else:
            st.line_chart(df_grafico_medias_ordenado)

        st.write("### 📋 Resumen histórico por año")

        if not tiene_comp2:
            resumen_medias = resumen_1.sort_index(ascending=False)
            total_solves_global = len(df_comp1)
            media_global = df_comp1["solves segundos"].mean()

            fila_total = pd.DataFrame(
                {"media": [round(media_global, 2)], "total_solves": [total_solves_global]},
                index=["Total General"],
            )

            resumen_medias.index = resumen_medias.index.astype(str)
            resumen_completo = pd.concat([resumen_medias, fila_total]).reset_index()
            resumen_completo = resumen_completo.rename(
                columns={
                    "index": "Año",
                    "media": "Media",
                    "total_solves": "Soluciones totales",
                }
            )
            resumen_completo["Media"] = resumen_completo["Media"].apply(
                lambda x: f"{x:.2f}"
            )
            st.dataframe(resumen_completo, hide_index=True, use_container_width=True)
        else:
            tabla_comp = df_grafico_medias.sort_index(ascending=False).reset_index()
            tabla_comp = tabla_comp.rename(columns={"año": "Año"})
            st.dataframe(tabla_comp, hide_index=True, use_container_width=True)

        # Nota aclaratoria al final del Tab 1
        st.markdown("---")
        st.caption(
            "ℹ️ **Nota:** Se calcula la media de todas las soluciones oficiales de 3x3 "
            "(excluyendo los DNF y los DNS) por año (incluye las soluciones de las finales head to head)."
        )

    # ==================== PESTAÑA 2 ====================
    with tab2:
        st.write("### ⏱️ Tasa de Solves Sub-X por Año")

        limite_tiempo = st.number_input(
            "Introduce un tiempo límite en segundos (ej. 10.0 para Sub-10):",
            min_value=0.0,
            max_value=100.0,
            value=10.0,
            step=0.5,
        )

        def obtener_tasa_sub_x(df, limite):
            df_temp = df.copy()
            df_temp["es_sub_x"] = df_temp["solves segundos"] < limite
            tasa = df_temp.groupby("año").agg(
                solves_sub_x=("es_sub_x", "sum"), total_solves=("es_sub_x", "count")
            )
            tasa["porcentaje"] = (
                (tasa["solves_sub_x"] / tasa["total_solves"]) * 100
            ).round(2)
            return tasa

        tasa_1 = obtener_tasa_sub_x(df_comp1, limite_tiempo)

        # 1. Gráfico
        st.write("### 📈 Evolución de la Tasa Sub-X (%)")
        df_grafico_tasa = pd.DataFrame({f"{wca_id_1}": tasa_1["porcentaje"]})

        if tiene_comp2:
            tasa_2 = obtener_tasa_sub_x(df_comp2, limite_tiempo)
            df_grafico_tasa[f"{wca_id_2}"] = tasa_2["porcentaje"]

        df_grafico_tasa_ordenado = df_grafico_tasa.sort_index(ascending=True)
        df_grafico_tasa_ordenado.index = df_grafico_tasa_ordenado.index.astype(str)

        if tiene_comp2:
            mostrar_grafico_lineas(df_grafico_tasa_ordenado, titulo_eje_y="Tasa (%)")
        else:
            st.line_chart(df_grafico_tasa_ordenado)

        # 2. Resumen rápido en cajas
        st.write("### 🎯 Totales Históricos")
        sub_1 = (df_comp1["solves segundos"] < limite_tiempo).sum()
        total_1 = len(df_comp1)
        pct_1 = (sub_1 / total_1 * 100) if total_1 > 0 else 0

        if tiene_comp2:
            sub_2 = (df_comp2["solves segundos"] < limite_tiempo).sum()
            total_2 = len(df_comp2)
            pct_2 = (sub_2 / total_2 * 100) if total_2 > 0 else 0

            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label=f"Competidor: {wca_id_1}",
                    value=f"{sub_1} / {total_1} ({pct_1:.2f}%)",
                )
            with col2:
                st.metric(
                    label=f"Competidor: {wca_id_2}",
                    value=f"{sub_2} / {total_2} ({pct_2:.2f}%)",
                )
        else:
            st.success(
                f"🎯 **{wca_id_1}** tiene en total **{sub_1}** solves Sub-{limite_tiempo:.2f} "
                f"de **{total_1}** totales (**{pct_1:.2f}%**)."
            )

        # 3. Tabla con resaltado de columnas
        st.write("### 📋 Tabla de Tasa Sub-X por Año")

        if not tiene_comp2:
            fila_total = pd.DataFrame(
                {
                    "solves_sub_x": [sub_1],
                    "total_solves": [total_1],
                    "porcentaje": [round(pct_1, 2)],
                },
                index=["Total Histórico"],
            )

            tasa_1_desc = tasa_1.sort_index(ascending=False)
            tasa_1_desc.index = tasa_1_desc.index.astype(str)

            tabla_final = pd.concat([tasa_1_desc, fila_total]).reset_index()
            tabla_final = tabla_final.rename(
                columns={
                    "index": "Año",
                    "solves_sub_x": f"Solves Sub-{limite_tiempo:.2f}",
                    "total_solves": "Solves Totales",
                    "porcentaje": "Tasa %",
                }
            )
            tabla_final["Tasa %"] = tabla_final["Tasa %"].apply(lambda x: f"{x:.2f}%")

            tabla_estilizada = tabla_final.style.map(
                lambda v: "background-color: rgba(0, 180, 216, 0.2); font-weight: bold;",
                subset=["Tasa %"],
            )

            st.dataframe(tabla_estilizada, hide_index=True, use_container_width=True)

        else:
            col_sub1 = f"Sub-{limite_tiempo:.2f} ({wca_id_1})"
            col_tot1 = f"Totales ({wca_id_1})"
            col_tasa1 = f"Tasa % ({wca_id_1})"

            col_sub2 = f"Sub-{limite_tiempo:.2f} ({wca_id_2})"
            col_tot2 = f"Totales ({wca_id_2})"
            col_tasa2 = f"Tasa % ({wca_id_2})"

            tabla_comp_tasa = pd.DataFrame(
                {
                    col_sub1: tasa_1["solves_sub_x"],
                    col_tot1: tasa_1["total_solves"],
                    col_tasa1: tasa_1["porcentaje"].apply(lambda x: f"{x:.2f}%"),
                    col_sub2: tasa_2["solves_sub_x"],
                    col_tot2: tasa_2["total_solves"],
                    col_tasa2: tasa_2["porcentaje"].apply(lambda x: f"{x:.2f}%"),
                }
            )

            # Convertimos las columnas de conteo a enteros limpios sin decimales
            cols_enteras = [col_sub1, col_tot1, col_sub2, col_tot2]
            tabla_comp_tasa[cols_enteras] = (
                tabla_comp_tasa[cols_enteras].fillna(0).astype(int)
            )

            tabla_comp_tasa = (
                tabla_comp_tasa.sort_index(ascending=False)
                .reset_index()
                .rename(columns={"año": "Año"})
            )

            tabla_comp_tasa = tabla_comp_tasa.rename(columns={"año": "Año"})

            tabla_estilizada = tabla_comp_tasa.style.map(
                lambda v: "background-color: rgba(0, 180, 216, 0.25); font-weight: bold;",
                subset=[col_tasa1],
            ).map(
                lambda v: "background-color: rgba(255, 75, 75, 0.25); font-weight: bold;",
                subset=[col_tasa2],
            )

            st.dataframe(tabla_estilizada, hide_index=True, use_container_width=True)

        # 4. Desplegables
        solves_sub1 = df_comp1[df_comp1["solves segundos"] < limite_tiempo]
        if len(solves_sub1) > 0:
            with st.expander(
                f"Ver detalle de soluciones Sub-{limite_tiempo:.2f} ({wca_id_1})"
            ):
                st.dataframe(
                    solves_sub1[["competición", "año", "ronda", "solves segundos"]],
                    hide_index=True,
                )

        if tiene_comp2:
            solves_sub2 = df_comp2[df_comp2["solves segundos"] < limite_tiempo]
            if len(solves_sub2) > 0:
                with st.expander(
                    f"Ver detalle de soluciones Sub-{limite_tiempo:.2f} ({wca_id_2})"
                ):
                    st.dataframe(
                        solves_sub2[["competición", "año", "ronda", "solves segundos"]],
                        hide_index=True,
                    )

        # Nota aclaratoria al final del Tab 2
        st.markdown("---")
        st.caption(
            f"ℹ️ **Nota:** Se calcula el número de soluciones sub {limite_tiempo:.2f} entre el total "
            f"de solves de un año multiplicado por 100 para calcular el porcentaje."
        )








