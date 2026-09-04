# -*- coding: utf-8 -*-
"""
Proyector de Demanda y Auditor de Ahorro Eléctrico
====================================================
Demo funcional para reuniones con gerentes de planta, IT managers y
owners de retail/inmobiliario. Modelo de negocio: ahorro compartido
(shared savings) — se cobra un % del ahorro efectivamente identificado.

Ejecutar con:  streamlit run app.py
"""

import io
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from fpdf import FPDF

# =========================================================================
# 0. CONFIGURACIÓN GENERAL Y PALETA DE COLORES
# =========================================================================

st.set_page_config(
    page_title="Proyector de Demanda y Auditor de Ahorro Eléctrico",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta "informe de consultoría": azules oscuros, grises, un color de acento
COLOR_PRIMARY = "#0B2545"      # azul marino oscuro
COLOR_SECONDARY = "#13315C"    # azul medio
COLOR_GRAY = "#5C6B73"         # gris neutro
COLOR_LIGHT_GRAY = "#E9ECEF"   # gris claro (fondos)
COLOR_ACCENT = "#D98324"       # ámbar/naranja para alertas y highlights
COLOR_SUCCESS = "#2E7D32"      # verde para ahorro confirmado
COLOR_TEXT = "#1B1B1E"

CUSTOM_CSS = f"""
<style>
    .stApp {{
        background-color: #F7F8FA;
    }}
    h1, h2, h3 {{
        color: {COLOR_PRIMARY};
        font-family: 'Georgia', serif;
    }}
    .metric-card {{
        background-color: white;
        border-left: 5px solid {COLOR_PRIMARY};
        border-radius: 6px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    .proposal-box {{
        background-color: {COLOR_PRIMARY};
        color: white;
        border-radius: 10px;
        padding: 1.8rem 2rem;
    }}
    .proposal-box h2, .proposal-box h3, .proposal-box p, .proposal-box li {{
        color: white !important;
    }}
    .alert-box {{
        background-color: #FDF1E3;
        border-left: 5px solid {COLOR_ACCENT};
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {COLOR_LIGHT_GRAY};
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
    }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

TARIFAS_PERU = [
    "BT4", "BT5A", "BT5B", "BT5C", "BT5D",
    "MT2", "MT3", "MT4", "Cliente Libre",
]

# =========================================================================
# 1. DATOS DE EJEMPLO (empresa ficticia) — precargados en session_state
# =========================================================================

def generar_datos_ejemplo() -> pd.DataFrame:
    """Genera 18 meses de histórico ficticio con tendencia creciente."""
    meses = pd.date_range(end=datetime.today().replace(day=1), periods=18, freq="MS")
    rng = np.random.default_rng(seed=42)

    base_kwh = 42000
    filas = []
    for i, mes in enumerate(meses):
        tendencia = base_kwh + i * 650  # crecimiento mensual
        ruido = rng.normal(0, 900)
        kwh = max(0, tendencia + ruido)
        kw_max = max(0, kwh / (24 * 30) * rng.uniform(3.0, 3.6))  # factor de carga aprox
        filas.append(
            {
                "Mes/Año": mes.strftime("%Y-%m"),
                "Energía (kWh)": round(kwh, 0),
                "Potencia Máx. Demandada (kW)": round(kw_max, 1),
                "Potencia Contratada (kW)": 220.0,
                "Tipo de Tarifa": "MT3",
                "Monto Facturado (S/.)": round(kwh * 0.62 + kw_max * 45, 2),
            }
        )
    return pd.DataFrame(filas)


DEFAULT_AUDITORIA = {
    "horario_operacion": "Continuo (24h)",
    "tiene_fp_corregido": "No",
    "kvar_estimado": 80.0,
    "equipo_mayor_consumo": "Chiller / Sistema de aire acondicionado",
    "potencia_nominal_equipo": 150.0,
    "antiguedad_instalacion": "Entre 10 y 20 años",
    "cortes_calidad_energia": "Sí, ocasionalmente",
    "tipo_cliente": "Regulado",
    "nivel_tension": "Media Tensión (MT)",
    "pct_iluminacion_led": 40,
}

if "facturas_df" not in st.session_state:
    st.session_state.facturas_df = generar_datos_ejemplo()

if "auditoria" not in st.session_state:
    st.session_state.auditoria = DEFAULT_AUDITORIA.copy()

if "nombre_empresa" not in st.session_state:
    st.session_state.nombre_empresa = "Industrias Ficticias del Sur S.A.C. (Demo)"

# =========================================================================
# SIDEBAR — Navegación y datos generales
# =========================================================================

st.sidebar.title("⚡ Navegación")
st.sidebar.markdown("---")
st.session_state.nombre_empresa = st.sidebar.text_input(
    "Nombre del cliente / empresa", value=st.session_state.nombre_empresa
)

modulo = st.sidebar.radio(
    "Módulo",
    [
        "1️⃣ Histórico de Facturas",
        "2️⃣ Auditoría Rápida",
        "3️⃣ Dashboard de Resultados",
    ],
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Restaurar datos de ejemplo"):
    st.session_state.facturas_df = generar_datos_ejemplo()
    st.session_state.auditoria = DEFAULT_AUDITORIA.copy()
    st.rerun()

if st.sidebar.button("🗑️ Limpiar todo (usar data real)"):
    st.session_state.facturas_df = pd.DataFrame(
        columns=[
            "Mes/Año", "Energía (kWh)", "Potencia Máx. Demandada (kW)",
            "Potencia Contratada (kW)", "Tipo de Tarifa", "Monto Facturado (S/.)",
        ]
    )
    st.session_state.auditoria = {k: None for k in DEFAULT_AUDITORIA}
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(
    "Demo — Bantiv | Ingeniería Eléctrica\n\n"
    "Modelo de negocio: ahorro compartido (shared savings)."
)

st.title("Proyector de Demanda y Auditor de Ahorro Eléctrico")
st.caption(f"Cliente: **{st.session_state.nombre_empresa}**")

# =========================================================================
# MÓDULO 1 — HISTÓRICO DE FACTURAS
# =========================================================================

if modulo.startswith("1"):
    st.header("1️⃣ Histórico de Facturas")
    st.markdown(
        "Ingresa el histórico de las últimas 12-24 facturas. También puedes "
        "cargar un CSV con las mismas columnas."
    )

    csv_file = st.file_uploader("Cargar CSV de facturas (opcional)", type=["csv"])
    if csv_file is not None:
        try:
            df_csv = pd.read_csv(csv_file)
            st.session_state.facturas_df = df_csv
            st.success("CSV cargado correctamente.")
        except Exception as e:
            st.error(f"No se pudo leer el CSV: {e}")

    edited_df = st.data_editor(
        st.session_state.facturas_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Tipo de Tarifa": st.column_config.SelectboxColumn(
                "Tipo de Tarifa", options=TARIFAS_PERU
            ),
            "Energía (kWh)": st.column_config.NumberColumn(format="%.0f"),
            "Potencia Máx. Demandada (kW)": st.column_config.NumberColumn(format="%.1f"),
            "Potencia Contratada (kW)": st.column_config.NumberColumn(format="%.1f"),
            "Monto Facturado (S/.)": st.column_config.NumberColumn(format="%.2f"),
        },
        key="editor_facturas",
    )
    st.session_state.facturas_df = edited_df

    # --- Validaciones básicas ---
    st.markdown("#### Validación de datos")
    problemas = []
    df_check = st.session_state.facturas_df

    if len(df_check) < 12:
        problemas.append(
            f"Solo hay {len(df_check)} meses cargados. Se recomienda un mínimo de 12 "
            "para una proyección confiable."
        )

    for col in ["Energía (kWh)", "Potencia Máx. Demandada (kW)", "Monto Facturado (S/.)"]:
        if col in df_check.columns and (df_check[col].fillna(0) == 0).any():
            problemas.append(f"Hay valores en cero en la columna '{col}'.")

    if (
        "Potencia Máx. Demandada (kW)" in df_check.columns
        and "Potencia Contratada (kW)" in df_check.columns
    ):
        excedidos = df_check[
            df_check["Potencia Máx. Demandada (kW)"] > df_check["Potencia Contratada (kW)"]
        ]
        if not excedidos.empty:
            problemas.append(
                f"⚠️ En {len(excedidos)} mes(es) la potencia máxima demandada superó "
                "la potencia contratada (riesgo de penalidad por exceso)."
            )

    if problemas:
        for p in problemas:
            st.markdown(f"<div class='alert-box'>⚠️ {p}</div>", unsafe_allow_html=True)
    else:
        st.success("✅ Datos completos y consistentes.")

# =========================================================================
# MÓDULO 2 — AUDITORÍA RÁPIDA COMPLEMENTARIA
# =========================================================================

elif modulo.startswith("2"):
    st.header("2️⃣ Auditoría Rápida Complementaria")
    st.markdown(
        "Estas preguntas levantan información que **no aparece en la factura** "
        "pero es clave para identificar ahorros reales."
    )
    aud = st.session_state.auditoria

    with st.expander("🕐 Operación y horarios", expanded=True):
        aud["horario_operacion"] = st.selectbox(
            "Horario de operación principal",
            ["Continuo (24h)", "1 turno (8h)", "2 turnos (16h)", "Solo horario diurno"],
            index=["Continuo (24h)", "1 turno (8h)", "2 turnos (16h)", "Solo horario diurno"].index(
                aud.get("horario_operacion") or "Continuo (24h)"
            ),
        )
        if aud["horario_operacion"] != "Continuo (24h)":
            st.info(
                "💡 Al no operar 24h, existe oportunidad de evaluar traslado de "
                "cargas flexibles hacia horas fuera de punta."
            )

    with st.expander("🔌 Factor de potencia y calidad de energía", expanded=True):
        aud["tiene_fp_corregido"] = st.radio(
            "¿Tiene factor de potencia corregido (banco de condensadores)?",
            ["Sí", "No"],
            index=["Sí", "No"].index(aud.get("tiene_fp_corregido") or "No"),
            horizontal=True,
        )
        if aud["tiene_fp_corregido"] == "No":
            aud["kvar_estimado"] = st.number_input(
                "kVAR estimado a compensar (si lo conoces; si no, dejar estimado)",
                min_value=0.0, value=float(aud.get("kvar_estimado") or 80.0), step=5.0,
            )
        aud["cortes_calidad_energia"] = st.selectbox(
            "¿Ha tenido cortes o problemas de calidad de energía en el último año?",
            ["No", "Sí, ocasionalmente", "Sí, frecuentemente"],
            index=["No", "Sí, ocasionalmente", "Sí, frecuentemente"].index(
                aud.get("cortes_calidad_energia") or "Sí, ocasionalmente"
            ),
        )

    with st.expander("🏭 Equipos e instalación", expanded=True):
        aud["equipo_mayor_consumo"] = st.selectbox(
            "Equipo de mayor consumo",
            ["Motor / Bomba", "Chiller / Sistema de aire acondicionado",
             "Compresor de aire", "Servidores / Data Center", "Hornos / Resistencias", "Otro"],
            index=["Motor / Bomba", "Chiller / Sistema de aire acondicionado",
                   "Compresor de aire", "Servidores / Data Center", "Hornos / Resistencias", "Otro"].index(
                aud.get("equipo_mayor_consumo") or "Chiller / Sistema de aire acondicionado"
            ),
        )
        aud["potencia_nominal_equipo"] = st.number_input(
            "Potencia nominal aproximada de ese equipo (kW)",
            min_value=0.0, value=float(aud.get("potencia_nominal_equipo") or 150.0), step=5.0,
        )
        aud["antiguedad_instalacion"] = st.selectbox(
            "Antigüedad de la instalación eléctrica principal",
            ["Menos de 5 años", "Entre 5 y 10 años", "Entre 10 y 20 años", "Más de 20 años"],
            index=["Menos de 5 años", "Entre 5 y 10 años", "Entre 10 y 20 años", "Más de 20 años"].index(
                aud.get("antiguedad_instalacion") or "Entre 10 y 20 años"
            ),
        )

    with st.expander("💡 Tarifa e iluminación", expanded=True):
        aud["tipo_cliente"] = st.radio(
            "¿Está en tarifa regulada o ha evaluado ser cliente libre?",
            ["Regulado", "Cliente Libre", "Ha evaluado pasar a Cliente Libre"],
            index=["Regulado", "Cliente Libre", "Ha evaluado pasar a Cliente Libre"].index(
                aud.get("tipo_cliente") or "Regulado"
            ),
        )
        aud["nivel_tension"] = st.radio(
            "Nivel de tensión de suministro",
            ["Baja Tensión (BT)", "Media Tensión (MT)"],
            index=["Baja Tensión (BT)", "Media Tensión (MT)"].index(
                aud.get("nivel_tension") or "Media Tensión (MT)"
            ),
            horizontal=True,
        )
        aud["pct_iluminacion_led"] = st.slider(
            "% de iluminación que ya es LED", 0, 100, int(aud.get("pct_iluminacion_led") or 40)
        )

    st.session_state.auditoria = aud
    st.success("✅ Auditoría guardada. Pasa al Módulo 3 para ver el dashboard de resultados.")

# =========================================================================
# MÓDULO 3 — DASHBOARD DE RESULTADOS
# =========================================================================

else:
    st.header("3️⃣ Dashboard de Resultados")
    df = st.session_state.facturas_df.copy()
    aud = st.session_state.auditoria

    if df.empty or len(df) < 3:
        st.warning("Carga al menos 3 meses de facturas en el Módulo 1 para generar el dashboard.")
        st.stop()

    df = df.reset_index(drop=True)
    df["idx"] = range(len(df))

    # --------------------------------------------------------------
    # 3.1 GRÁFICO DE TENDENCIA + PROYECCIÓN
    # --------------------------------------------------------------
    st.subheader("📈 Tendencia de Consumo y Proyección a 12 Meses")

    x = df["idx"].values
    y_kwh = df["Energía (kWh)"].values
    y_kw = df["Potencia Máx. Demandada (kW)"].values
    potencia_contratada = df["Potencia Contratada (kW)"].iloc[-1]

    # Regresión lineal simple (numpy polyfit) — kWh y kW
    coef_kwh = np.polyfit(x, y_kwh, 1)
    coef_kw = np.polyfit(x, y_kw, 1)

    meses_futuros = 12
    x_full = np.arange(0, len(df) + meses_futuros)
    y_kwh_proj = np.polyval(coef_kwh, x_full)
    y_kw_proj = np.polyval(coef_kw, x_full)

    labels_hist = df["Mes/Año"].tolist()
    ultimo_mes = pd.to_datetime(labels_hist[-1])
    labels_fut = [
        (ultimo_mes + pd.DateOffset(months=i)).strftime("%Y-%m")
        for i in range(1, meses_futuros + 1)
    ]
    labels_full = labels_hist + labels_fut

    # Detectar mes de cruce del límite contratado
    mes_cruce = None
    for i in range(len(df), len(x_full)):
        if y_kw_proj[i] >= potencia_contratada:
            mes_cruce = labels_full[i]
            break

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels_hist, y=y_kw, mode="lines+markers", name="Potencia Máx. Demandada (kW) - histórico",
        line=dict(color=COLOR_PRIMARY, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=labels_full[len(df) - 1:], y=y_kw_proj[len(df) - 1:], mode="lines", name="Proyección Potencia (kW)",
        line=dict(color=COLOR_PRIMARY, width=2, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=labels_full, y=[potencia_contratada] * len(labels_full), mode="lines",
        name="Límite Potencia Contratada", line=dict(color=COLOR_ACCENT, width=2, dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=labels_hist, y=y_kwh / 100, mode="lines+markers", name="Energía (kWh /100) - histórico",
        line=dict(color=COLOR_GRAY, width=1.5), yaxis="y2", opacity=0.6,
    ))

    if mes_cruce:
        fig.add_vline(x=mes_cruce, line_dash="dot", line_color="red")
        fig.add_annotation(x=mes_cruce, y=potencia_contratada, text="⚠️ Cruce proyectado",
                            showarrow=True, arrowhead=2, font=dict(color="red"))

    fig.update_layout(
        template="plotly_white",
        height=480,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_title="Mes",
        yaxis_title="Potencia (kW)",
        yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Energía (kWh /100)"),
        margin=dict(t=30),
    )
    st.plotly_chart(fig, use_container_width=True)

    if mes_cruce:
        st.markdown(
            f"<div class='alert-box'>⚠️ Según la tendencia actual, la potencia máxima demandada "
            f"cruzaría el límite contratado de <b>{potencia_contratada:.0f} kW</b> "
            f"alrededor de <b>{mes_cruce}</b>.</div>",
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------------
    # 3.2 TABLA DE OPORTUNIDADES DE AHORRO
    # --------------------------------------------------------------
    st.subheader("💰 Oportunidades de Ahorro Detectadas")

    monto_anual_actual = df["Monto Facturado (S/.)"].tail(12).sum() if len(df) >= 12 else df["Monto Facturado (S/.)"].mean() * 12
    kwh_anual = df["Energía (kWh)"].tail(12).sum() if len(df) >= 12 else df["Energía (kWh)"].mean() * 12

    oportunidades = []

    # --- Oportunidad 1: Corrección de Factor de Potencia ---
    # FÓRMULA PLACEHOLDER — VALIDAR CON DATOS REALES
    # Penalidad OSINERGMIN: recargo aplica si FP < 0.9 (cos phi).
    # Aproximación: penalidad ~ 1% de la facturación de energía activa por cada
    # 0.01 de FP por debajo de 0.9, hasta un tope razonable de 15%.
    if aud.get("tiene_fp_corregido") == "No":
        fp_estimado = 0.82  # placeholder si no se midió
        deficit_fp = max(0, 0.9 - fp_estimado)
        pct_penalidad = min(0.15, deficit_fp * 100 * 0.01)
        ahorro_fp = monto_anual_actual * pct_penalidad
        kvar = aud.get("kvar_estimado") or 80.0
        inversion_fp = kvar * 180  # S/. por kVAR, placeholder
        payback_fp = inversion_fp / ahorro_fp if ahorro_fp > 0 else None
        oportunidades.append({
            "Oportunidad": "Corrección de Factor de Potencia",
            "Ahorro Anual Estimado (S/.)": round(ahorro_fp, 0),
            "Confianza": "Medio" if aud.get("kvar_estimado") else "Bajo",
            "Inversión Requerida (S/.)": round(inversion_fp, 0),
            "Payback (años)": round(payback_fp, 1) if payback_fp else "N/A",
        })

    # --- Oportunidad 2: Optimización de Potencia Contratada ---
    # FÓRMULA PLACEHOLDER — VALIDAR CON DATOS REALES
    # Si la demanda máxima histórica está consistentemente por debajo de la
    # contratada, se calcula el sobrecosto de tener contratado de más.
    demanda_prom = df["Potencia Máx. Demandada (kW)"].tail(12).mean() if len(df) >= 3 else df["Potencia Máx. Demandada (kW)"].mean()
    if demanda_prom < potencia_contratada * 0.85:
        exceso_kw = potencia_contratada - demanda_prom * 1.1  # margen de seguridad 10%
        cargo_potencia_mensual = 45  # S/. por kW, placeholder
        ahorro_potencia = max(0, exceso_kw) * cargo_potencia_mensual * 12
        oportunidades.append({
            "Oportunidad": "Optimización de Potencia Contratada",
            "Ahorro Anual Estimado (S/.)": round(ahorro_potencia, 0),
            "Confianza": "Alto" if len(df) >= 12 else "Medio",
            "Inversión Requerida (S/.)": 0,
            "Payback (años)": "Inmediato",
        })

    # --- Oportunidad 3: Cambio de Horario de Cargas ---
    # FÓRMULA PLACEHOLDER — VALIDAR CON DATOS REALES
    if aud.get("horario_operacion") and aud["horario_operacion"] != "Continuo (24h)":
        ahorro_horario = monto_anual_actual * 0.04  # 4% placeholder por desplazamiento a fuera de punta
        oportunidades.append({
            "Oportunidad": "Cambio de Horario de Cargas (fuera de punta)",
            "Ahorro Anual Estimado (S/.)": round(ahorro_horario, 0),
            "Confianza": "Bajo",
            "Inversión Requerida (S/.)": 0,
            "Payback (años)": "Inmediato",
        })

    # --- Oportunidad 4: Migración de Tarifa ---
    # FÓRMULA PLACEHOLDER — VALIDAR CON DATOS REALES (pendiente tabla real de tarifas)
    ahorro_tarifa = monto_anual_actual * 0.03  # 3% placeholder
    oportunidades.append({
        "Oportunidad": "Migración / Optimización de Tarifa",
        "Ahorro Anual Estimado (S/.)": round(ahorro_tarifa, 0),
        "Confianza": "Bajo",
        "Inversión Requerida (S/.)": 0,
        "Payback (años)": "Inmediato",
    })

    # --- Oportunidad 5: Modernización de Iluminación LED ---
    # FÓRMULA PLACEHOLDER — VALIDAR CON DATOS REALES
    pct_led = aud.get("pct_iluminacion_led")
    if pct_led is not None and pct_led < 80:
        pct_no_led = (100 - pct_led) / 100
        ahorro_led = monto_anual_actual * 0.06 * pct_no_led  # 6% del gasto total si 100% no-LED, placeholder
        inversion_led = pct_no_led * 15000  # placeholder
        payback_led = inversion_led / ahorro_led if ahorro_led > 0 else None
        oportunidades.append({
            "Oportunidad": "Modernización de Iluminación a LED",
            "Ahorro Anual Estimado (S/.)": round(ahorro_led, 0),
            "Confianza": "Medio",
            "Inversión Requerida (S/.)": round(inversion_led, 0),
            "Payback (años)": round(payback_led, 1) if payback_led else "N/A",
        })

    df_oportunidades = pd.DataFrame(oportunidades)

    def resaltar_confianza(val):
        colores = {"Alto": "background-color:#DCEFDD", "Medio": "background-color:#FFF3CD", "Bajo": "background-color:#FBEBEE"}
        return colores.get(val, "")

    st.dataframe(
        df_oportunidades.style.applymap(resaltar_confianza, subset=["Confianza"]).format(
            {"Ahorro Anual Estimado (S/.)": "S/. {:,.0f}", "Inversión Requerida (S/.)": "S/. {:,.0f}"}
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "⚠️ Todas las fórmulas están marcadas como placeholder en el código y deben "
        "validarse con datos reales del cliente y tarifario vigente de OSINERGMIN."
    )

    # --------------------------------------------------------------
    # 3.3 RESUMEN EJECUTIVO Y PROPUESTA
    # --------------------------------------------------------------
    st.subheader("📋 Resumen Ejecutivo")

    ahorro_total_anual = df_oportunidades["Ahorro Anual Estimado (S/.)"].sum()
    inversion_total = df_oportunidades["Inversión Requerida (S/.)"].sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"<div class='metric-card'><h4>Ahorro Potencial Anual</h4>"
            f"<h2 style='color:{COLOR_SUCCESS}'>S/. {ahorro_total_anual:,.0f}</h2></div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"<div class='metric-card'><h4>Facturación Anual Actual</h4>"
            f"<h2>S/. {monto_anual_actual:,.0f}</h2></div>",
            unsafe_allow_html=True,
        )
    with col3:
        pct_ahorro = (ahorro_total_anual / monto_anual_actual * 100) if monto_anual_actual else 0
        st.markdown(
            f"<div class='metric-card'><h4>% de Ahorro sobre Facturación</h4>"
            f"<h2 style='color:{COLOR_ACCENT}'>{pct_ahorro:.1f}%</h2></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    pct_comision = st.slider("Ajustar % de comisión del modelo de ahorro compartido", 10, 50, 30)
    comision_anual = ahorro_total_anual * pct_comision / 100
    retencion_cliente = ahorro_total_anual - comision_anual

    st.markdown(
        f"""
        <div class='proposal-box'>
        <h3>💼 Propuesta de Ahorro Compartido</h3>
        <p>Con el modelo de ahorro compartido, tu inversión inicial en el diagnóstico es
        <b>S/. 0</b>. Si el ahorro identificado se confirma y se logra el
        <b>{pct_comision}%</b> de comisión pactado:</p>
        <ul>
            <li>Comisión anual estimada: <b>S/. {comision_anual:,.0f}</b></li>
            <li>Tú retienes: <b>S/. {retencion_cliente:,.0f}</b> ({100 - pct_comision}% del ahorro)</li>
        </ul>
        <p><i>Nota: la inversión en equipos (ej. banco de condensadores, LED) señalada en la
        tabla de oportunidades es aparte y se evalúa caso por caso.</i></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------------
    # 3.4 EXPORTACIÓN A PDF
    # --------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)

    def generar_pdf() -> bytes:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Informe de Auditoría y Ahorro Eléctrico", ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, f"Cliente: {st.session_state.nombre_empresa}", ln=True)
        pdf.cell(0, 8, f"Fecha: {datetime.today().strftime('%Y-%m-%d')}", ln=True)
        pdf.ln(5)

        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "Resumen Ejecutivo", ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 7, (
            f"Facturacion anual actual: S/. {monto_anual_actual:,.0f}\n"
            f"Ahorro potencial anual identificado: S/. {ahorro_total_anual:,.0f} "
            f"({pct_ahorro:.1f}% de la facturacion)\n"
            f"Modelo de ahorro compartido ({pct_comision}% comision): "
            f"comision anual S/. {comision_anual:,.0f}, retencion cliente S/. {retencion_cliente:,.0f}\n"
        ))
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "Oportunidades de Ahorro Detectadas", ln=True)
        pdf.set_font("Helvetica", "B", 10)
        headers = ["Oportunidad", "Ahorro S/.", "Confianza", "Inversion S/.", "Payback"]
        widths = [70, 30, 25, 30, 25]
        for h, w in zip(headers, widths):
            pdf.cell(w, 8, h, border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for _, row in df_oportunidades.iterrows():
            pdf.cell(widths[0], 8, str(row["Oportunidad"])[:40], border=1)
            pdf.cell(widths[1], 8, f"{row['Ahorro Anual Estimado (S/.)']:,.0f}", border=1)
            pdf.cell(widths[2], 8, str(row["Confianza"]), border=1)
            pdf.cell(widths[3], 8, f"{row['Inversión Requerida (S/.)']:,.0f}", border=1)
            pdf.cell(widths[4], 8, str(row["Payback (años)"]), border=1)
            pdf.ln()

        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(0, 6, (
            "Nota: todos los calculos financieros de este informe utilizan formulas "
            "placeholder que deben validarse con datos reales del cliente y el "
            "tarifario vigente de OSINERGMIN antes de presentarse como propuesta final."
        ))

        return bytes(pdf.output(dest="S"))

    pdf_bytes = generar_pdf()
    st.download_button(
        label="📄 Descargar Informe en PDF",
        data=pdf_bytes,
        file_name=f"informe_ahorro_{st.session_state.nombre_empresa.replace(' ', '_')[:30]}.pdf",
        mime="application/pdf",
    )
