import re
import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Estadísticas WCA 3x3x3", page_icon="🧩", layout="wide"
)

st.title("🧩 Estadísticas Oficiales de 3x3x3")

# ==================== CONTROLES PRINCIPALES ====================
col_wca1, col_wca2 = st.columns(2)

with col_wca1:
    wca_id_1 = st.text_input("🔍 WCA ID 1 (Obligatorio):", placeholder="Ej: 2015GONZ08").strip().upper()

with col_wca2:
    wca_id_2 = st.text_input("🔍 WCA ID 2 (Opcional - para comparar):", placeholder="Ej: 2017KRAS05").strip().upper()

st.markdown("---")


@st.cache_data(ttl=3600)
def obtener_solves_wca(wca_id_input):
    if not wca_id_input:
        return None

    wca_id_clean = wca_id_input.strip().upper()
    url = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/refs/heads/v1/persons/{wca_id_clean}.json"

    try:
        respuesta = requests.get(url, timeout=10)
        if respuesta.status_code != 200:
            return None
        datos = respuesta.json()
    except requests.RequestException:
        return None

    results = datos.get("results", {})
    solves = []

    # Iteramos la estructura tal como viene en el JSON (las competiciones y rondas más recientes están primero)
    for comp, event in results.items():
        if "333" in event:
            rondas = event["333"]
            match_año = re.search(r"\d{4}$", comp)
            año = int(match_año.group()) if match_año else 0

            for ronda in rondas:
                nombre_ronda = ronda.get("round", "Desconocida")
                solves_ronda = ronda.get("solves", [])
                
                # Invertimos las solves de la ronda ([::-1]) para que la 5.ª solve (la última hecha) sea la primera
                for i, tiempo in enumerate(reversed(solves_ronda)):
                    if tiempo > 0:
                        num_solve_orig = len(solves_ronda) - i  # Identificador de la solve original (1 a 5)
                        solves.append(
                            {
                                "competición": comp,
                                "año": año,
                                "ronda": nombre_ronda,
                                "num_solve": f"Solve #{num_solve_orig}",
                                "solves segundos": tiempo / 100.0,
                            }
                        )

    if not solves:
        return pd.DataFrame()

    # El DataFrame ahora tiene la última solve de la última ronda al principio (index 0 = la más reciente)
    return pd.DataFrame(solves)


# Función para renderizar gráficos de líneas interactivos en Altair
def mostrar_grafico_lineas(df, titulo_eje_y="Valor"):
    df_reset = df.reset_index()
    nombre_col_index = df_reset.columns[0]

    df_melted = df_reset.melt(
        id_vars=[nombre_col_index], var_name="Competidor", value_name="Valor"
    ).rename(columns={nombre_col_index: "Año"})

    df_melted = df_melted.dropna(subset=["Valor"])

    selection = alt.selection_point(fields=["Competidor"], bind="legend")

    chart = (
        alt.Chart(df_melted)
        .mark_line(point=True)
        .encode(
            x=alt.X("Año:O", title="Año", sort=None),
            y=alt.Y("Valor:Q", title=titulo_eje_y),
            color=alt.Color(
                "Competidor:N",
                scale=alt.Scale(range=["#00B4D8", "#FF4B4B"]),
            ),
            opacity=alt.condition(selection, alt.value(1), alt.value(0.2)),
            tooltip=[
                alt.Tooltip("Año:O", title="Año"),
                alt.Tooltip("Competidor:N", title="Competidor"),
                alt.Tooltip("Valor:Q", title=titulo_eje_y, format=".2f"),
            ],
        )
        .add_params(selection)
        .properties(height=380)
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)


# ==================== CARGA DE DATOS ====================
df_comp1 = obtener_solves_wca(wca_id_1) if wca_id_1 else None
df_comp2 = obtener_solves_wca(wca_id_2) if wca_id_2 else None

if not wca_id_1:
    st.info(
        "👆 Introduce un WCA ID en la casilla superior para consultar y generar los gráficos."
    )
elif df_comp1 is None:
    st.error(
        f"No se pudo encontrar o cargar la información del WCA ID: **{wca_id_1}**"
    )
elif df_comp1.empty:
    st.warning(f"El competidor **{wca_id_1}** no tiene soluciones registradas en 3x3.")
else:
    tiene_comp2 = False
    if wca_id_2:
        if df_comp2 is None:
            st.error(f"No se encontró el WCA ID opcional: **{wca_id_2}**")
        elif df_comp2.empty:
            st.warning(f"**{wca_id_2}** no tiene soluciones registradas en 3x3.")
        else:
            tiene_comp2 = True

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Evolución de Medias", "⏱️ Tasa Sub-X", "⚡ Últimas N Solves (AoN)", "Variabilidad"])

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
            mostrar_grafico_lineas(
                df_grafico_medias_ordenado, titulo_eje_y="Media (s)"
            )
        else:
            st.line_chart(df_grafico_medias_ordenado)

        st.write("### 📋 Resumen Histórico por Año")

        if not tiene_comp2:
            resumen_medias = resumen_1.sort_index(ascending=False)
            total_solves_global = len(df_comp1)
            media_global = df_comp1["solves segundos"].mean()

            fila_total = pd.DataFrame(
                {
                    "media": [round(media_global, 2)],
                    "total_solves": [total_solves_global],
                },
                index=["Total General"],
            )

            resumen_medias.index = resumen_medias.index.astype(str)
            resumen_completo = pd.concat([resumen_medias, fila_total]).reset_index()
            resumen_completo = resumen_completo.rename(
                columns={
                    "index": "Año",
                    "media": "Media (s)",
                    "total_solves": "Soluciones Totales",
                }
            )
            resumen_completo["Media (s)"] = resumen_completo["Media (s)"].apply(
                lambda x: f"{x:.2f}"
            )
            st.dataframe(
                resumen_completo, hide_index=True, use_container_width=True
            )
        else:
            col_m1 = f"Media (s) ({wca_id_1})"
            col_s1 = f"Solves ({wca_id_1})"
            col_m2 = f"Media (s) ({wca_id_2})"
            col_s2 = f"Solves ({wca_id_2})"

            tabla_comp_medias = pd.DataFrame(
                {
                    col_m1: resumen_1["media"],
                    col_s1: resumen_1["total_solves"],
                    col_m2: resumen_2["media"],
                    col_s2: resumen_2["total_solves"],
                }
            )

            tabla_comp_medias = tabla_comp_medias.sort_index(ascending=False)
            tabla_comp_medias.index = tabla_comp_medias.index.astype(str)

            total_s1 = len(df_comp1)
            media_g1 = df_comp1["solves segundos"].mean()
            total_s2 = len(df_comp2)
            media_g2 = df_comp2["solves segundos"].mean()

            fila_total = pd.DataFrame(
                {
                    col_m1: [round(media_g1, 2)],
                    col_s1: [total_s1],
                    col_m2: [round(media_g2, 2)],
                    col_s2: [total_s2],
                },
                index=["Total General"],
            )

            tabla_completa = pd.concat([tabla_comp_medias, fila_total]).reset_index()
            tabla_completa = tabla_completa.rename(columns={"index": "Año"})

            cols_solves = [col_s1, col_s2]
            tabla_completa[cols_solves] = tabla_completa[cols_solves].fillna(0).astype(int)

            tabla_completa[col_m1] = tabla_completa[col_m1].apply(
                lambda x: f"{x:.2f}" if pd.notnull(x) else "-"
            )
            tabla_completa[col_m2] = tabla_completa[col_m2].apply(
                lambda x: f"{x:.2f}" if pd.notnull(x) else "-"
            )

            st.dataframe(
                tabla_completa, hide_index=True, use_container_width=True
            )

        st.markdown("---")
        st.caption(
            "ℹ️ **Nota:** Se calcula la media de todas las soluciones oficiales (excluyendo DNF's Y DNS's) de 3x3 por año."
        )

    # ==================== PESTAÑA 2 ====================
    with tab2:
        limite_tiempo = st.number_input(
            "Introduce un tiempo límite en segundos (ej. 10.0 para Sub-10):",
            min_value=0.0,
            max_value=100.0,
            value=10.0,
            step=0.5,
        )

        st.write(f"### ⏱️ Tasa de Solves Sub-{limite_tiempo:.2f} por Año")

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

        st.write(f"### 📈 Evolución de la Tasa Sub-{limite_tiempo:.2f} (%)")
        df_grafico_tasa = pd.DataFrame({f"{wca_id_1}": tasa_1["porcentaje"]})

        if tiene_comp2:
            tasa_2 = obtener_tasa_sub_x(df_comp2, limite_tiempo)
            df_grafico_tasa[f"{wca_id_2}"] = tasa_2["porcentaje"]

        df_grafico_tasa_ordenado = df_grafico_tasa.sort_index(ascending=True)
        df_grafico_tasa_ordenado.index = df_grafico_tasa_ordenado.index.astype(str)

        if tiene_comp2:
            mostrar_grafico_lineas(
                df_grafico_tasa_ordenado, titulo_eje_y="Tasa (%)"
            )
        else:
            st.line_chart(df_grafico_tasa_ordenado)

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

        st.write(f"### 📋 Tabla de Tasa Sub-{limite_tiempo:.2f} por Año")

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
            tabla_final["Tasa %"] = tabla_final["Tasa %"].apply(
                lambda x: f"{x:.2f}%"
            )

            tabla_estilizada = tabla_final.style.map(
                lambda v: "background-color: rgba(0, 180, 216, 0.2); font-weight: bold;",
                subset=["Tasa %"],
            )

            st.dataframe(
                tabla_estilizada, hide_index=True, use_container_width=True
            )

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
                    col_tasa1: tasa_1["porcentaje"],
                    col_sub2: tasa_2["solves_sub_x"],
                    col_tot2: tasa_2["total_solves"],
                    col_tasa2: tasa_2["porcentaje"],
                }
            )

            tabla_comp_tasa = tabla_comp_tasa.sort_index(ascending=False)
            tabla_comp_tasa.index = tabla_comp_tasa.index.astype(str)

            fila_total_tasa = pd.DataFrame(
                {
                    col_sub1: [sub_1],
                    col_tot1: [total_1],
                    col_tasa1: [round(pct_1, 2)],
                    col_sub2: [sub_2],
                    col_tot2: [total_2],
                    col_tasa2: [round(pct_2, 2)],
                },
                index=["Total Histórico"],
            )

            tabla_comp_tasa_completa = pd.concat([tabla_comp_tasa, fila_total_tasa]).reset_index()
            tabla_comp_tasa_completa = tabla_comp_tasa_completa.rename(columns={"index": "Año"})

            cols_enteras = [col_sub1, col_tot1, col_sub2, col_tot2]
            tabla_comp_tasa_completa[cols_enteras] = (
                tabla_comp_tasa_completa[cols_enteras].fillna(0).astype(int)
            )

            tabla_comp_tasa_completa[col_tasa1] = tabla_comp_tasa_completa[col_tasa1].apply(
                lambda x: f"{x:.2f}%" if pd.notnull(x) else "-"
            )
            tabla_comp_tasa_completa[col_tasa2] = tabla_comp_tasa_completa[col_tasa2].apply(
                lambda x: f"{x:.2f}%" if pd.notnull(x) else "-"
            )

            tabla_estilizada = tabla_comp_tasa_completa.style.map(
                lambda v: "background-color: rgba(0, 180, 216, 0.25); font-weight: bold;",
                subset=[col_tasa1],
            ).map(
                lambda v: "background-color: rgba(255, 75, 75, 0.25); font-weight: bold;",
                subset=[col_tasa2],
            )

            st.dataframe(
                tabla_estilizada, hide_index=True, use_container_width=True
            )

        solves_sub1 = df_comp1[df_comp1["solves segundos"] < limite_tiempo]
        if len(solves_sub1) > 0:
            with st.expander(
                f"Ver detalle de soluciones Sub-{limite_tiempo:.2f} ({wca_id_1})"
            ):
                st.dataframe(
                    solves_sub1[
                        ["competición", "ronda", "solves segundos"]
                    ],
                    hide_index=True,
                    use_container_width=True,
                )

        if tiene_comp2:
            solves_sub2 = df_comp2[df_comp2["solves segundos"] < limite_tiempo]
            if len(solves_sub2) > 0:
                with st.expander(
                    f"Ver detalle de soluciones Sub-{limite_tiempo:.2f} ({wca_id_2})"
                ):
                    st.dataframe(
                        solves_sub2[
                            ["competición", "ronda", "solves segundos"]
                        ],
                        hide_index=True,
                        use_container_width=True,
                    )

        st.markdown("---")
        st.caption(
            f"ℹ️ **Nota:** Se calcula el porcentaje de soluciones sub-{limite_tiempo:.2f} respecto al "
            f"total de solves válidas (no DNF, no DNS) de cada año."
        )
    # ==================== PESTAÑA 3 ====================
    with tab3:
        st.write("### ⚡ Media de las Últimas N Soluciones Oficiales (AoN)")

        tamano_n = st.selectbox(
            "Selecciona la cantidad de soluciones recientes a promediar (N):",
            options=[12, 25, 50, 100, 500, 1000],
            index=1,
        )

        st.markdown(f"#### 📊 Resultados para las Últimas {tamano_n} Soluciones (Ao{tamano_n})")

        # Como el DataFrame ya está en orden inverso exacto, tomamos los primeros N elementos con .head(N)
        df_recientes_1 = df_comp1.head(tamano_n)
        solves_contadas_1 = len(df_recientes_1)

        if not tiene_comp2:
            if solves_contadas_1 < tamano_n:
                st.warning(
                    f"⚠️ **{wca_id_1}** solo tiene **{solves_contadas_1}** soluciones registradas en total."
                )

            media_n_1 = df_recientes_1["solves segundos"].mean()

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric(
                    label=f"Media de {tamano_n} (Últimas {solves_contadas_1} solves)",
                    value=f"{media_n_1:.2f} s",
                )
            with col_m2:
                st.metric(
                    label="Mejor tiempo de la media",
                    value=f"{df_recientes_1['solves segundos'].min():.2f} s",
                )

            with st.expander(
                f"📋 Ver detalle de las {solves_contadas_1} solves (de más reciente a más antigua)"
            ):
                st.dataframe(
                    df_recientes_1[["competición", "solves segundos"]],
                    hide_index=True,
                    use_container_width=True,
                )

        else:
            df_recientes_2 = df_comp2.head(tamano_n)
            solves_contadas_2 = len(df_recientes_2)

            media_n_1 = df_recientes_1["solves segundos"].mean()
            media_n_2 = df_recientes_2["solves segundos"].mean()

            col_a, col_b = st.columns(2)

            with col_a:
                st.write(f"**Competidor 1 ({wca_id_1})**")
                if solves_contadas_1 < tamano_n:
                    st.warning(f"Tiene {solves_contadas_1}/{tamano_n} soluciones.")
                st.metric(
                    label=f"Media Ao{tamano_n}",
                    value=f"{media_n_1:.2f} s",
                )

            with col_b:
                st.write(f"**Competidor 2 ({wca_id_2})**")
                if solves_contadas_2 < tamano_n:
                    st.warning(f"Tiene {solves_contadas_2}/{tamano_n} soluciones.")
                st.metric(
                    label=f"Media Ao{tamano_n}",
                    value=f"{media_n_2:.2f} s",
                )

            tabla_aon = pd.DataFrame(
                {
                    "Competidor": [wca_id_1, wca_id_2],
                    f"Media Ao{tamano_n} (s)": [f"{media_n_1:.2f}", f"{media_n_2:.2f}"],
                    "Soluciones Usadas": [solves_contadas_1, solves_contadas_2],
                    "Mejor Tiempo en el Bloque (s)": [
                        f"{df_recientes_1['solves segundos'].min():.2f}",
                        f"{df_recientes_2['solves segundos'].min():.2f}",
                    ],
                }
            )

            st.write("#### 📋 Comparativa Directa")
            st.dataframe(tabla_aon, hide_index=True, use_container_width=True)

            with st.expander(f"📋 Ver detalle de las {solves_contadas_1} solves ({wca_id_1})"):
                st.dataframe(
                    df_recientes_1[["competición", "solves segundos"]],
                    hide_index=True,
                    use_container_width=True,
                )

            with st.expander(f"📋 Ver detalle de las {solves_contadas_2} solves ({wca_id_2})"):
                st.dataframe(
                    df_recientes_2[["competición", "solves segundos"]],
                    hide_index=True,
                    use_container_width=True,
                )

        st.markdown("---")
        st.caption(
            f"ℹ️ **Nota:** se calcula la media de las "
            f"últimas {tamano_n} soluciones válidas (no DNF no DNS)."
        )
        # ==================== PESTAÑA DE VARIABILIDAD ====================
    with tab4:

        def calcular_variabilidad_anual(df):
            if df.empty:
                return pd.DataFrame()
            
            df_temp = df.copy()
            
            # Agrupamos por año y calculamos media, desviación estándar y varianza
            resumen = df_temp.groupby("año")["solves segundos"].agg(
                media="mean",
                desviacion="std",
                varianza="var",
                solves_totales="count"
            )
            
            # Coeficiente de variación: (Desviación / Media) * 100
            resumen["cv_porcentaje"] = (resumen["desviacion"] / resumen["media"]) * 100
            return resumen

        var_1 = calcular_variabilidad_anual(df_comp1)

        # --- GRÁFICO DE EVOLUCIÓN ---
        st.write("### 📈 Evolución del Coeficiente de Variación (%)")
        st.caption("Un porcentaje más bajo indica mayor consistencia en los tiempos.")
        
        df_grafico_var = pd.DataFrame({f"{wca_id_1}": var_1["cv_porcentaje"]})

        if tiene_comp2:
            var_2 = calcular_variabilidad_anual(df_comp2)
            df_grafico_var[f"{wca_id_2}"] = var_2["cv_porcentaje"]

        df_grafico_var_ordenado = df_grafico_var.sort_index(ascending=True)
        df_grafico_var_ordenado.index = df_grafico_var_ordenado.index.astype(str)

        if tiene_comp2:
            mostrar_grafico_lineas(
                df_grafico_var_ordenado, titulo_eje_y="Coef. Variación (%)"
            )
        else:
            st.line_chart(df_grafico_var_ordenado)

        # --- TABLAS DE RESUMEN ---
        st.write("### 📋 Tabla de Variabilidad por Año")

        if not tiene_comp2:
            var_1_desc = var_1.sort_index(ascending=False).copy()
            var_1_desc.index = var_1_desc.index.astype(str)
            tabla_final_var = var_1_desc.reset_index()

            tabla_final_var = tabla_final_var.rename(
                columns={
                    "año": "Año",
                    "media": "Media (s)",
                    "desviacion": "Desv. Estándar (s)",
                    "varianza": "Varianza (s²)",
                    "cv_porcentaje": "Coef. Variación (%)",
                    "solves_totales": "Solves Totales",
                }
            )

            # Formato de decimales
            tabla_final_var["Media (s)"] = tabla_final_var["Media (s)"].apply(lambda x: f"{x:.2f}")
            tabla_final_var["Desv. Estándar (s)"] = tabla_final_var["Desv. Estándar (s)"].apply(lambda x: f"{x:.2f}")
            tabla_final_var["Varianza (s²)"] = tabla_final_var["Varianza (s²)"].apply(lambda x: f"{x:.2f}")
            tabla_final_var["Coef. Variación (%)"] = tabla_final_var["Coef. Variación (%)"].apply(lambda x: f"{x:.2f}%")

            st.dataframe(tabla_final_var, hide_index=True, use_container_width=True)

        else:
            col_cv1 = f"CV % ({wca_id_1})"
            col_std1 = f"Desv (s) ({wca_id_1})"
            col_cv2 = f"CV % ({wca_id_2})"
            col_std2 = f"Desv (s) ({wca_id_2})"

            tabla_comp_var = pd.DataFrame({
                col_cv1: var_1["cv_porcentaje"],
                col_std1: var_1["desviacion"],
                col_cv2: var_2["cv_porcentaje"],
                col_std2: var_2["desviacion"],
            })

            tabla_comp_var = tabla_comp_var.sort_index(ascending=False).reset_index()
            tabla_comp_var = tabla_comp_var.rename(columns={"año": "Año"})
            tabla_comp_var["Año"] = tabla_comp_var["Año"].astype(str)

            tabla_comp_var[col_std1] = tabla_comp_var[col_std1].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "-")
            tabla_comp_var[col_std2] = tabla_comp_var[col_std2].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "-")
            tabla_comp_var[col_cv1] = tabla_comp_var[col_cv1].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")
            tabla_comp_var[col_cv2] = tabla_comp_var[col_cv2].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

            st.dataframe(tabla_comp_var, hide_index=True, use_container_width=True)

        st.markdown("---")
        st.caption(
            "ℹ️ **Nota:** El **Coeficiente de Variación (CV)** expresa la desviación estándar como porcentaje de la media. "
            "Permite comparar la consistencia entre competidores."
        )
