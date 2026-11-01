import streamlit as st
import pandas as pd
import datetime
import calendar
import os

import logging
import math
import re
import time

from firebase_admin import firestore

from database import obtener_conexion, obtener_catálogo_tipos, verificar_queja_duplicada
from limitador import esta_bloqueado, limpiar, registrar_fallo
from seguridad import (
    RE_ID_DRIVE, ErrorValidacion, LimiteExcedido,
    escapar_md as md, formatear_codigo, link_whatsapp, normalizar_telefono,
    sanear_nombre, verificar_secreto,
)
from utils import (
    buscar_queja_segura, cargar_quejas, descargar_evidencia, registrar_aclaracion,
    registrar_auditoria, registrar_lote, validar_queja,
)

logger = logging.getLogger("quejas")

# Tiempos de sesión del panel RH
INACTIVIDAD_SEG = 30 * 60      # 30 min sin actividad -> cierra sesión
SESION_MAX_SEG = 8 * 60 * 60   # 8 h máximo aunque haya actividad
ESTADOS_QUEJA = ['Pendiente', 'En proceso', 'Requiere información', 'Resuelto', 'Rechazada']

# Configuración inicial de la página
st.set_page_config(
    page_title="Sistema de Gestión de Quejas de Nómina", 
    page_icon="📋", 
    layout="wide"
)

# Identidad visual
st.markdown("""
<style>
:root { color-scheme: light; }
.stApp { background: #f4f7fb; color: #172033; }
[data-testid="stHeader"] { background: rgba(244,247,251,.88); }
[data-testid="stMainBlockContainer"] { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#12233f 0%,#172f50 100%); border-right: 1px solid #203c60; }
[data-testid="stSidebar"] * { color: #edf5ff; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { background: rgba(255,255,255,.055); border: 1px solid rgba(255,255,255,.09); border-radius: 12px; padding: .55rem .7rem; margin: .25rem 0; transition: .18s ease; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: rgba(255,255,255,.13); }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #c6d6eb; }
h1, h2, h3 { color: #172b4d; letter-spacing: -.025em; }
h1 { font-weight: 800; }
h2 { font-weight: 750; margin-top: .35rem; }
h3 { font-weight: 700; }
p, label, .stMarkdown { line-height: 1.55; }
[data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] { border: 1px solid #e0e8f2; border-radius: 18px; background: #fff; box-shadow: 0 8px 28px rgba(31,55,88,.055); padding: 1.15rem; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stSelectbox"] div[data-baseweb="select"] { border-radius: 10px; }
[data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus, [data-testid="stTextArea"] textarea:focus { border-color: #3978d4; box-shadow: 0 0 0 2px rgba(57,120,212,.12); }
.stButton > button, [data-testid="stFormSubmitButton"] button, [data-testid="stDownloadButton"] button { border-radius: 10px; border: 1px solid #245fba; background: linear-gradient(135deg,#2868c7,#1d4f9a); color: white; font-weight: 650; padding: .55rem 1rem; box-shadow: 0 4px 10px rgba(36,95,186,.15); transition: transform .15s ease, box-shadow .15s ease; }
.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover, [data-testid="stDownloadButton"] button:hover { border-color: #174582; box-shadow: 0 7px 16px rgba(36,95,186,.22); transform: translateY(-1px); color: white; }
[data-testid="stAlert"] { border-radius: 12px; border: 1px solid #dce7f4; }
[data-testid="stDataFrame"] { border: 1px solid #dfe7f1; border-radius: 14px; overflow: hidden; }
hr { border-color: #e1e8f1; margin: 1.4rem 0; }
[data-testid="stFileUploader"] section { border: 1px dashed #b7c9e0; border-radius: 12px; background: #f8fbff; }
.hero-app { padding: 1.5rem 1.7rem; border-radius: 20px; margin: 0 0 1.5rem; background: linear-gradient(115deg,#12233f 0%,#1f528f 65%,#3279c8 100%); color: white; box-shadow: 0 12px 30px rgba(26,65,112,.16); }
.hero-app .eyebrow { color: #bcd8ff; text-transform: uppercase; letter-spacing: .13em; font-size: .76rem; font-weight: 750; margin-bottom: .45rem; }
.hero-app h1 { color: white; font-size: clamp(1.7rem,3vw,2.45rem); line-height: 1.12; margin: 0 0 .55rem; }
.hero-app p { color: #e0edff; margin: 0; font-size: 1rem; }
.section-intro { color: #61728a; margin-top: -.45rem; margin-bottom: 1.25rem; }
@media (max-width: 700px) { [data-testid="stMainBlockContainer"] { padding: 1rem .8rem 2rem; } .hero-app { padding: 1.2rem; border-radius: 15px; } [data-testid="stForm"] { padding: .7rem; } }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-app">
  <div class="eyebrow">Portal de atención · Recursos Humanos</div>
  <h1>Gestión de Quejas de Nómina</h1>
  <p>Registra hasta 5 incidencias en una sola sesión, consulta el seguimiento y facilita la atención en un solo lugar.</p>
</div>
""", unsafe_allow_html=True)

modulo = st.sidebar.radio(
    "Seleccione Módulo", 
    [
        "Empleado: Crear Queja", 
        "Empleado: Consultar Estatus", 
        "Panel RH / Gestión"
    ]
)

# Firma flotante
enlace_perfil = "https://share.streamlit.io/user/danyflow"

firma_html = f"""
<style>
.firma-flotante-link {{
    position: fixed !important;
    bottom: 18px !important;    
    left: 18px !important;      
    right: auto !important;
    z-index: 2147483647 !important;
    text-decoration: none !important;
}}
.firma-flotante {{
    display: flex !important;
    align-items: center !important;
    background: #06b6d4 !important;
    color: #ffffff !important;
    width: 44px !important;
    height: 44px !important;
    padding: 6px !important;
    border-radius: 50px !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
    border: 1px solid #0891b2 !important;
    font-family: sans-serif !important;
    font-size: 13px !important;
    overflow: hidden !important;
    transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease, background 0.3s ease, padding 0.3s ease !important;
    cursor: pointer !important;
    white-space: nowrap !important;
}}
.firma-flotante:hover {{
    width: max-content !important; 
    background: #0891b2 !important; 
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35) !important;
    padding-right: 16px !important; 
}}
.firma-flotante img {{
    width: 30px !important;
    height: 30px !important;
    border-radius: 50% !important;
    object-fit: cover !important;
    flex-shrink: 0 !important;
    border: 1.5px solid rgba(255, 255, 255, 0.9) !important;
}}
.firma-avatar {{ width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: #ffffff; color: #0891b2; font-size: 16px; flex-shrink: 0; }}
.firma-texto {{
    margin-left: 12px !important;
    opacity: 0 !important;
    transition: opacity 0.25s ease 0.1s !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    text-align: left !important;
    line-height: 1.3 !important;
}}
.firma-flotante:hover .firma-texto {{ opacity: 1 !important; }}
.firma-titulo {{ font-weight: 600 !important; font-size: 12px !important; color: #ffffff !important; }}
.firma-sub {{ font-size: 10px !important; color: #ecfeff !important; }}
</style>
<a href="{enlace_perfil}" target="_blank" rel="noopener noreferrer" class="firma-flotante-link" title="Visitar perfil de Streamlit">
    <div class="firma-flotante">
        <span class="firma-avatar">⚡</span>
        <div class="firma-texto">
            <span class="firma-titulo">By Dany FloVel</span>
            <span class="firma-sub">⚡ Ver perfil ⚡</span>
        </div>
    </div>
</a>
"""
st.markdown(firma_html, unsafe_allow_html=True)

# ---------------------------------------------------------
# MÓDULO 1: EMPLEADO - CREAR QUEJA (MULTIPLE / HASTA 5)
# ---------------------------------------------------------
if modulo == "Empleado: Crear Queja":
    st.header("✍️ Registrar quejas de nómina")
    st.markdown("""<div class="section-intro">Puedes registrar una o hasta 5 quejas simultáneas en el mismo trámite. Todos los campos con * son obligatorios.</div>""", unsafe_allow_html=True)

    # Resultado de un registro exitoso: se muestra hasta que la persona lo confirme,
    # porque el código de seguimiento se entrega UNA sola vez.
    if st.session_state.get("resultado_registro"):
        resultado = st.session_state["resultado_registro"]
        st.success("✅ Tus quejas fueron registradas correctamente.")
        st.warning("⚠️ **Guarda tu folio y tu código de seguimiento.** Los necesitarás (junto con tu número de tarjeta) para consultar el estatus. Por seguridad el código no se vuelve a mostrar.")
        lineas_comprobante = []
        for r in resultado:
            linea = f"Folio: {r['folio']}    Código de seguimiento: {formatear_codigo(r['codigo'])}"
            st.code(f"{linea}\n({r['tipo']})", language=None)
            lineas_comprobante.append(f"{linea}  ({r['tipo']})")
        st.download_button(
            "📄 Descargar comprobante (.txt)",
            data="Comprobante de quejas de nómina\n\n" + "\n".join(lineas_comprobante) + "\n",
            file_name="comprobante_quejas.txt",
            mime="text/plain",
        )
        if st.button("➕ Registrar otras quejas"):
            del st.session_state["resultado_registro"]
            st.rerun()
        st.stop()

    catálogo = obtener_catálogo_tipos()
    opciones_tipos = {item['nombre']: item for item in catálogo}

    if 'modo_confirmacion_lote' not in st.session_state:
        st.session_state.modo_confirmacion_lote = False

    def crear_estructura_queja_vacia():
        return {
            "tarjeta": "", "nombre": "", "telefono": "", "turno": "Matutino",
            "tipo_nombre": list(opciones_tipos.keys())[0] if opciones_tipos else "",
            "anio": datetime.datetime.now().year, "mes": "Enero", "periodo": "Q1 (Días 1-15)",
            "monto": 0.0, "dias_incidencia_lista": [], "motivo": "", "evidencias": [], "talon": None
        }

    if 'lista_quejas_temp' not in st.session_state or not st.session_state.lista_quejas_temp:
        st.session_state.lista_quejas_temp = [crear_estructura_queja_vacia()]

    # PASO 2: VISTA PREVIA Y CONFIRMACIÓN DE LOTE COMPLETO
    if st.session_state.modo_confirmacion_lote:
        st.subheader(f"📋 Resumen y Confirmación del Lote ({len(st.session_state.lista_quejas_temp)} Solicitud(es))")
        st.info("Verifique detenidamente la información de cada queja antes de registrar las solicitudes.")

        for idx, datos in enumerate(st.session_state.lista_quejas_temp, start=1):
            with st.expander(f"🔹 Queja #{idx}: {datos['tipo_nombre']} - ${datos['monto']:,.2f}", expanded=True):
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.write(f"**Tarjeta de Empleado:** {md(datos['tarjeta'])}")
                    st.write(f"**Nombre del Empleado:** {md(datos['nombre'])}")
                    st.write(f"**Teléfono / WhatsApp:** {md(datos['telefono'])}")
                    st.write(f"**Turno:** {md(datos['turno'])}")

                with col_res2:
                    st.write(f"**Tipo de Queja:** {md(datos['tipo_nombre'])}")
                    st.write(f"**Quincena Afectada:** {md(datos['quincena'])}")
                    st.write(f"**Monto Reclamado:** \\${datos['monto']:,.2f}")
                    if datos.get('dias_str'):
                        st.write(f"**Días de Incidencia:** {md(datos['dias_str'])}")

                if datos['evidencias']:
                    nombres_ev = ", ".join([sanear_nombre(e.name) for e in datos['evidencias']])
                    st.write(f"📄 **Evidencia(s) Principal(es):** {md(nombres_ev)}")

                if datos['talon']:
                    st.write(f"📄 **Talón de Pago:** {md(sanear_nombre(datos['talon'].name))}")

                st.write(f"**Motivo / Detalle:** {md(datos['motivo'])}")

        st.write("---")
        col_btn1, col_btn2 = st.columns([1, 1])

        with col_btn1:
            if st.button("✏️ Modificar / Regresar a Edición"):
                st.session_state.modo_confirmacion_lote = False
                st.rerun()

        with col_btn2:
            if st.button("🚀 Confirmar y Registrar Lote de Quejas", type="primary"):
                registro_ok = None
                try:
                    with st.spinner("Registrando quejas y subiendo evidencias..."):
                        registro_ok = registrar_lote(st.session_state.lista_quejas_temp)
                except (ErrorValidacion, LimiteExcedido) as e:
                    st.error(f"⚠️ {md(str(e))}")
                except Exception:
                    logger.exception("Error al registrar el lote de quejas")
                    st.error("No se pudo registrar el lote. Intenta de nuevo; si el problema continúa, avisa a Recursos Humanos.")

                if registro_ok:
                    st.session_state.resultado_registro = registro_ok
                    st.session_state.modo_confirmacion_lote = False
                    st.session_state.lista_quejas_temp = [crear_estructura_queja_vacia()]
                    st.rerun()

    # PASO 1: FORMULARIO DINÁMICO DE CAPTURA EN PESTAÑAS (HASTA 5 QUEJAS)
    else:
        num_quejas = len(st.session_state.lista_quejas_temp)
        st.markdown(f"#### ⚙️ Captura de Solicitudes ({num_quejas} de 5 máximo)")
            
        if num_quejas >= 5:
            st.caption("ℹ️ Ha alcanzado el límite máximo de 5 quejas simultáneas en este lote.")

        nombres_tabs = [f"Queja #{i+1}" for i in range(num_quejas)]
        tabs = st.tabs(nombres_tabs)
        
        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]

        for i, tab in enumerate(tabs):
            with tab:
                q_data = st.session_state.lista_quejas_temp[i]
                
                if num_quejas > 1:
                    c_del1, c_del2 = st.columns([4, 1])
                    with c_del2:
                        if st.button(f"🗑️ Quitar Queja #{i+1}", key=f"btn_del_q_{i}"):
                            st.session_state.lista_quejas_temp.pop(i)
                            st.rerun()

                st.markdown("##### 📌 Datos Principales")
                col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                
                with col_a1:
                    tarjeta = st.text_input("Número de Tarjeta *", value=q_data.get('tarjeta', ''), max_chars=15, key=f"tarjeta_{i}")
                    nombre = st.text_input("Nombre del Empleado *", value=q_data.get('nombre', ''), max_chars=60, key=f"nombre_{i}")
                    
                with col_a2:
                    telefono = st.text_input("Teléfono / WhatsApp *", value=q_data.get('telefono', ''), max_chars=15, placeholder="Ej. 3312345678", key=f"tel_{i}")
                    turnos_opciones = ["Matutino", "Vespertino", "Nocturno", "Jornada Acumulada Diurna", "Jornada Acumulada Nocturna"]
                    turno_prev = q_data.get('turno', 'Matutino')
                    idx_turno = turnos_opciones.index(turno_prev) if turno_prev in turnos_opciones else 0
                    turno = st.selectbox("Turno *", turnos_opciones, index=idx_turno, key=f"turno_{i}")

                with col_a3:
                    lista_tipos = list(opciones_tipos.keys())
                    tipo_prev = q_data.get('tipo_nombre', lista_tipos[0])
                    idx_tipo = lista_tipos.index(tipo_prev) if tipo_prev in lista_tipos else 0
                    tipo_seleccionado = st.selectbox("Tipo de Queja *", lista_tipos, index=idx_tipo, key=f"tipo_{i}")
                    
                    monto_val = float(q_data.get('monto', 0.0))
                    monto = st.number_input("Monto Descuento ($) *", value=monto_val, min_value=0.0, max_value=1000000.0, step=50.0, key=f"monto_{i}")

                with col_a4:
                    anio_actual = datetime.datetime.now().year
                    lista_anios = list(range(anio_actual - 3, anio_actual + 2))
                    try:
                        anio_prev = int(q_data.get('anio', anio_actual))
                    except (ValueError, TypeError):
                        anio_prev = anio_actual
                    idx_anio = lista_anios.index(anio_prev) if anio_prev in lista_anios else lista_anios.index(anio_actual)
                    anio_seleccionado = st.selectbox("Año *", lista_anios, index=idx_anio, key=f"anio_{i}")
                    
                    mes_prev = q_data.get('mes', 'Enero')
                    idx_mes_sel = meses.index(mes_prev) if mes_prev in meses else 0
                    mes_seleccionado = st.selectbox("Mes *", meses, index=idx_mes_sel, key=f"mes_{i}")

                opciones_periodo = ["Q1 (Días 1-15)", "Q2 (Días 16-fin)"]
                periodo_prev = q_data.get('periodo', 'Q1 (Días 1-15)')
                idx_p = opciones_periodo.index(periodo_prev) if periodo_prev in opciones_periodo else 0
                quincena_periodo = st.radio("Periodo Quincenal *", opciones_periodo, index=idx_p, horizontal=True, key=f"periodo_{i}")

                idx_mes = meses.index(mes_seleccionado) + 1
                num_q = "Q1" if "Q1" in quincena_periodo else "Q2"
                quincena = f"{anio_seleccionado}-{idx_mes:02d}{num_q}"
                
                st.caption(f"📅 Quincena calculada: **{quincena}**")

                dias_seleccionados = []
                es_tipo_especial = tipo_seleccionado in ['Descuento por omisión', 'Permiso no aplicado']
                
                if es_tipo_especial:
                    st.write("---")
                    st.markdown(f"🗓️ **Selección de Días Afectados ({mes_seleccionado} {anio_seleccionado} - {quincena_periodo})**")
                    st.caption("Marque de las siguientes opciones los días correspondientes a esta incidencia (Máximo 5 días):")
                    
                    if "Q1" in quincena_periodo:
                        rango_dias = list(range(1, 16))
                    else:
                        ultimo_dia_mes = calendar.monthrange(anio_seleccionado, idx_mes)[1]
                        rango_dias = list(range(16, ultimo_dia_mes + 1))
                    
                    dias_prev_guardados = q_data.get('dias_incidencia_lista', [])
                    num_cols = 5 if len(rango_dias) >= 5 else len(rango_dias)
                    cols_dias = st.columns(num_cols)
                    
                    for d_idx, d in enumerate(rango_dias):
                        c_target = cols_dias[d_idx % num_cols]
                        with c_target:
                            default_checked = d in dias_prev_guardados
                            if st.checkbox(f"Día {d}", value=default_checked, key=f"chk_q{i}_dia_{d}"):
                                dias_seleccionados.append(d)
                                
                    if len(dias_seleccionados) > 5:
                        st.warning("⚠️ Máximo 5 días permitidos por queja.")

                st.write("---")
                col_file1, col_file2 = st.columns(2)
                with col_file1:
                    evidencias = st.file_uploader("1. Evidencia(s) Principal(es) * (Máx. 5 archivos)", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True, key=f"evidencias_{i}")
                with col_file2:
                    talon_pago = st.file_uploader("2. Talón de Pago (Opcional)", type=["pdf", "png", "jpg", "jpeg"], key=f"talon_{i}")

                motivo = st.text_area("Motivo y Detalle de la Queja *", value=q_data.get('motivo', ''), placeholder="Explique detalladamente el concepto de la incidencia...", max_chars=2000, key=f"motivo_{i}")
                
                st.write("---")
                
                puede_agregar = num_quejas < 5
                if st.button("➕ Añadir otra queja al lote", disabled=not puede_agregar, key=f"btn_add_bottom_{i}"):
                    st.session_state.lista_quejas_temp.append(crear_estructura_queja_vacia())
                    st.rerun()

                st.session_state.lista_quejas_temp[i] = {
                    "tarjeta": tarjeta.strip(),
                    "nombre": nombre.strip(),
                    "telefono": telefono.strip(),
                    "turno": turno,
                    "tipo_nombre": tipo_seleccionado,
                    "tipo_id": opciones_tipos[tipo_seleccionado]['id'],
                    "anio": int(anio_seleccionado),
                    "mes": mes_seleccionado,
                    "periodo": quincena_periodo,
                    "quincena": quincena,
                    "monto": monto,
                    "dias_incidencia_lista": sorted(dias_seleccionados),
                    "motivo": motivo.strip(),
                    "evidencias": evidencias if evidencias else q_data.get('evidencias', []),
                    "talon": talon_pago if talon_pago is not None else q_data.get('talon')
                }

        st.write("---")
        if st.button("📋 Revisar y Confirmar Lote de Quejas", type="primary"):
            errores = []
            vistos = set()

            for idx, q_item in enumerate(st.session_state.lista_quejas_temp, start=1):
                es_esp = q_item['tipo_nombre'] in ['Descuento por omisión', 'Permiso no aplicado']
                q_item['dias_str'] = ", ".join(str(d) for d in q_item['dias_incidencia_lista']) if es_esp else None

                problemas = validar_queja(q_item)
                for p in problemas:
                    errores.append(f"Queja #{idx}: {p}")

                if not problemas:
                    clave = (q_item['tarjeta'], q_item['tipo_id'], q_item['quincena'])
                    if clave in vistos:
                        errores.append(f"Queja #{idx}: está repetida dentro de este mismo lote.")
                    elif verificar_queja_duplicada(*clave):
                        errores.append(f"Queja #{idx}: Ya existe una queja activa para la tarjeta {q_item['tarjeta']} en la quincena {q_item['quincena']}.")
                    vistos.add(clave)

            if errores:
                for err in errores:
                    st.error(f"⚠️ {md(err)}")
            else:
                st.session_state.modo_confirmacion_lote = True
                st.rerun()

# ---------------------------------------------------------
# MÓDULO 2: EMPLEADO - CONSULTAR ESTATUS
# ---------------------------------------------------------
elif modulo == "Empleado: Consultar Estatus":
    st.header("🔎 Seguimiento de solicitud")
    st.markdown("""<div class="section-intro">Ingresa tu folio, tu número de tarjeta y el código de seguimiento que recibiste al registrar la queja.</div>""", unsafe_allow_html=True)

    if st.session_state.pop("aclaracion_ok", False):
        st.success("✅ ¡Información enviada correctamente! El estatus de tu queja cambió a 'En proceso'.")

    col1, col2, col3 = st.columns(3)
    with col1:
        q_folio = st.text_input("Folio de Queja (ej. Q-2026-0001)", max_chars=20).strip()
    with col2:
        q_tarjeta = st.text_input("Número de Tarjeta", max_chars=15).strip()
    with col3:
        q_codigo = st.text_input("Código de seguimiento", max_chars=12, placeholder="XXXX-XXXX").strip()

    if st.button("Buscar Queja"):
        st.session_state['queja_encontrada'] = None
        if not (q_folio and q_tarjeta and q_codigo):
            st.warning("Por favor ingrese folio, tarjeta y código de seguimiento.")
        else:
            try:
                encontrada = buscar_queja_segura(q_folio, q_tarjeta, q_codigo)
                if encontrada:
                    st.session_state['queja_encontrada'] = encontrada
                else:
                    st.error("Los datos no coinciden con ninguna queja. Verifica folio, tarjeta y código.")
            except LimiteExcedido as e:
                st.error(f"⚠️ {md(str(e))}")
            except Exception:
                logger.exception("Error en la consulta de estatus")
                st.error("No se pudo realizar la consulta. Intenta de nuevo en unos minutos.")

    queja = st.session_state.get('queja_encontrada')
    if queja:
        st.write("---")
        st.subheader(f"Estatus Actual: **{md(queja.get('estatus', ''))}**")
        st.write(f"**Folio:** {md(queja['folio'])} | **Tipo:** {md(queja.get('tipo_nombre', ''))} | **Quincena:** {md(queja.get('quincena_afectada', ''))}")
        if queja.get('nombre'):
            st.write(f"**Nombre:** {md(queja['nombre'])}")
        if queja.get('turno'):
            st.write(f"**Turno:** {md(queja['turno'])}")
        if queja.get('dias_incidencia'):
            st.write(f"**Días de Incidencia:** {md(queja['dias_incidencia'])}")
        if queja.get('monto_reclamado'):
            st.write(f"**Monto Reclamado:** \\${queja['monto_reclamado']:,.2f}")
        st.info(f"**Motivo registrado:** {md(queja.get('motivo', ''))}")

        db = obtener_conexion()
        comentarios_docs = db.collection("quejas").document(queja['id']).collection("comentarios").where("es_interno", "==", False).stream()
        comentarios = sorted(
            (c.to_dict() for c in comentarios_docs),
            key=lambda c: c.get('fecha') or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        )

        st.write("---")
        st.subheader("💬 Historial de Respuestas de RH")
        if comentarios:
            for c in comentarios:
                fecha = c.get('fecha')
                fecha_str = fecha.strftime('%d/%m/%Y %H:%M') if hasattr(fecha, 'strftime') else ""
                # No se muestran usuarios internos de RH a los empleados
                autor = "Tú" if str(c.get('usuario', '')).startswith("Empleado") else "Recursos Humanos"
                st.markdown(f"**{autor}** ({fecha_str}):")
                st.write(md(c.get('comentario', '')))
        else:
            st.caption("Aún no hay respuestas o notas de seguimiento registradas por RH.")

        if queja.get('estatus') == 'Requiere información':
            st.write("---")
            st.warning("⚠️ **Recursos Humanos ha solicitado información adicional para dar seguimiento a tu queja.**")

            with st.form(f"form_aclaracion_emp_{queja['id']}"):
                aclaracion_texto = st.text_area("Aclaración o mensaje para RH *", max_chars=2000, placeholder="Escriba aquí los detalles adicionales solicitados por Recursos Humanos...")

                st.write("📎 **Adjuntar evidencias adicionales (hasta 3 archivos opcionales):**")
                arch1 = st.file_uploader("Archivo adicional 1", type=["pdf", "png", "jpg", "jpeg"], key=f"ac_file1_{queja['id']}")
                arch2 = st.file_uploader("Archivo adicional 2", type=["pdf", "png", "jpg", "jpeg"], key=f"ac_file2_{queja['id']}")
                arch3 = st.file_uploader("Archivo adicional 3", type=["pdf", "png", "jpg", "jpeg"], key=f"ac_file3_{queja['id']}")

                btn_enviar_aclaracion = st.form_submit_button("Enviar Información Adicional")

            if btn_enviar_aclaracion:
                try:
                    registrar_aclaracion(queja['id'], aclaracion_texto, [f for f in (arch1, arch2, arch3) if f is not None])
                    st.session_state['queja_encontrada'] = None
                    st.session_state['aclaracion_ok'] = True
                    registrada = True
                except (ErrorValidacion, LimiteExcedido) as e:
                    st.error(f"⚠️ {md(str(e))}")
                    registrada = False
                except Exception:
                    logger.exception("Error al registrar la aclaración")
                    st.error("No se pudo guardar la información. Intenta de nuevo.")
                    registrada = False
                if registrada:
                    st.rerun()

# ---------------------------------------------------------
# MÓDULO 3: PANEL DE GESTIÓN RH
# ---------------------------------------------------------
elif modulo == "Panel RH / Gestión":
    st.header("🗂️ Panel de gestión de RH")

    for _k, _v in (("rh_logueado", False), ("rh_usuario", ""), ("rh_rol", ""), ("rh_inicio", 0.0), ("rh_ultimo", 0.0)):
        st.session_state.setdefault(_k, _v)

    def cerrar_sesion_rh():
        for _k in ("rh_logueado", "rh_usuario", "rh_rol", "rh_inicio", "rh_ultimo", "descarga_lista", "ultimo_wa_envio"):
            st.session_state.pop(_k, None)

    # Expiración de sesión por inactividad o por tiempo máximo
    _ahora = time.time()
    if st.session_state.rh_logueado:
        if (_ahora - st.session_state.rh_ultimo > INACTIVIDAD_SEG) or (_ahora - st.session_state.rh_inicio > SESION_MAX_SEG):
            cerrar_sesion_rh()
            st.warning("Tu sesión expiró por seguridad. Vuelve a iniciar sesión.")
            st.session_state.setdefault("rh_logueado", False)
        else:
            st.session_state.rh_ultimo = _ahora

    if not st.session_state.get("rh_logueado"):
        st.info("🔒 Acceso restringido al personal de Recursos Humanos.")

        with st.form("form_login_rh"):
            usuario_input = st.text_input("Usuario de RH", max_chars=40)
            password_input = st.text_input("Contraseña", type="password", max_chars=128)
            btn_login = st.form_submit_button("Iniciar Sesión")

        if btn_login:
            usuario_input = usuario_input.strip()
            clave_login = f"login:{usuario_input.lower()[:40]}"
            entro = False
            try:
                espera = esta_bloqueado(clave_login)
                if espera:
                    st.error(f"Demasiados intentos fallidos. Intenta de nuevo en {math.ceil(espera / 60)} minuto(s).")
                else:
                    usuarios = st.secrets.get("usuarios_rh", {})
                    datos_usuario = dict(usuarios[usuario_input]) if usuario_input and usuario_input in usuarios else {}
                    # Se verifica SIEMPRE (con relleno si el usuario no existe) para no delatar usuarios válidos
                    clave_ok = verificar_secreto(password_input, datos_usuario.get("password_hash", ""))
                    if clave_ok and datos_usuario:
                        limpiar(clave_login)
                        st.session_state.rh_logueado = True
                        st.session_state.rh_usuario = usuario_input
                        st.session_state.rh_rol = datos_usuario.get("rol", "RH")
                        st.session_state.rh_inicio = time.time()
                        st.session_state.rh_ultimo = time.time()
                        registrar_auditoria(obtener_conexion(), usuario_input, "login", "")
                        entro = True
                    else:
                        registrar_fallo(clave_login, max_fallos=5, ventana_seg=900, bloqueo_seg=900)
                        time.sleep(1)
                        st.error("Usuario o contraseña incorrectos.")
            except Exception:
                logger.exception("Error durante el inicio de sesión de RH")
                st.error("No se pudo validar el acceso. Intenta de nuevo.")
            if entro:
                st.rerun()

    else:
        col_info, col_logout = st.columns([4, 1])
        with col_info:
            st.success(f"Conectado como: **{md(st.session_state.rh_usuario)}** ({md(st.session_state.rh_rol)})")
        with col_logout:
            if st.button("Cerrar Sesión"):
                registrar_auditoria(obtener_conexion(), st.session_state.rh_usuario, "logout", "")
                cerrar_sesion_rh()
                st.rerun()

        st.write("---")

        db = obtener_conexion()

        if st.button("🔄 Actualizar bandeja"):
            cargar_quejas.clear()

        lista_q = cargar_quejas()
        df_quejas = pd.DataFrame(lista_q)

        if df_quejas.empty:
            st.info("No hay quejas registradas en el sistema.")
        else:
            st.subheader("Bandeja de Tickets y Filtros")

            quincenas_unicas = ["Todas"] + sorted(df_quejas['quincena_afectada'].dropna().unique().tolist(), reverse=True)
            filtro_quincena = st.selectbox("Filtrar Bandeja por Quincena Afectada", quincenas_unicas)

            if filtro_quincena != "Todas":
                df_filtrado = df_quejas[df_quejas['quincena_afectada'] == filtro_quincena]
            else:
                df_filtrado = df_quejas

            cols_ver = [c for c in ['nombre', 'folio', 'tarjeta_empleado', 'turno', 'tipo_nombre', 'quincena_afectada', 'monto_reclamado', 'dias_incidencia', 'estatus', 'fecha_creacion'] if c in df_filtrado.columns]
            st.dataframe(df_filtrado[cols_ver])

            st.write("---")
            st.subheader("🛠️ Gestor y Cierre de Ticket Seleccionado")

            filtrados = [q for q in lista_q if filtro_quincena == "Todas" or q.get('quincena_afectada') == filtro_quincena]
            tickets_por_etiqueta = {}
            for t in filtrados:
                etiqueta = f"{t.get('folio', 'S/F')} — {t.get('tarjeta_empleado', '')}"
                if etiqueta in tickets_por_etiqueta:
                    etiqueta += f" [{t['id'][:4]}]"
                tickets_por_etiqueta[etiqueta] = t

            if not tickets_por_etiqueta:
                st.warning("No hay tickets en la quincena seleccionada.")
            else:
                etiqueta_sel = st.selectbox("Seleccione un Folio para Atender o Cerrar", list(tickets_por_etiqueta.keys()))
                ticket_info = tickets_por_etiqueta[etiqueta_sel]

                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**Tarjeta:** {md(ticket_info.get('tarjeta_empleado'))}")
                c2.write(f"**Nombre:** {md(ticket_info.get('nombre'))}")
                c3.write(f"**Turno:** {md(ticket_info.get('turno', 'N/A'))}")
                c4.write(f"**Quincena:** {md(ticket_info.get('quincena_afectada'))}")

                st.write(f"**Tipo:** {md(ticket_info.get('tipo_nombre', ''))}")
                if ticket_info.get('dias_incidencia'):
                    st.write(f"**Días de Incidencia:** {md(ticket_info['dias_incidencia'])}")

                st.info(f"**Motivo del empleado:** {md(ticket_info.get('motivo'))}")
                st.write(f"**Estatus actual:** {md(ticket_info.get('estatus'))}")

                if ticket_info.get('telefono'):
                    texto_wh = f"Hola, te contactamos de Recursos Humanos respecto a tu queja de nómina con folio {ticket_info['folio']}."
                    link_admin_wa = link_whatsapp(ticket_info['telefono'], texto_wh)
                    if link_admin_wa:
                        st.link_button(f"💬 Enviar WhatsApp al empleado ({ticket_info['telefono']})", link_admin_wa)
                    else:
                        st.caption("El teléfono registrado no tiene un formato válido.")

                st.write("#### 📂 Archivos Adjuntos (privados en Google Drive)")
                adjuntos = [a.to_dict() for a in db.collection("quejas").document(ticket_info['id']).collection("adjuntos").stream()]

                if adjuntos:
                    for adj in adjuntos:
                        file_id = adj.get('drive_file_id') or adj.get('ruta_dropbox') or ''
                        nombre_a = adj.get('nombre_archivo', 'Archivo')
                        tipo_a = adj.get('tipo_archivo', 'Adjunto')

                        col_adj1, col_adj2 = st.columns([3, 1])
                        with col_adj1:
                            st.markdown(f"📄 **{md(tipo_a)}:** `{sanear_nombre(nombre_a)}`")
                        with col_adj2:
                            if RE_ID_DRIVE.fullmatch(str(file_id)):
                                if st.button("📥 Preparar descarga", key=f"prep_{file_id}"):
                                    try:
                                        contenido, mime = descargar_evidencia(file_id)
                                        st.session_state["descarga_lista"] = {"id": file_id, "data": contenido, "mime": mime, "nombre": sanear_nombre(nombre_a)}
                                        registrar_auditoria(db, st.session_state.rh_usuario, "descarga_adjunto", f"{ticket_info['folio']} / {sanear_nombre(nombre_a)}")
                                    except Exception:
                                        logger.exception("Error al descargar adjunto")
                                        st.error("No se pudo descargar el archivo.")
                                lista = st.session_state.get("descarga_lista")
                                if lista and lista["id"] == file_id:
                                    st.download_button("⬇️ Guardar archivo", data=lista["data"], file_name=lista["nombre"], mime=lista["mime"], key=f"dl_{file_id}")
                            else:
                                st.caption("Archivo no disponible")
                else:
                    st.caption("No hay archivos adjuntos en este ticket.")

                st.write("---")
                st.write("#### ✍️ Actualizar Estatus, Responder o Cerrar Ticket")

                estatus_actual = ticket_info.get('estatus')
                idx_actual = ESTADOS_QUEJA.index(estatus_actual) if estatus_actual in ESTADOS_QUEJA else 0

                with st.form(f"form_atencion_{ticket_info['id']}"):
                    nuevo_estatus = st.selectbox("Nuevo Estatus", ESTADOS_QUEJA, index=idx_actual)
                    nuevo_comentario = st.text_area("Respuesta o Nota de Seguimiento", max_chars=2000, placeholder="Escriba la respuesta oficial para el empleado o motivo de rechazo...")
                    es_nota_interna = st.checkbox("Marcar como Nota Interna (Privada para RH)")

                    btn_actualizar = st.form_submit_button("Guardar Cambios y Notificar")

                if btn_actualizar:
                    comentario = nuevo_comentario.strip()
                    if nuevo_estatus not in ESTADOS_QUEJA:
                        st.error("Estatus no válido.")
                    elif nuevo_estatus == 'Rechazada' and not comentario:
                        st.error("⚠️ Para cerrar un ticket como 'Rechazada', es obligatorio escribir la razón o motivo del rechazo en el cuadro de respuesta.")
                    else:
                        try:
                            q_ref = db.collection("quejas").document(ticket_info['id'])
                            actual = q_ref.get().to_dict() or {}          # estatus real en este momento
                            ahora_utc = datetime.datetime.now(datetime.timezone.utc)
                            lote = db.batch()
                            lote.update(q_ref, {"estatus": nuevo_estatus})
                            lote.set(q_ref.collection("historial_estatus").document(), {
                                "estatus_anterior": actual.get("estatus"),
                                "estatus_nuevo": nuevo_estatus,
                                "usuario_cambio": st.session_state.rh_usuario,
                                "comentario": comentario,
                                "fecha": ahora_utc,
                            })
                            if comentario:
                                lote.set(q_ref.collection("comentarios").document(), {
                                    "usuario": f"RH ({st.session_state.rh_usuario})",
                                    "comentario": comentario,
                                    "es_interno": bool(es_nota_interna),
                                    "fecha": ahora_utc,
                                })
                            lote.commit()
                            cargar_quejas.clear()
                            st.session_state['ultimo_wa_envio'] = {
                                'telefono': ticket_info.get('telefono'),
                                'folio': ticket_info['folio'],
                                'estatus': nuevo_estatus,
                                'comentario': "" if es_nota_interna else comentario,
                            }
                            guardado = True
                        except Exception:
                            logger.exception("Error al actualizar el ticket")
                            st.error("No se pudo actualizar el ticket. Intenta de nuevo.")
                            guardado = False
                        if guardado:
                            st.rerun()

                wa_data = st.session_state.get('ultimo_wa_envio')
                if wa_data and wa_data['folio'] == ticket_info['folio'] and wa_data['telefono']:
                    st.write("---")
                    st.success("📲 **Notificación lista para enviar al empleado:**")
                    msg_wa_cambio = f"Hola, te informamos que el estatus de tu queja con folio *{wa_data['folio']}* ha cambiado a: *{wa_data['estatus']}*."
                    if wa_data['comentario']:
                        msg_wa_cambio += "\n\n*Detalle / Respuesta de RH:* " + wa_data['comentario']
                    link_wa_cambio = link_whatsapp(wa_data['telefono'], msg_wa_cambio)
                    if link_wa_cambio:
                        st.link_button(f"👉 Enviar actualización por WhatsApp ({wa_data['telefono']})", link_wa_cambio)

            # -----------------------------------------------------------------
            # ZONA DE ADMINISTRACIÓN (solo rol Administrador)
            # -----------------------------------------------------------------
            if st.session_state.rh_rol == "Administrador":
                st.write("---")
                st.subheader("⚙️ Zona de Administración: Depuración de Folios")
                st.caption("Los folios se marcan como eliminados (borrado lógico): salen de la bandeja pero quedan en la base para auditoría.")

                with st.expander("🔴 Desplegar panel de eliminación múltiple", expanded=False):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        busqueda_del = st.text_input("🔍 Buscar por Folio o Tarjeta:", placeholder="Ej. Q-2026-0001...", key="busqueda_del_input").strip().lower()
                    with col_f2:
                        quincenas_del = sorted({str(q.get('quincena_afectada', '')) for q in lista_q if q.get('quincena_afectada')}, reverse=True)
                        filtro_periodo_del = st.selectbox("Filtrar por Quincena Afectada:", ["Todas las quincenas"] + quincenas_del, key="filtro_periodo_del_select")

                    candidatos = {}
                    for q_item in lista_q:
                        coincide_texto = (not busqueda_del) or busqueda_del in str(q_item.get('folio', '')).lower() or busqueda_del in str(q_item.get('tarjeta_empleado', '')).lower()
                        coincide_periodo = filtro_periodo_del == "Todas las quincenas" or filtro_periodo_del == q_item.get('quincena_afectada', '')
                        if coincide_texto and coincide_periodo:
                            etiqueta = f"{q_item.get('folio', 'S/F')} — {q_item.get('tarjeta_empleado', '')} — {q_item.get('quincena_afectada', '')} ({q_item.get('estatus', '')}) [{q_item['id'][:4]}]"
                            candidatos[etiqueta] = q_item['id']

                    st.markdown(f"**Folios coincidentes con el filtro:** {len(candidatos)}")

                    if not candidatos:
                        st.info("No hay folios que coincidan con los criterios de búsqueda.")
                    else:
                        def _seleccionar_todos(etiquetas):
                            st.session_state["adm_del_sel"] = list(etiquetas)

                        # Si cambió el filtro, descarta selecciones que ya no están visibles
                        st.session_state["adm_del_sel"] = [s for s in st.session_state.get("adm_del_sel", []) if s in candidatos]

                        st.button("☑️ Seleccionar todos los visibles", on_click=_seleccionar_todos, args=(list(candidatos.keys()),))
                        seleccion = st.multiselect("Folios a eliminar", options=list(candidatos.keys()), key="adm_del_sel")
                        _n_del = st.session_state.get("adm_del_n", 0)
                        confirmacion = st.text_input("Para confirmar escribe ELIMINAR", key=f"adm_del_confirm_{_n_del}")

                        if st.button("🔥 Eliminar folios seleccionados", type="primary"):
                            if st.session_state.rh_rol != "Administrador":
                                st.error("No tienes permiso para esta acción.")
                            elif not seleccion:
                                st.warning("⚠️ No has seleccionado ningún folio para eliminar.")
                            elif confirmacion.strip() != "ELIMINAR":
                                st.warning("Escribe la palabra ELIMINAR (en mayúsculas) para confirmar.")
                            else:
                                try:
                                    ahora_utc = datetime.datetime.now(datetime.timezone.utc)
                                    ids = [candidatos[s] for s in seleccion]
                                    for i in range(0, len(ids), 400):
                                        lote = db.batch()
                                        for doc_id in ids[i:i + 400]:
                                            lote.update(db.collection("quejas").document(doc_id), {
                                                "eliminada": True,
                                                "eliminada_por": st.session_state.rh_usuario,
                                                "eliminada_en": ahora_utc,
                                            })
                                        lote.commit()
                                    registrar_auditoria(db, st.session_state.rh_usuario, "eliminar_folios", ", ".join(s.split(" — ")[0] for s in seleccion))
                                    cargar_quejas.clear()
                                    st.session_state["adm_del_n"] = _n_del + 1
                                    eliminado = len(ids)
                                except Exception:
                                    logger.exception("Error al eliminar folios")
                                    st.error("No se pudieron eliminar los folios.")
                                    eliminado = 0
                                if eliminado:
                                    st.success(f"Se marcaron como eliminados {eliminado} folio(s).")
                                    st.rerun()
