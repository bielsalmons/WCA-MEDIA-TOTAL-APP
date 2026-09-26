import re
import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Estadísticas Oficiales WCA", page_icon="🧩", layout="wide"
)

st.title("🧩 Estadísticas Oficiales WCA")

NOMBRES_EVENTOS = {
    "222": "2x2x2 Cube",
    "333": "3x3x3 Cube",
    "444": "4x4x4 Cube",
    "555": "5x5x5 Cube",
    "666": "6x6x6 Cube",
    "777": "7x7x7 Cube",
    "333bf": "3x3x3 Blindfolded",
    "333fm": "3x3x3 Fewest Moves",
    "333oh": "3x3x3 One-Handed",
    "clock": "Clock",
    "minx": "Megaminx",
    "pyram": "Pyraminx",
    "skewb": "Skewb",
    "sq1": "Square-1",
    "444bf": "4x4x4 Blindfolded",
    "555bf": "5x5x5 Blindfolded",
}

# ==================== FUNCIÓN DE BÚSQUEDA Y VALIDACIÓN ====================
def resolver_wca_id(busqueda_input, label_prefix=""):
    busqueda_clean = busqueda_input.strip()
    if not busqueda_clean:
        return None

    if (
        len(busqueda_clean) == 10
        and busqueda_clean[:4].isdigit()
        and busqueda_clean[4:8].isalpha()
        and busqueda_clean[8:].isdigit()
    ):
        return busqueda_clean.upper()
    else:
        url_search = f"https://www.worldcubeassociation.org/api/v0/search/users?q={busqueda_clean}"
        resp_search = requests.get(url_search)

        if resp_search.status_code == 200:
            resultados = resp_search.json().get("result", [])
            personas = [u for u in resultados if u.get("wca_id") is not None]

            if personas:
                opciones = {f"{p['name']} ({p['wca_id']})": p["wca_id"] for p in personas}
                persona_elegida = st.selectbox(
                    f"Coincidencias encontradas para {label_prefix}:",
                    options=list(opciones.keys()),
                    key=f"select_{label_prefix}"
                )
                return opciones[persona_elegida]
            else:
                st.warning(f"No se encontraron competidores para '{busqueda_clean}'.")
                return None
    return None

def obtener_nombre_competidor(wca_id_target):
    if not wca_id_target:
        return ""
    url = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/refs/heads/v1/persons/{wca_id_target}.json"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            d = r.json()
            return d.get("name", wca_id_target)
    except Exception:
        pass
    return wca_id_target

# ==================== CONTROLES PRINCIPALES ====================
col_wca1, col_wca2 = st.columns(2)

with col_wca1:
    input_1 = st.text_input("🔍 Competidor 1 (WCA ID o Nombre):", placeholder="Ej: 2015GONZ08 o Carlos").strip()
    wca_id_1 = resolver_wca_id(input_1, "Competidor 1") if input_1 else None

with col_wca2:
    input_2 = st.text_input("🔍 Competidor 2 (Opcional - WCA ID o Nombre):", placeholder="Ej: 2017KRAS05 o Alex").strip()
    wca_id_2 = resolver_wca_id(input_2, "Competidor 2") if input_2 else None

eventos_disponibles = ["333"]
datos_persona_1 = None
nombre_1 = obtener_nombre_competidor(wca_id_1) if wca_id_1 else ""
nombre_2 = obtener_nombre_competidor(wca_id_2) if wca_id_2 else ""

if wca_id_1:
    url_p1 = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/refs/heads/v1/persons/{wca_id_1}.json"
    r1 = requests.get(url_p1)
    if r1.status_code == 200:
        datos_persona_1 = r1.json()
        df_avg1 = pd.json_normalize(datos_persona_1, record_path=["rank", "averages"], meta="name") if "rank" in datos_persona_1 and "averages" in datos_persona_1["rank"] else pd.DataFrame()
        df_sgl1 = pd.json_normalize(datos_persona_1, record_path=["rank", "singles"], meta="name") if "rank" in datos_persona_1 and "singles" in datos_persona_1["rank"] else pd.DataFrame()
        
        ev_avg = df_avg1["eventId"].tolist() if not df_avg1.empty else []
        ev_sgl = df_sgl1["eventId"].tolist() if not df_sgl1.empty else []
        lista_evs = sorted([e for e in set(ev_avg + ev_sgl) if e in NOMBRES_EVENTOS])
        if lista_evs:
            eventos_disponibles = lista_evs

evento_elegido = st.selectbox(
    "🧩 Selecciona el Evento a analizar:",
    options=eventos_disponibles,
    format_func=lambda x: NOMBRES_EVENTOS.get(x, x),
)

st.markdown("---")

# ==================== EXTRACCIÓN DE SOLVES POR EVENTO ====================
@st.cache_data(ttl=3600)
def obtener_solves_wca_evento(wca_id_clean, event_id):
    if not wca_id_clean:
        return None

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

    for comp, event in results.items():
        if event_id in event:
            rondas = event[event_id]
            match_año = re.search(r"\d{4}$", comp)
            año = int(match_año.group()) if match_año else 0

            for ronda in rondas:
                nombre_ronda = ronda.get("round", "Desconocida")
                solves_ronda = ronda.get("solves", [])
                
                for i, tiempo in enumerate(reversed(solves_ronda)):
                    if tiempo > 0:
                        num_solve_orig = len(solves_ronda) - i
                        valor_final = float(tiempo) if event_id == "333fm" else tiempo / 100.0
                        solves.append(
                            {
                                "competición": comp,
                                "año": año,
                                "ronda": nombre_ronda,
                                "num_solve": f"Solve #{num_solve_orig}",
                                "solves segundos": valor_final,
                            }
                        )

    if not solves:
        return pd.DataFrame()

    return pd.DataFrame(solves)


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
df_comp1 = obtener_solves_wca_evento(wca_id_1, evento_elegido) if wca_id_1 else None
df_comp2 = obtener_solves_wca_evento(wca_id_2, evento_elegido) if wca_id_2 else None

unidad_medida = "movs" if evento_elegido == "333fm" else "s"

if not wca_id_1:
    st.info("👆 Introduce un WCA ID o Nombre en la casilla superior para comenzar.")
elif df_comp1 is None:
    st.error(f"No se pudo cargar la información del WCA ID: **{wca_id_1}**")
else:
    tiene_comp2 = False
    if wca_id_2:
        if df_comp2 is None:
            st.error(f"No se encontró el WCA ID opcional: **{wca_id_2}**")
        elif df_comp2.empty:
            st.warning(f"**{nombre_2}** no tiene soluciones registradas en {NOMBRES_EVENTOS.get(evento_elegido, evento_elegido)}.")
        else:
            tiene_comp2 = True

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Evolución de Medias", 
        "⏱️ Tasa Sub-X", 
        "⚡ Medias de N (AoN)", 
        "📉 Variabilidad", 
        "🏆 Top Mundial"
    ])

    # ==================== PESTAÑA 1 ====================
    with tab1:
        st.write(f"### 📊 Evolución de la Media por Años ({NOMBRES_EVENTOS.get(evento_elegido, evento_elegido)})")

        if df_comp1.empty:
            st.warning(f"El competidor **{nombre_1}** no tiene soluciones registradas en este evento.")
        else:
            resumen_1 = (
                df_comp1.groupby("año")["solves segundos"]
                .agg(media="mean", total_solves="count")
                .round(2)
            )

            df_grafico_medias = pd.DataFrame({nombre_1: resumen_1["media"]})

            if tiene_comp2 and not df_comp2.empty:
                resumen_2 = (
                    df_comp2.groupby("año")["solves segundos"]
                    .agg(media="mean", total_solves="count")
                    .round(2)
                )
                df_grafico_medias[nombre_2] = resumen_2["media"]

            df_grafico_medias_ordenado = df_grafico_medias.sort_index(ascending=True)
            df_grafico_medias_ordenado.index = df_grafico_medias_ordenado.index.astype(str)

            if tiene_comp2:
                mostrar_grafico_lineas(df_grafico_medias_ordenado, titulo_eje_y=f"Media ({unidad_medida})")
            else:
                st.line_chart(df_grafico_medias_ordenado)

            st.write("### 📋 Resumen Histórico por Año")

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
                    columns={"index": "Año", "media": f"Media ({unidad_medida})", "total_solves": "Soluciones Totales"}
                )
                resumen_completo[f"Media ({unidad_medida})"] = resumen_completo[f"Media ({unidad_medida})"].apply(lambda x: f"{x:.2f}")
                st.dataframe(resumen_completo, hide_index=True, use_container_width=True)
            else:
                col_m1, col_s1 = f"Media ({unidad_medida}) ({nombre_1})", f"Solves ({nombre_1})"
                col_m2, col_s2 = f"Media ({unidad_medida}) ({nombre_2})", f"Solves ({nombre_2})"

                tabla_comp_medias = pd.DataFrame({
                    col_m1: resumen_1["media"],
                    col_s1: resumen_1["total_solves"],
                    col_m2: resumen_2["media"] if tiene_comp2 else None,
                    col_s2: resumen_2["total_solves"] if tiene_comp2 else None,
                }).sort_index(ascending=False)

                tabla_comp_medias.index = tabla_comp_medias.index.astype(str)
                st.dataframe(tabla_comp_medias.reset_index().rename(columns={"index": "Año"}), hide_index=True, use_container_width=True)

            st.caption("📌 **Nota:** Esta gráfica y tabla muestran la media aritmética global de todos los resultados válidos registrados en competiciones oficiales de la WCA para este evento año a año.")

    # ==================== PESTAÑA 2 ====================
    with tab2:
        val_def = 30.0 if evento_elegido == "333fm" else 10.0
        limite_tiempo = st.number_input(
            f"Introduce un límite en {unidad_medida} (ej. {val_def:.1f} para Sub-{val_def:.0f}):",
            min_value=0.0, max_value=300.0, value=val_def, step=0.5,
        )

        st.write(f"### ⏱️ Tasa de Solves Sub-{limite_tiempo:.2f} por Año")

        def obtener_tasa_sub_x(df, limite):
            if df.empty:
                return pd.DataFrame()
            df_temp = df.copy()
            df_temp["es_sub_x"] = df_temp["solves segundos"] < limite
            tasa = df_temp.groupby("año").agg(
                solves_sub_x=("es_sub_x", "sum"), total_solves=("es_sub_x", "count")
            )
            tasa["porcentaje"] = (tasa["solves_sub_x"] / tasa["total_solves"]) * 100
            return tasa

        if not df_comp1.empty:
            tasa_1 = obtener_tasa_sub_x(df_comp1, limite_tiempo)
            df_grafico_tasa = pd.DataFrame({f"{nombre_1}": tasa_1["porcentaje"]})

            if tiene_comp2 and not df_comp2.empty:
                tasa_2 = obtener_tasa_sub_x(df_comp2, limite_tiempo)
                df_grafico_tasa[f"{nombre_2}"] = tasa_2["porcentaje"]

            df_grafico_tasa_ordenado = df_grafico_tasa.sort_index(ascending=True)
            df_grafico_tasa_ordenado.index = df_grafico_tasa_ordenado.index.astype(str)

            if tiene_comp2:
                mostrar_grafico_lineas(df_grafico_tasa_ordenado, titulo_eje_y="Tasa (%)")
            else:
                st.line_chart(df_grafico_tasa_ordenado)

            # --- VISTA ESTILO CAPTURA "TOTALES HISTÓRICOS" ---
            st.write("### 🎯 Totales Históricos")
            sub_1 = (df_comp1["solves segundos"] < limite_tiempo).sum()
            total_1 = len(df_comp1)
            pct_1 = (sub_1 / total_1 * 100) if total_1 > 0 else 0

            if tiene_comp2 and not df_comp2.empty:
                sub_2 = (df_comp2["solves segundos"] < limite_tiempo).sum()
                total_2 = len(df_comp2)
                pct_2 = (sub_2 / total_2 * 100) if total_2 > 0 else 0

                c1, c2 = st.columns(2)
                with c1:
                    st.caption(f"Competidor: {nombre_1}")
                    st.markdown(f"## **{sub_1} / {total_1} ({pct_1:.2f}%)**")
                with c2:
                    st.caption(f"Competidor: {nombre_2}")
                    st.markdown(f"## **{sub_2} / {total_2} ({pct_2:.2f}%)**")
            else:
                st.caption(f"Competidor: {nombre_1}")
                st.markdown(f"## **{sub_1} / {total_1} ({pct_1:.2f}%)**")

            st.write("")

            # --- TABLA DE TASA SUB-X CON COLORES ---
            st.write("### 📋 Tabla de Tasa Sub-X por Año")
            if not tiene_comp2:
                tasa_tabla = tasa_1.sort_index(ascending=False).reset_index()
                tasa_tabla.columns = ["Año", f"Solves Sub-{limite_tiempo:.2f}", "Solves Totales", "% Tasa"]
                tasa_tabla["% Tasa"] = tasa_tabla["% Tasa"] / 100.0
                
                styled_df = tasa_tabla.style.format({"% Tasa": "{:.2%}"}).background_gradient(
                    cmap="Blues", subset=["% Tasa"]
                )
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
            else:
                tasa_tabla_comp = pd.DataFrame({
                    f"Sub-{limite_tiempo:.2f} ({nombre_1})": tasa_1["solves_sub_x"],
                    f"% ({nombre_1})": tasa_1["porcentaje"] / 100.0,
                    f"Sub-{limite_tiempo:.2f} ({nombre_2})": tasa_2["solves_sub_x"] if tiene_comp2 else None,
                    f"% ({nombre_2})": (tasa_2["porcentaje"] / 100.0) if tiene_comp2 else None,
                }).sort_index(ascending=False).reset_index()
                tasa_tabla_comp = tasa_tabla_comp.rename(columns={"año": "Año"})

                cols_pct = [f"% ({nombre_1})", f"% ({nombre_2})"]
                styled_df = tasa_tabla_comp.style.format({c: "{:.2%}" for c in cols_pct}).background_gradient(
                    cmap="Blues", subset=cols_pct
                )
                st.dataframe(styled_df, hide_index=True, use_container_width=True)

            # --- DESPLEGABLE CON DETALLE DE SOLUCIONES SUB-X ---
            with st.expander(f"🔍 Ver detalle de soluciones Sub-{limite_tiempo:.2f}"):
                if tiene_comp2:
                    col_det1, col_det2 = st.columns(2)
                    with col_det1:
                        st.write(f"**Soluciones Sub-{limite_tiempo:.2f} - {nombre_1}**")
                        df_sub1 = df_comp1[df_comp1["solves segundos"] < limite_tiempo][["competición", "año", "ronda", "num_solve", "solves segundos"]].copy()
                        df_sub1.columns = ["Competición", "Año", "Ronda", "Solve", f"Tiempo ({unidad_medida})"]
                        df_sub1[f"Tiempo ({unidad_medida})"] = df_sub1[f"Tiempo ({unidad_medida})"].apply(lambda x: f"{x:.2f}")
                        st.dataframe(df_sub1, hide_index=True, use_container_width=True)
                    with col_det2:
                        st.write(f"**Soluciones Sub-{limite_tiempo:.2f} - {nombre_2}**")
                        df_sub2 = df_comp2[df_comp2["solves segundos"] < limite_tiempo][["competición", "año", "ronda", "num_solve", "solves segundos"]].copy()
                        df_sub2.columns = ["Competición", "Año", "Ronda", "Solve", f"Tiempo ({unidad_medida})"]
                        df_sub2[f"Tiempo ({unidad_medida})"] = df_sub2[f"Tiempo ({unidad_medida})"].apply(lambda x: f"{x:.2f}")
                        st.dataframe(df_sub2, hide_index=True, use_container_width=True)
                else:
                    st.write(f"**Soluciones Sub-{limite_tiempo:.2f} - {nombre_1}**")
                    df_sub1 = df_comp1[df_comp1["solves segundos"] < limite_tiempo][["competición", "año", "ronda", "num_solve", "solves segundos"]].copy()
                    df_sub1.columns = ["Competición", "Año", "Ronda", "Solve", f"Tiempo ({unidad_medida})"]
                    df_sub1[f"Tiempo ({unidad_medida})"] = df_sub1[f"Tiempo ({unidad_medida})"].apply(lambda x: f"{x:.2f}")
                    st.dataframe(df_sub1, hide_index=True, use_container_width=True)

            st.caption("📌 **Nota:** El porcentaje representa la proporción de soluciones registradas por debajo del umbral indicado frente al total de soluciones en competiciones ese año.")

    # ==================== PESTAÑA 3 ====================
    with tab3:
        st.write("### ⚡ Actual y mejor media de N soluciones")

        tamano_n = st.selectbox(
            "Selecciona la cantidad de soluciones consecutivas a promediar (N):",
            options=[5, 12, 25, 50, 100, 500, 1000], index=0,
        )

        def calcular_media_bloque(serie_tiempos):
            if len(serie_tiempos) != tamano_n:
                return None
            if tamano_n == 5:
                tiempos_ordenados = sorted(serie_tiempos)
                return sum(tiempos_ordenados[1:4]) / 3.0
            else:
                return serie_tiempos.mean()

        def obtener_metricas_aon(df, n):
            if df.empty or len(df) < n:
                return None, None, None, None, None, None, len(df)

            df_recientes = df.head(n).copy()
            media_actual = calcular_media_bloque(df_recientes["solves segundos"])
            single_act = df_recientes["solves segundos"].min() if not df_recientes.empty else None

            df_cronologico = df.iloc[::-1].reset_index(drop=True)
            mejor_media_historica = float("inf")
            idx_mejor_bloque = -1

            for i in range(len(df_cronologico) - n + 1):
                bloque = df_cronologico.iloc[i : i + n]["solves segundos"]
                media_bloque = calcular_media_bloque(bloque)
                if media_bloque is not None and media_bloque < mejor_media_historica:
                    mejor_media_historica = media_bloque
                    idx_mejor_bloque = i

            if idx_mejor_bloque != -1:
                df_mejor_bloque = df_cronologico.iloc[idx_mejor_bloque : idx_mejor_bloque + n].copy()
                df_mejor_bloque = df_mejor_bloque.iloc[::-1].reset_index(drop=True)
                mejor_single_bloque = df_mejor_bloque["solves segundos"].min()
            else:
                df_mejor_bloque = pd.DataFrame()
                mejor_media_historica = None
                mejor_single_bloque = None

            return media_actual, single_act, mejor_media_historica, mejor_single_bloque, df_recientes, df_mejor_bloque, len(df)

        def renderizar_tarjeta_aon_individual(titulo_tipo, media_val, single_val, n_val, es_mejor=False):
            med_str = f"{media_val:.2f}{unidad_medida}" if media_val is not None else "N/A"
            sgl_str = f"{single_val:.2f}{unidad_medida}" if single_val is not None else "N/A"
            border_color = "#FFD700" if es_mejor else "#00B4D8"
            glow_gradient = "linear-gradient(180deg, #FFE57F 0%, #D4AF37 100%)" if es_mejor else "linear-gradient(180deg, #90E0EF 0%, #00B4D8 100%)"

            st.markdown(f"""
            <div style="background: radial-gradient(circle at top left, #1A1A1A 0%, #0D0D0D 100%); border: 1px solid #333333; border-left: 5px solid {border_color}; border-radius: 12px; padding: 18px 22px; margin-bottom: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.6); color: white;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 12px; font-weight: 800; color: {border_color}; letter-spacing: 1.5px; text-transform: uppercase;">
                            {titulo_tipo} (Ao{n_val})
                        </span>
                        <div style="font-size: 13px; color: #A0A0A0; margin-top: 6px;">
                            Mejor Single del bloque: <b style="color: #FFFFFF;">{sgl_str}</b>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 10px; color: #A0A0A0; letter-spacing: 1.2px; text-transform: uppercase; font-weight: 600;">Media</div>
                        <div style="font-size: 32px; font-weight: 900; background: {glow_gradient}; -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                            {med_str}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        def mostrar_tabla_solves(df_bloque, titulo):
            if df_bloque is not None and not df_bloque.empty:
                with st.expander(f"📋 {titulo}"):
                    tabla_fmt = df_bloque[["competición", "año", "ronda", "num_solve", "solves segundos"]].copy()
                    tabla_fmt.columns = ["Competición", "Año", "Ronda", "Solve", f"Tiempo ({unidad_medida})"]
                    tabla_fmt[f"Tiempo ({unidad_medida})"] = tabla_fmt[f"Tiempo ({unidad_medida})"].apply(lambda x: f"{x:.2f}")
                    st.dataframe(tabla_fmt, hide_index=True, use_container_width=True)

        def procesar_y_mostrar_bloque_competidor(nombre_target, df_target, n_val, mostrar_cabecera=True):
            med_act, sgl_act, mej_med, mej_sgl, df_rec, df_mej, tot_solves = obtener_metricas_aon(df_target, n_val)
            
            if tot_solves < n_val:
                st.warning(f"**{nombre_target}** necesita al menos {n_val} soluciones (tiene {tot_solves}).")
                return None
            else:
                if mostrar_cabecera:
                    st.subheader(f"Competidor: {nombre_target}")
                
                renderizar_tarjeta_aon_individual("Media Actual", med_act, sgl_act, n_val, es_mejor=False)
                mostrar_tabla_solves(df_rec, f"Tiempos de la Media Actual (Últimas {n_val})")

                renderizar_tarjeta_aon_individual("🏆 Mejor Media Histórica", mej_med, mej_sgl, n_val, es_mejor=True)
                mostrar_tabla_solves(df_mej, f"Tiempos de la Mejor Media (Ao{n_val})")
                
                return {
                    "med_act": med_act, "sgl_act": sgl_act,
                    "mej_med": mej_med, "mej_sgl": mej_sgl
                }

        if tiene_comp2:
            col_aon1, col_aon2 = st.columns(2)
            with col_aon1:
                m1 = procesar_y_mostrar_bloque_competidor(nombre_1, df_comp1, tamano_n, mostrar_cabecera=True)
            with col_aon2:
                m2 = procesar_y_mostrar_bloque_competidor(nombre_2, df_comp2, tamano_n, mostrar_cabecera=True)

            if m1 and m2:
                st.markdown("---")
                st.write("### ⚔️ Tabla Comparativa Directa")
                df_comp_directa = pd.DataFrame({
                    "Métrica": [f"Media Actual (Ao{tamano_n})", "Mejor Single (Media Actual)", f"Mejor Media Histórica (Ao{tamano_n})", "Mejor Single (Mejor Media)"],
                    f"{nombre_1}": [f"{m1['med_act']:.2f}{unidad_medida}", f"{m1['sgl_act']:.2f}{unidad_medida}", f"{m1['mej_med']:.2f}{unidad_medida}", f"{m1['mej_sgl']:.2f}{unidad_medida}"],
                    f"{nombre_2}": [f"{m2['med_act']:.2f}{unidad_medida}", f"{m2['sgl_act']:.2f}{unidad_medida}", f"{m2['mej_med']:.2f}{unidad_medida}", f"{m2['mej_sgl']:.2f}{unidad_medida}"],
                })
                st.dataframe(df_comp_directa, hide_index=True, use_container_width=True)
        else:
            procesar_y_mostrar_bloque_competidor(nombre_1, df_comp1, tamano_n, mostrar_cabecera=False)

        st.caption("📌 **Nota:** Para el cálculo de Ao5 se descartan el mejor y peor tiempo según la normativa WCA. Para N > 5 se utiliza la media aritmética simple del bloque consecutivo de N soluciones.")

    # ==================== PESTAÑA 4 ====================
    with tab4:
        st.write("### 📈 Coeficiente de Variación (%)")
        
        def calcular_variabilidad_anual(df):
            if df.empty:
                return pd.DataFrame()
            resumen = df.groupby("año")["solves segundos"].agg(
                media="mean", desviacion="std", varianza="var", solves_totales="count"
            )
            resumen["cv_porcentaje"] = (resumen["desviacion"] / resumen["media"]) * 100
            return resumen

        if not df_comp1.empty:
            var_1 = calcular_variabilidad_anual(df_comp1)
            df_grafico_var = pd.DataFrame({f"{nombre_1}": var_1["cv_porcentaje"]})

            if tiene_comp2 and not df_comp2.empty:
                var_2 = calcular_variabilidad_anual(df_comp2)
                df_grafico_var[f"{nombre_2}"] = var_2["cv_porcentaje"]

            df_grafico_var_ordenado = df_grafico_var.sort_index(ascending=True)
            df_grafico_var_ordenado.index = df_grafico_var_ordenado.index.astype(str)

            if tiene_comp2:
                mostrar_grafico_lineas(df_grafico_var_ordenado, titulo_eje_y="Coef. Variación (%)")
            else:
                st.line_chart(df_grafico_var_ordenado)

            st.write("### 📋 Resumen de Variabilidad Anual")
            if not tiene_comp2:
                tabla_var = var_1.sort_index(ascending=False).reset_index()
                tabla_var.columns = ["Año", f"Media ({unidad_medida})", "Desviación Estándar", "Varianza", "Solves Totales", "Coef. Variación (%)"]
                tabla_var[f"Media ({unidad_medida})"] = tabla_var[f"Media ({unidad_medida})"].apply(lambda x: f"{x:.2f}")
                tabla_var["Desviación Estándar"] = tabla_var["Desviación Estándar"].apply(lambda x: f"{x:.2f}")
                tabla_var["Varianza"] = tabla_var["Varianza"].apply(lambda x: f"{x:.2f}")
                tabla_var["Coef. Variación (%)"] = tabla_var["Coef. Variación (%)"].apply(lambda x: f"{x:.2f}%")
                st.dataframe(tabla_var, hide_index=True, use_container_width=True)
            else:
                tabla_var_comp = pd.DataFrame({
                    f"CV% ({nombre_1})": var_1["cv_porcentaje"],
                    f"Desv.Std ({nombre_1})": var_1["desviacion"],
                    f"CV% ({nombre_2})": var_2["cv_porcentaje"] if tiene_comp2 else None,
                    f"Desv.Std ({nombre_2})": var_2["desviacion"] if tiene_comp2 else None,
                }).sort_index(ascending=False).reset_index()
                tabla_var_comp = tabla_var_comp.rename(columns={"año": "Año"})
                st.dataframe(tabla_var_comp, hide_index=True, use_container_width=True)

            st.caption("📌 **Nota:** El Coeficiente de Variación (CV) mide la dispersión relativa de los tiempos. Un valor menor indica mayor consistencia en los resultados.")

    # ==================== PESTAÑA 5: TOP MUNDIAL ====================
    with tab5:
        st.write(f"### 🏆 Posición y Percentil Mundial ({NOMBRES_EVENTOS.get(evento_elegido, evento_elegido)})")

        def renderizar_tarjetas_top(wca_id_target, nombre_target, mostrar_cabecera=True):
            url_person = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/refs/heads/v1/persons/{wca_id_target}.json"
            resp = requests.get(url_person)

            if resp.status_code == 200:
                data = resp.json()
                df_avg = pd.json_normalize(data, record_path=["rank", "averages"], meta="name") if "rank" in data and "averages" in data["rank"] else pd.DataFrame()
                df_sgl = pd.json_normalize(data, record_path=["rank", "singles"], meta="name") if "rank" in data and "singles" in data["rank"] else pd.DataFrame()

                if mostrar_cabecera:
                    st.subheader(f"Competidor: {nombre_target}")

                # --- AVERAGE ---
                fila_avg = df_avg[df_avg["eventId"] == evento_elegido] if not df_avg.empty else pd.DataFrame()
                if not fila_avg.empty:
                    url_t_avg = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/refs/heads/v1/rank/world/average/{evento_elegido}.json"
                    tot_avg = requests.get(url_t_avg).json()["total"]
                    rk_avg = fila_avg["rank.world"].values[0]
                    val_avg_raw = fila_avg['best'].values[0]
                    val_avg_fmt = f"{val_avg_raw}{unidad_medida}" if evento_elegido == "333fm" else f"{val_avg_raw / 100:.2f}s".replace(".", ",")
                    top_avg_fmt = f"{(rk_avg / tot_avg):.3%}".replace(".", ",")

                    st.markdown(f"""
                    <div style="background: radial-gradient(circle at top left, #1A1A1A 0%, #0D0D0D 100%); border: 1px solid #D4AF37; border-left: 5px solid #FFD700; border-radius: 12px; padding: 16px 22px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 6px 20px rgba(0,0,0,0.6); color: white; margin-bottom: 16px;">
                        <div style="display: flex; flex-direction: column; gap: 4px;">
                            <span style="font-size: 13px; font-weight: 800; color: #D4AF37; letter-spacing: 1.5px; text-transform: uppercase;">Average</span>
                            <div style="font-size: 14px; color: #E0E0E0;">Tiempo: <b style="color: #FFFFFF;">{val_avg_fmt}</b> <span style="color: #D4AF37; margin: 0 6px;">|</span> Rank: <b style="color: #FFFFFF;">#{rk_avg:,}</b></div>
                            <div style="font-size: 12px; color: #A0A0A0;">Total competidores: <span style="color: #FFFFFF;">{tot_avg:,}</span></div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 10px; color: #D4AF37; letter-spacing: 1.2px; text-transform: uppercase; font-weight: 600;">Top Mundial</div>
                            <div style="font-size: 34px; font-weight: 900; background: linear-gradient(180deg, #FFE57F 0%, #D4AF37 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{top_avg_fmt}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info(f"Sin registro de Average en {NOMBRES_EVENTOS.get(evento_elegido, evento_elegido)}.")

                # --- SINGLE ---
                fila_sgl = df_sgl[df_sgl["eventId"] == evento_elegido] if not df_sgl.empty else pd.DataFrame()
                if not fila_sgl.empty:
                    url_t_sgl = f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/refs/heads/v1/rank/world/single/{evento_elegido}.json"
                    tot_sgl = requests.get(url_t_sgl).json()["total"]
                    rk_sgl = fila_sgl["rank.world"].values[0]
                    val_sgl_raw = fila_sgl['best'].values[0]
                    val_sgl_fmt = f"{val_sgl_raw}{unidad_medida}" if evento_elegido == "333fm" else f"{val_sgl_raw / 100:.2f}s".replace(".", ",")
                    top_sgl_fmt = f"{(rk_sgl / tot_sgl):.3%}".replace(".", ",")

                    st.markdown(f"""
                    <div style="background: radial-gradient(circle at top left, #1A1A1A 0%, #0D0D0D 100%); border: 1px solid #D4AF37; border-left: 5px solid #FFD700; border-radius: 12px; padding: 16px 22px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 6px 20px rgba(0,0,0,0.6); color: white; margin-bottom: 16px;">
                        <div style="display: flex; flex-direction: column; gap: 4px;">
                            <span style="font-size: 13px; font-weight: 800; color: #D4AF37; letter-spacing: 1.5px; text-transform: uppercase;">Single</span>
                            <div style="font-size: 14px; color: #E0E0E0;">Tiempo: <b style="color: #FFFFFF;">{val_sgl_fmt}</b> <span style="color: #D4AF37; margin: 0 6px;">|</span> Rank: <b style="color: #FFFFFF;">#{rk_sgl:,}</b></div>
                            <div style="font-size: 12px; color: #A0A0A0;">Total competidores: <span style="color: #FFFFFF;">{tot_sgl:,}</span></div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 10px; color: #D4AF37; letter-spacing: 1.2px; text-transform: uppercase; font-weight: 600;">Top Mundial</div>
                            <div style="font-size: 34px; font-weight: 900; background: linear-gradient(180deg, #FFE57F 0%, #D4AF37 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{top_sgl_fmt}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info(f"Sin registro de Single en {NOMBRES_EVENTOS.get(evento_elegido, evento_elegido)}.")

        if tiene_comp2:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                renderizar_tarjetas_top(wca_id_1, nombre_1, mostrar_cabecera=True)
            with col_t2:
                renderizar_tarjetas_top(wca_id_2, nombre_2, mostrar_cabecera=True)
        else:
            renderizar_tarjetas_top(wca_id_1, nombre_1, mostrar_cabecera=False)

        st.caption("📌 **Nota:** Posición en el ranking mundial oficial WCA y percentil relativo respecto al número total de competidores con registro en este evento.")
