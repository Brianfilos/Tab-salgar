import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --------------------------------------------------
# 0. Configuración inicial
# --------------------------------------------------
st.set_page_config(
    page_title="Análisis Predial Salgar",
    layout="wide",
    initial_sidebar_state="expanded"
)

EXCEL_FILE = "MATRIZ ANALISIS 2026 base tablero.xlsx"

LOGO_IZQ = "logo_legal.png"
LOGO_DER = "logo_salgar.png"


# --------------------------------------------------
# Funciones auxiliares
# --------------------------------------------------
@st.cache_data(show_spinner=True)
def load_sheet(sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def to_num(series: pd.Series) -> pd.Series:
    """Convierte una serie a numérico soportando formatos con puntos y comas."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    s = series.astype(str).str.replace(" ", "", regex=False)
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def safe_sum(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns:
        return 0.0
    return to_num(df[col]).fillna(0).sum()


def header():
    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        try:
            st.image(LOGO_IZQ, width=90)
        except Exception:
            pass
    with c2:
        st.markdown(
            '<h1 style="text-align:center;color:#004c99;">ANÁLISIS IMPUESTO PREDIAL UNIFICADO – SALGAR</h1>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p style="text-align:center;font-size:17px;color:#555;">'
            'Impacto de la actualización catastral y aplicación de límites de incremento (Ley 44, Ley 1995 y topes locales)'
            '</p>',
            unsafe_allow_html=True,
        )
    with c3:
        try:
            st.image(LOGO_DER, width=90)
        except Exception:
            pass


# --------------------------------------------------
# 1. Selector de página
# --------------------------------------------------
header()

pagina = st.sidebar.radio(
    "Selecciona la vista",
    [
        "Rural – Actualización catastral (GRUPO1-RURAL)",
        "Resago cambio de sector",
        "Urbano",
        "Predios nuevos",
        "Predios sin sector actual",
    ],
)


# --------------------------------------------------
# 2. PÁGINA 1: GRUPO1-RURAL
# --------------------------------------------------
if pagina.startswith("Rural"):
    st.markdown("## 🌾 GRUPO1-RURAL – Impacto de la actualización catastral")

    df = load_sheet("GRUPO1-RURAL")

    # --- KPIs de debido cobrar / Ley 44 / Ley 1995 ---
    deb25 = safe_sum(df, "DEBIDO COBRAR EN 2025")
    deb26 = safe_sum(df, "DEBIDO COBRAR 2026")
    ley44 = safe_sum(df, "LEY 44")
    ley1995 = safe_sum(df, "LEY 1995 50%")

    var44_abs = ley44 - deb26
    var44_pct = (var44_abs / deb26 * 100) if deb26 != 0 else 0

    var1995_abs = ley1995 - deb26
    var1995_pct = (var1995_abs / deb26 * 100) if deb26 != 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Debido cobrar 2025", f"${deb25:,.0f}")
    c2.metric("Debido cobrar 2026", f"${deb26:,.0f}")
    c3.metric("Escenario Ley 44 (tope incremento)", f"${ley44:,.0f}",
              delta=f"{var44_pct:.2f}%")
    c4.metric("Escenario Ley 1995 (50%)", f"${ley1995:,.0f}",
              delta=f"{var1995_pct:.2f}%")

    st.caption(
        "Las variaciones porcentuales se calculan frente al **Debido cobrar 2026** "
        "(escenario sin límites). Valores negativos indican reducción del recaudo."
    )

    # --- Concentración de avalúos por destino y rangos ---
    st.markdown("### 🧩 Concentración de avalúos por destinación y rangos de avalúo")

    if "AVALUO_ACT" in df.columns and "DEST_ACT" in df.columns:
        df_av = df.copy()
        df_av["AVALUO_ACT_NUM"] = to_num(df_av["AVALUO_ACT"])

        # Creamos rangos automáticos (quintiles) para ver en qué niveles se concentran los avalúos
        vals = df_av["AVALUO_ACT_NUM"].dropna()
        if len(vals) > 0:
            # 5 rangos aproximados
            cuantiles = np.quantile(vals, [0, 0.2, 0.4, 0.6, 0.8, 1.0])
            # evitar límites duplicados
            bins = sorted(set(cuantiles))
            if len(bins) >= 2:
                etiquetas = []
                for i in range(len(bins) - 1):
                    etiquetas.append(
                        f"${bins[i]:,.0f} – ${bins[i+1]:,.0f}"
                    )
                df_av["RANGO_AVALUO"] = pd.cut(
                    df_av["AVALUO_ACT_NUM"],
                    bins=bins,
                    labels=etiquetas,
                    include_lowest=True,
                )

                # Top destinaciones por suma de avalúo
                dest_sum = (
                    df_av.groupby("DEST_ACT")["AVALUO_ACT_NUM"]
                    .sum()
                    .sort_values(ascending=False)
                    .reset_index()
                )
                st.markdown("#### Destinaciones con mayor suma de avalúos (Rural)")
                st.dataframe(dest_sum.head(10), use_container_width=True)

                # Tabla cruzada DEST_ACT x RANGO_AVALUO
                tabla_rangos = (
                    df_av.groupby(["DEST_ACT", "RANGO_AVALUO"])["AVALUO_ACT_NUM"]
                    .agg(conteo="count", total_avaluo="sum")
                    .reset_index()
                )
                st.markdown("#### Distribución de avalúos por destinación y rango de avalúo")
                st.dataframe(tabla_rangos, use_container_width=True)

                # Gráfico de barras de los 10 destinos con más avalúo
                fig_rural = px.bar(
                    dest_sum.head(10),
                    x="DEST_ACT",
                    y="AVALUO_ACT_NUM",
                    title="Top 10 destinaciones rurales por suma de avalúos",
                    labels={"AVALUO_ACT_NUM": "Suma avalúos", "DEST_ACT": "Destinación"},
                )
                fig_rural.update_traces(texttemplate="$%{y:,.0f}", textposition="outside")
                fig_rural.update_layout(xaxis_tickangle=-30)
                st.plotly_chart(fig_rural, use_container_width=True)
            else:
                st.info("No hay suficientes valores distintos de avalúo para formar rangos.")
        else:
            st.info("No hay valores de AVALUO_ACT para analizar.")
    else:
        st.info("No se encontraron columnas AVALUO_ACT o DEST_ACT en la hoja GRUPO1-RURAL.")


# --------------------------------------------------
# 3. PÁGINA 2: RESAGO CAMBIO SECTOR
# --------------------------------------------------
elif pagina.startswith("Resago"):
    st.markdown("## 🔄 RESAGO CAMBIO SECTOR – Efecto de cambio de sector y límites locales")

    df = load_sheet("RESAGO CAMBIO SECTOR")

    deb25 = safe_sum(df, "DEBIDO COBRAR 2025")
    deb26 = safe_sum(df, "DEBIDO COBRAR 2026")
    limite100 = safe_sum(df, "LIMITE LOCAL 100%")
    limite50 = safe_sum(df, "LIMITE LOCAL 50%")

    var_26_abs = deb26 - deb25
    var_26_pct = (var_26_abs / deb25 * 100) if deb25 != 0 else 0

    var_100_abs = limite100 - deb26
    var_100_pct = (var_100_abs / deb26 * 100) if deb26 != 0 else 0

    var_50_abs = limite50 - deb26
    var_50_pct = (var_50_abs / deb26 * 100) if deb26 != 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Debido cobrar 2025", f"${deb25:,.0f}")
    c2.metric("Debido cobrar 2026 (sin límites)", f"${deb26:,.0f}",
              delta=f"{var_26_pct:.2f}%")
    c3.metric("Escenario límite local 100%", f"${limite100:,.0f}",
              delta=f"{var_100_pct:.2f}%")
    c4.metric("Escenario límite local 50%", f"${limite50:,.0f}",
              delta=f"{var_50_pct:.2f}%")

    st.caption(
        "Las variaciones de límite local 100% y 50% se calculan frente al **Debido cobrar 2026** "
        "(escenario sin tope). Valores negativos indican reducción del recaudo por la aplicación del límite."
    )

    # Gráfico comparativo
    df_totales = pd.DataFrame({
        "Escenario": [
            "2025",
            "2026 sin límite",
            "Límite local 100%",
            "Límite local 50%",
        ],
        "Valor": [deb25, deb26, limite100, limite50],
    })

    fig_resago = px.bar(
        df_totales,
        x="Escenario",
        y="Valor",
        text="Valor",
        title="Comparación de debido cobrar por escenario – Resago cambio de sector",
    )
    fig_resago.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig_resago.update_layout(yaxis_title="Valor", xaxis_title="")
    st.plotly_chart(fig_resago, use_container_width=True)


# --------------------------------------------------
# 4. PÁGINA 3: URBANO
# --------------------------------------------------
elif pagina.startswith("Urbano"):
    st.markdown("## 🏙️ URBANO – Impacto actualización catastral y topes")

    df = load_sheet("URBANO")

    liq25 = safe_sum(df, "LIQ_2025")
    deb26 = safe_sum(df, "DEBIDO COBRAR 2026")
    ley44 = safe_sum(df, "LEY 44 ")
    limite50 = safe_sum(df, "LIMITE LOCAL 50%")

    var_deb_abs = deb26 - liq25
    var_deb_pct = (var_deb_abs / liq25 * 100) if liq25 != 0 else 0

    var_ley44_abs = ley44 - deb26
    var_ley44_pct = (var_ley44_abs / deb26 * 100) if deb26 != 0 else 0

    var_lim50_abs = limite50 - deb26
    var_lim50_pct = (var_lim50_abs / deb26 * 100) if deb26 != 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Liquidación 2025 (LIQ_2025)", f"${liq25:,.0f}")
    c2.metric("Debido cobrar 2026", f"${deb26:,.0f}", delta=f"{var_deb_pct:.2f}%")
    c3.metric("Escenario Ley 44", f"${ley44:,.0f}", delta=f"{var_ley44_pct:.2f}%")
    c4.metric("Escenario límite local 50%", f"${limite50:,.0f}", delta=f"{var_lim50_pct:.2f}%")

    # Gráfico comparativo
    df_totales = pd.DataFrame({
        "Escenario": [
            "LIQ 2025",
            "Debido 2026 sin límite",
            "Ley 44",
            "Límite local 50%",
        ],
        "Valor": [liq25, deb26, ley44, limite50],
    })

    fig_urb = px.bar(
        df_totales,
        x="Escenario",
        y="Valor",
        text="Valor",
        title="Comparación de escenarios urbanos",
    )
    fig_urb.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig_urb.update_layout(yaxis_title="Valor", xaxis_title="")
    st.plotly_chart(fig_urb, use_container_width=True)


# --------------------------------------------------
# 5. PÁGINA 4: PREDIOS NUEVOS
# --------------------------------------------------
elif pagina.startswith("Predios nuevos"):
    st.markdown("## 🆕 PREDIOS NUEVOS – Perfil de la base catastral incorporada")

    df = load_sheet("PREDIOS NUEVOS")

    total_predios = df.shape[0]
    prom_avaluo = to_num(df["AVALUO"]).mean() if "AVALUO" in df.columns else 0

    c1, c2 = st.columns(2)
    c1.metric("Número de predios nuevos", f"{total_predios:,}")
    c2.metric("Avalúo promedio", f"${prom_avaluo:,.0f}")

    if "NOMBRE_DESTINACION" in df.columns and "AVALUO" in df.columns:
        df_dest = df.copy()
        df_dest["AVALUO_NUM"] = to_num(df_dest["AVALUO"])

        resumen = (
            df_dest.groupby("NOMBRE_DESTINACION")["AVALUO_NUM"]
            .agg(predios="count", avaluo_total="sum", avaluo_promedio="mean")
            .sort_values("avaluo_total", ascending=False)
            .reset_index()
        )

        st.markdown("### Destinaciones con mayor participación en avalúos de predios nuevos")
        st.dataframe(resumen, use_container_width=True)

        fig_nuevos = px.bar(
            resumen.head(10),
            x="NOMBRE_DESTINACION",
            y="avaluo_total",
            title="Top 10 destinaciones por suma de avalúos (predios nuevos)",
            labels={"NOMBRE_DESTINACION": "Destinación", "avaluo_total": "Avalúo total"},
        )
        fig_nuevos.update_traces(texttemplate="$%{y:,.0f}", textposition="outside")
        fig_nuevos.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig_nuevos, use_container_width=True)
    else:
        st.info("No se encontraron las columnas NOMBRE_DESTINACION o AVALUO en la hoja PREDIOS NUEVOS.")


# --------------------------------------------------
# 6. PÁGINA 5: SIN SECTOR ACTUAL
# --------------------------------------------------
else:  # "Predios sin sector actual"
    st.markdown("## ❓ PREDIOS SIN SECTOR ACTUAL – Destinaciones y avalúos")

    df = load_sheet("SIN SECTOR ACTUAL")

    total_predios = df.shape[0]
    total_avaluo = safe_sum(df, "AVALUO_ACT")
    total_liq25 = safe_sum(df, "LIQ_2025")

    c1, c2, c3 = st.columns(3)
    c1.metric("Número de predios sin sector", f"{total_predios:,}")
    c2.metric("Avalúo total actual", f"${total_avaluo:,.0f}")
    c3.metric("Liquidación 2025 total (LIQ_2025)", f"${total_liq25:,.0f}")

    if "DEST_ACT" in df.columns:
        df_s = df.copy()
        df_s["AVALUO_ACT_NUM"] = to_num(df_s["AVALUO_ACT"])
        df_s["LIQ_2025_NUM"] = to_num(df_s["LIQ_2025"])

        resumen_dest = (
            df_s.groupby("DEST_ACT")[["AVALUO_ACT_NUM", "LIQ_2025_NUM"]]
            .agg(predios=("AVALUO_ACT_NUM", "count"),
                 avaluo_total=("AVALUO_ACT_NUM", "sum"),
                 liq_2025_total=("LIQ_2025_NUM", "sum"),
                 avaluo_promedio=("AVALUO_ACT_NUM", "mean"))
            .sort_values("avaluo_total", ascending=False)
            .reset_index()
        )

        st.markdown("### Destinaciones de predios sin sector y sus avalúos")
        st.dataframe(resumen_dest, use_container_width=True)

        fig_sin = px.bar(
            resumen_dest.head(10),
            x="DEST_ACT",
            y="avaluo_total",
            title="Top 10 destinaciones sin sector por avalúo total",
            labels={"DEST_ACT": "Destinación", "avaluo_total": "Avalúo total"},
        )
        fig_sin.update_traces(texttemplate="$%{y:,.0f}", textposition="outside")
        fig_sin.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig_sin, use_container_width=True)
    else:
        st.info("No se encontró la columna DEST_ACT en la hoja SIN SECTOR ACTUAL.")

