import calendar
import csv
import io
import json
import zipfile
import contextlib
import datetime
import html
import logging
import math
import os
import time

import pandas as pd
import streamlit as st

from comprobante import generar_pdf
from database import obtener_conexion, obtener_catálogo_tipos, verificar_queja_duplicada
from limitador import esta_bloqueado, limpiar, registrar_fallo
from plantillas import MARCA_COMPLETAR, PLANTILLAS, rellenar
from roles import ICONOS_EVENTO, limpiar_queja_para_rol, puede, quejas_visibles_para_rol, rol_valido
from seguridad import (
    RE_ID_DRIVE, ErrorValidacion, LimiteExcedido,
    escapar_md as md, formatear_codigo, link_whatsapp, sanear_nombre,
    validar_nombre, validar_tarjeta, validar_telefono, verificar_secreto,
)
from ui import (
    CLAVE_CSS_ESTADO, CSS, ESTADOS_ORDEN, badge, css_ancho, enlaces_legales_lateral, hero,
    icono_estado, notificacion_item, notificaciones_cabecera, notificaciones_lista,
    notificaciones_vacias, pie_legal, stepper_estatus, stepper_pasos, tarjeta, tarjeta_codigos,
)
from utils import (
    TIPOS_CON_DIAS, buscar_queja_segura, cancelar_solicitud_control, cargar_quejas,
    crear_solicitud_control, descargar_evidencia, fecha_local, marcar_notificaciones_vistas,
    obtener_notificaciones, obtener_solicitudes_control, registrar_aclaracion,
    registrar_auditoria, registrar_lote, responder_solicitud_control, validar_queja,
)

logger = logging.getLogger("quejas")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
URL_TERMINOS = "https://github.com/DanyFlow/Sistema-quejas-HGO/blob/main/TERMS.md"
URL_PRIVACIDAD = "https://github.com/DanyFlow/Sistema-quejas-HGO/blob/main/PRIVACY.md"
SELLO_COMPROBANTE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sello_recibido.png")
SELLO_ANGULO = 45   # grados (positivo = gira a la izquierda, negativo = a la derecha, 0 = derecho)

INACTIVIDAD_SEG = 30 * 60      # 30 min sin actividad -> cierra sesión del panel
SESION_MAX_SEG = 8 * 60 * 60   # 8 h máximo aunque haya actividad
ESTADOS_QUEJA = ESTADOS_ORDEN
ESTADOS_CERRADOS = ("Resuelto", "Rechazada")

TURNOS = ["Matutino", "Vespertino", "Nocturno", "Jornada Acumulada Diurna", "Jornada Acumulada Nocturna"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
PERIODOS = ["Q1 (Días 1-15)", "Q2 (Días 16-fin)"]
ETIQUETA_PERIODO = {"Q1 (Días 1-15)": "Del 1 al 15", "Q2 (Días 16-fin)": "Del 16 al fin de mes"}
MAX_QUEJAS = 5
FORMATOS_ARCHIVO = ["pdf", "png", "jpg", "jpeg"]


def _config_app():
    try:
        return dict(st.secrets.get("app", {}))
    except Exception:
        return {}


_CFG = _config_app()
NOMBRE_EMPRESA = str(_CFG.get("nombre_empresa", ""))
CONTACTO_AYUDA = str(_CFG.get("contacto_ayuda", ""))

st.set_page_config(page_title="Quejas de nómina", page_icon="📋", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Navegación
# ---------------------------------------------------------------------------
PAGINAS = ["Inicio", "Registrar una queja", "Consultar mi queja", "Acceso RH"]
st.session_state.setdefault("pagina", "Inicio")


def ir_a(pagina):
    st.session_state["pagina"] = pagina


if os.path.exists("logo.png"):          # logo opcional: pon un logo.png en la raíz del repositorio
    st.logo("logo.png")
if NOMBRE_EMPRESA:
    st.sidebar.markdown(f"**{md(NOMBRE_EMPRESA)}**")
st.sidebar.markdown("### 📋 Menú")


# Navegación con botones uniformes y alto contraste para tema claro y oscuro
st.markdown("""
<style>
/* Estilo base para los botones del menú lateral */
[data-testid="stSidebar"] div.stButton > button {
    width: 100% !important;
    min-height: 3.15rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    
    /* Colores y visibilidad para Tema Claro */
    background-color: #F0F2F6 !important; /* Fondo gris claro suave */
    color: #1F2937 !important;            /* Texto oscuro de alto contraste */
    border: 1px solid #D1D5DB !important;  /* Borde visible */
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease-in-out !important;
}

/* El texto interno (<p>) heredaba el color claro de la barra lateral: se fuerza el del botón */
[data-testid="stSidebar"] div.stButton > button p,
[data-testid="stSidebar"] div.stButton > button div { color: inherit !important; }

/* Página activa */
[data-testid="stSidebar"] div.stButton > button[kind="primary"],
[data-testid="stSidebar"] div.stButton > button[data-testid="stBaseButton-primary"] {
    background: #1d4f9e !important;
    color: #ffffff !important;
    border-color: #1d4f9e !important;
}

/* Efecto al pasar el cursor (Hover) */
[data-testid="stSidebar"] div.stButton > button:hover {
    background-color: #E5E7EB !important; /* Gris un poco más oscuro */
    color: #111827 !important;
    border-color: #9CA3AF !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
}

/* Estado activo / enfocado (Focus/Active) */
[data-testid="stSidebar"] div.stButton > button:focus, 
[data-testid="stSidebar"] div.stButton > button:active {
    background-color: #D1D5DB !important;
    color: #111827 !important;
    border-color: #4B5563 !important;
    box-shadow: none !important;
}

/* Soporte automático para usuarios con Tema Oscuro (Dark Mode) */
@media (prefers-color-scheme: dark) {
    [data-testid="stSidebar"] div.stButton > button {
        background-color: #262730 !important;
        color: #FAFAFA !important;
        border: 1px solid #4B5563 !important;
    }
    [data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #31333F !important;
        border-color: #6B7280 !important;
    }
}
</style>
""", unsafe_allow_html=True)

for _opcion, _etiqueta in [
    ("Inicio", "🏠 Inicio"),
    ("Registrar una queja", "📝 Registrar una queja"),
    ("Consultar mi queja", "🔎 Consultar una queja"),
    ("Acceso RH", "🔐 Acceso RH"),
]:
    st.sidebar.button(
        _etiqueta,
        key=f"menu_{_opcion.lower().replace(' ', '_')}",
        type="primary" if st.session_state.get("pagina") == _opcion else "secondary",
        use_container_width=True,
        on_click=ir_a,
        args=(_opcion,),
    )

st.sidebar.markdown(enlaces_legales_lateral(URL_PRIVACIDAD, URL_TERMINOS), unsafe_allow_html=True)


def boton_inicio():
    st.button("🏠 Inicio", key="btn_inicio", on_click=ir_a, args=("Inicio",))


# ===========================================================================
# PÁGINA: INICIO
# ===========================================================================
def pagina_inicio():
    st.markdown(css_ancho(1100), unsafe_allow_html=True)
    st.markdown(hero(
        "Portal de atención · Recursos Humanos · Hospital General de Occidente ",
        "Quejas por descuento en la nómina/Bonos no pagados",
        "Si tu pago llegó con un descuento y consideras que es un error, cuéntanoslo aquí. Es rápido y puedes ver el avance de tu caso cuando quieras.",
    ), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(tarjeta("📝", "Registrar una queja", "Cuéntanos qué pasó con tu pago"), unsafe_allow_html=True)
        st.button("➕ Registrar una queja", key="home_registrar", on_click=ir_a, args=("Registrar una queja",))
    with c2:
        st.markdown(tarjeta("🔎", "Consultar mi queja", "Mira cómo va tu caso con tu folio y tu clave."), unsafe_allow_html=True)
        st.button("🔎 Consultar mi queja", key="home_consultar", on_click=ir_a, args=("Consultar mi queja",))

    st.subheader("¿Cómo funciona?")
    a, b, c = st.columns(3)
    a.markdown(tarjeta("1️⃣", "Llena tus datos para comenzar", "Tu tarjeta, tu nombre y un teléfono para contactarte."), unsafe_allow_html=True)
    b.markdown(tarjeta("2️⃣", "Guarda tu folio y tu clave", "Al terminar te damos un comprobante en PDF."), unsafe_allow_html=True)
    c.markdown(tarjeta("3️⃣", "Consulta cuando quieras", "Entra a «Consultar mi queja» y mira el avance."), unsafe_allow_html=True)

    if CONTACTO_AYUDA:
        st.info(f"💬 ¿Necesitas ayuda? {md(CONTACTO_AYUDA)}")


# ===========================================================================
# PÁGINA: REGISTRAR UNA QUEJA (3 pasos)
# ===========================================================================
def _datos_vacios():
    return {"tarjeta": "", "nombre": "", "telefono": "", "turno": TURNOS[0]}


def _queja_vacia(opciones_tipos):
    st.session_state["reg_contador"] = st.session_state.get("reg_contador", 0) + 1
    return {
        "uid": st.session_state["reg_contador"],     # clave estable de los widgets (aunque se quiten quejas)
        "tipo_nombre": list(opciones_tipos.keys())[0] if opciones_tipos else "",
        "tipo_id": "", "anio": datetime.datetime.now().year, "mes": "Enero", "periodo": PERIODOS[0],
        "quincena": "", "monto": 0.0, "dias_incidencia_lista": [], "motivo": "", "evidencias": [], "talon": None,
    }


def _reiniciar_registro():
    for k in ("reg_paso", "reg_datos", "lista_quejas_temp"):
        st.session_state.pop(k, None)


def _nueva_queja():
    st.session_state.pop("resultado_registro", None)
    st.session_state.pop("resultado_fecha", None)


def _armar_lote():
    """Une los datos del empleado (paso 1) con cada queja (paso 2)."""
    datos = st.session_state.reg_datos
    lote = []
    for q in st.session_state.lista_quejas_temp:
        item = {**q, "tarjeta": datos["tarjeta"], "nombre": datos["nombre"],
                "telefono": datos["telefono"], "turno": datos["turno"]}
        especial = item["tipo_nombre"] in TIPOS_CON_DIAS
        item["dias_str"] = ", ".join(str(d) for d in item["dias_incidencia_lista"]) if especial else None
        lote.append(item)
    return lote


def _texto_quincena(anio, mes, periodo):
    mes_txt = MESES[mes - 1].lower()
    if periodo.startswith("Q1"):
        return f"del 1 al 15 de {mes_txt} de {anio}"
    return f"del 16 al {calendar.monthrange(anio, mes)[1]} de {mes_txt} de {anio}"


def registrar_paso1():
    datos = st.session_state.setdefault("reg_datos", _datos_vacios())
    with st.container(border=True):
        st.subheader("Paso 1 de 3 · Tus datos")
        st.caption("Nos sirven para identificarte y poder contactarte. Los campos con * son obligatorios.")
        datos["tarjeta"] = st.text_input("Tu número de tarjeta de empleado *", value=datos["tarjeta"], max_chars=15,
                                         key="reg_tarjeta", placeholder="Ej. 123456").strip()
        datos["nombre"] = st.text_input("Tu nombre completo *", value=datos["nombre"], max_chars=60,
                                        key="reg_nombre", placeholder="Ej. María López Pérez").strip()
        datos["telefono"] = st.text_input("Tu teléfono celular (WhatsApp) *", value=datos["telefono"], max_chars=15,
                                          key="reg_tel", placeholder="Ej. 3312345678",
                                          help="10 dígitos, sin espacios ni guiones.").strip()
        idx = TURNOS.index(datos["turno"]) if datos["turno"] in TURNOS else 0
        datos["turno"] = st.selectbox("Tu turno *", TURNOS, index=idx, key="reg_turno")

    if st.button("Siguiente ➜", type="primary", key="reg_sig1"):
        errores = []
        if not validar_tarjeta(datos["tarjeta"]):
            errores.append("Revisa tu número de tarjeta: de 3 a 15 letras o números, sin espacios.")
        if not validar_nombre(datos["nombre"]):
            errores.append("Revisa tu nombre: solo letras y espacios (de 3 a 60 caracteres).")
        if not validar_telefono(datos["telefono"]):
            errores.append("Revisa tu teléfono: deben ser 10 dígitos, por ejemplo 3312345678.")
        if errores:
            for e in errores:
                st.error(f"⚠️ {e}")
        else:
            st.session_state.reg_paso = 2
            st.rerun()


def formulario_queja(i, opciones_tipos):
    quejas = st.session_state.lista_quejas_temp
    q = quejas[i]
    uid = q["uid"]
    n = len(quejas)

    if n > 1:
        if st.button(f"🗑️ Quitar la queja {i + 1}", key=f"quitar_q_{uid}"):
            quejas.pop(i)
            st.rerun()

    st.markdown("##### 1. ¿Qué pasó?")
    tipos = list(opciones_tipos.keys())
    idx_tipo = tipos.index(q["tipo_nombre"]) if q["tipo_nombre"] in tipos else 0
    tipo = st.selectbox("Tipo de queja *", tipos, index=idx_tipo, key=f"tipo_{uid}")

    st.markdown("##### 2. ¿De qué quincena es el pago?")
    anio_actual = datetime.datetime.now().year
    anios = list(range(anio_actual - 3, anio_actual + 2))
    c1, c2 = st.columns(2)
    with c1:
        anio = st.selectbox("Año *", anios, index=anios.index(q["anio"]) if q["anio"] in anios else anios.index(anio_actual), key=f"anio_{uid}")
    with c2:
        mes_nombre = st.selectbox("Mes *", MESES, index=MESES.index(q["mes"]) if q["mes"] in MESES else 0, key=f"mes_{uid}")
    etiquetas_periodo = list(ETIQUETA_PERIODO.values())
    periodo_elegido = st.segmented_control(
        "Periodo *", options=etiquetas_periodo,
        default=ETIQUETA_PERIODO.get(q["periodo"], etiquetas_periodo[0]),
        selection_mode="single", key=f"periodo_seg_{uid}"
    ) or etiquetas_periodo[0]
    periodo = next(k for k, v in ETIQUETA_PERIODO.items() if v == periodo_elegido)
    mes_num = MESES.index(mes_nombre) + 1
    quincena = f"{anio}-{mes_num:02d}{'Q1' if periodo.startswith('Q1') else 'Q2'}"
    st.caption(f"📅 Quincena: {_texto_quincena(anio, mes_num, periodo)}")

    monto = st.number_input("¿De cuánto es el descuento o el pago que falta? ($) *", value=float(q["monto"]), min_value=0.0,
                            max_value=1000000.0, step=50.0, key=f"monto_{uid}")

    dias = []
    if tipo in TIPOS_CON_DIAS:
        st.markdown("##### 3. ¿Qué días fueron?")
        st.caption("Selecciona los días de esta incidencia. Puedes elegir hasta 5.")
        if periodo.startswith("Q1"):
            rango = list(range(1, 16))
        else:
            rango = list(range(16, calendar.monthrange(anio, mes_num)[1] + 1))
        seleccion_dias = st.pills(
            "Días de la incidencia", options=rango, selection_mode="multi",
            default=[d for d in q["dias_incidencia_lista"] if d in rango],
            key=f"dias_{uid}",
        ) or []
        dias = sorted(int(d) for d in seleccion_dias)
        if len(dias) > 5:
            st.warning("⚠️ Máximo 5 días por queja.")

    st.markdown("##### Documentos que prueben tu queja")
    st.caption("Puedes tomarle una foto con tu celular. Formatos: PDF, PNG o JPG, de hasta 5 MB cada uno.")
    subidas = st.file_uploader("📎 Evidencias * (hasta 5 archivos)", type=FORMATOS_ARCHIVO,
                               accept_multiple_files=True, key=f"evid_{uid}")
    evidencias = list(subidas) if subidas else q["evidencias"]
    if evidencias and not subidas:
        st.success("📎 Ya adjuntaste: " + ", ".join(sanear_nombre(e.name) for e in evidencias))
        if st.button("Quitar estos archivos", key=f"quitar_evid_{uid}"):
            q["evidencias"] = []
            st.rerun()
    talon_subido = st.file_uploader("🧾 Tu talón de pago (opcional)", type=FORMATOS_ARCHIVO, key=f"talon_{uid}")
    talon = talon_subido if talon_subido is not None else q["talon"]
    if talon is not None and talon_subido is None:
        st.success(f"🧾 Ya adjuntaste: {sanear_nombre(talon.name)}")
        if st.button("Quitar el talón", key=f"quitar_talon_{uid}"):
            q["talon"] = None
            st.rerun()

    motivo = st.text_area("Cuéntanos qué pasó *", value=q["motivo"], max_chars=2000, key=f"motivo_{uid}",
                          placeholder="Ej. Me descontaron un día que sí trabajé...").strip()

    quejas[i] = {
        "uid": uid, "tipo_nombre": tipo, "tipo_id": opciones_tipos[tipo]["id"], "anio": int(anio), "mes": mes_nombre,
        "periodo": periodo, "quincena": quincena, "monto": monto, "dias_incidencia_lista": sorted(dias),
        "motivo": motivo, "evidencias": evidencias, "talon": talon,
    }


def registrar_paso2(opciones_tipos):
    if not st.session_state.get("lista_quejas_temp"):
        st.session_state.lista_quejas_temp = [_queja_vacia(opciones_tipos)]
    quejas = st.session_state.lista_quejas_temp
    n = len(quejas)

    st.subheader("Paso 2 de 3 · Tu queja")
    if n > 1:
        st.caption(f"Estás registrando {n} quejas (máximo {MAX_QUEJAS}).")
        pestanas = st.tabs([f"Queja {i + 1}" for i in range(n)])
    for i in range(n):
        contexto = pestanas[i] if n > 1 else contextlib.nullcontext()
        with contexto:
            with st.container(border=True):
                formulario_queja(i, opciones_tipos)

    if st.button("➕ Agregar otra queja", key="reg_agregar", disabled=(len(st.session_state.lista_quejas_temp) >= MAX_QUEJAS)):
        st.session_state.lista_quejas_temp.append(_queja_vacia(opciones_tipos))
        st.rerun()

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅ Atrás", key="reg_atras2"):
            st.session_state.reg_paso = 1
            st.rerun()
    with c2:
        revisar = st.button("Revisar mi queja ➜", type="primary", key="reg_revisar")

    if revisar:
        errores, vistos = [], set()
        for idx, item in enumerate(_armar_lote(), start=1):
            problemas = validar_queja(item)
            errores.extend(f"Queja {idx}: {p}" for p in problemas)
            if not problemas:
                clave = (item["tarjeta"], item["tipo_id"], item["quincena"])
                if clave in vistos:
                    errores.append(f"Queja {idx}: está repetida en este mismo trámite.")
                elif verificar_queja_duplicada(*clave):
                    errores.append(f"Queja {idx}: ya existe una queja abierta de ese tipo para esa quincena.")
                vistos.add(clave)
        if errores:
            for e in errores:
                st.error(f"⚠️ {md(e)}")
        else:
            st.session_state.reg_paso = 3
            st.rerun()


def registrar_paso3():
    lote = _armar_lote()
    st.subheader("Paso 3 de 3 · Revisa y envía")
    st.caption("Lee con calma. Si algo está mal, regresa y corrígelo.")

    for idx, d in enumerate(lote, start=1):
        with st.container(border=True):
            st.markdown(f"**Queja {idx}: {md(d['tipo_nombre'])}**")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Tarjeta:** {md(d['tarjeta'])}")
                st.write(f"**Nombre:** {md(d['nombre'])}")
                st.write(f"**Teléfono:** {md(d['telefono'])}")
                st.write(f"**Turno:** {md(d['turno'])}")
            with c2:
                st.write(f"**Quincena:** {md(_texto_quincena(d['anio'], MESES.index(d['mes']) + 1, d['periodo']))}")
                st.write(f"**Monto:** \\${d['monto']:,.2f}")
                if d.get("dias_str"):
                    st.write(f"**Días:** {md(d['dias_str'])}")
            nombres = ", ".join(sanear_nombre(e.name) for e in d["evidencias"])
            st.write(f"📎 **Evidencias:** {md(nombres)}")
            if d["talon"] is not None:
                st.write(f"🧾 **Talón:** {md(sanear_nombre(d['talon'].name))}")
            st.write(f"**Lo que pasó:** {md(d['motivo'])}")

    st.info(f"🔒 Al enviar tu queja aceptas el [Aviso de privacidad]({URL_PRIVACIDAD}) y las "
            f"[Condiciones de servicio]({URL_TERMINOS}).")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅ Corregir", key="reg_corregir"):
            st.session_state.reg_paso = 2
            st.rerun()
    with c2:
        enviar = st.button("✅ Enviar mi queja", type="primary", key="reg_enviar")

    if enviar:
        resultado = None
        try:
            with st.spinner("Enviando tu queja y subiendo tus archivos..."):
                resultado = registrar_lote(lote)
        except (ErrorValidacion, LimiteExcedido) as e:
            st.error(f"⚠️ {md(str(e))}")
        except Exception:
            logger.exception("Error al registrar el lote de quejas")
            st.error("No se pudo enviar tu queja. Intenta de nuevo; si sigue igual, avisa a Recursos Humanos.")
        if resultado:
            st.session_state.resultado_registro = resultado
            st.session_state.resultado_fecha = fecha_local(datetime.datetime.now(datetime.timezone.utc))
            _reiniciar_registro()      # no dejar datos personales en la sesión
            st.rerun()


def mostrar_resultado():
    resultado = st.session_state["resultado_registro"]
    st.success("✅ ¡Listo! Tu queja fue registrada.")
    st.warning("**Guarda tu folio y tu clave.** Los necesitas, junto con tu número de tarjeta, para consultar tu queja. "
               "Por seguridad la clave no se vuelve a mostrar.")
    for r in resultado:
        st.markdown(tarjeta_codigos(r["tipo"], r["folio"], formatear_codigo(r["codigo"])), unsafe_allow_html=True)

    pdf = generar_pdf(
        resultado, empresa=NOMBRE_EMPRESA, fecha_txt=st.session_state.get("resultado_fecha", ""),
        pie_lineas=[f"Aviso de privacidad: {URL_PRIVACIDAD}", f"Condiciones de servicio: {URL_TERMINOS}"],
        sello=SELLO_COMPROBANTE, sello_angulo=SELLO_ANGULO,
    )
    st.download_button("📄 Descargar mi comprobante (PDF)", data=pdf, file_name="comprobante_queja.pdf",
                       mime="application/pdf", type="primary")
    c1, c2 = st.columns(2)
    with c1:
        st.button("➕ Registrar otra queja", key="res_otra", on_click=_nueva_queja)
    with c2:
        st.button("🔎 Consultar mi queja", key="res_consultar", on_click=ir_a, args=("Consultar mi queja",))


def pagina_registrar():
    st.markdown(css_ancho(920), unsafe_allow_html=True)
    boton_inicio()
    st.header("✍️ Registrar una queja")

    if st.session_state.get("resultado_registro"):
        mostrar_resultado()
        return

    opciones_tipos = {item["nombre"]: item for item in obtener_catálogo_tipos()}
    paso = st.session_state.setdefault("reg_paso", 1)
    st.markdown(stepper_pasos(paso, ["Tus datos", "Tu queja", "Revisar y enviar"]), unsafe_allow_html=True)

    if paso == 1:
        registrar_paso1()
    elif paso == 2:
        registrar_paso2(opciones_tipos)
    else:
        registrar_paso3()


# ===========================================================================
# PÁGINA: CONSULTAR MI QUEJA
# ===========================================================================
def pagina_consultar():
    st.markdown(css_ancho(920), unsafe_allow_html=True)
    boton_inicio()
    st.header("🔎 Consultar mi queja")
    st.markdown('<div class="section-intro">Escribe tu folio, tu número de tarjeta y la clave que te dimos al registrar tu queja.</div>',
                unsafe_allow_html=True)

    if st.session_state.pop("aclaracion_ok", False):
        st.success("✅ ¡Gracias! Recibimos tu información. Tu queja sigue en revisión.")

    with st.container(border=True):
        q_folio = st.text_input("Tu folio", max_chars=20, placeholder="Ej. Q-2026-0001").strip()
        q_tarjeta = st.text_input("Tu número de tarjeta", max_chars=15, placeholder="Ej. 123456").strip()
        q_codigo = st.text_input("Tu clave para consultar", max_chars=12, placeholder="Ej. AB12-CD34").strip()
        buscar = st.button("🔎 Consultar", type="primary", key="btn_consultar")

    if buscar:
        st.session_state["queja_encontrada"] = None
        if not (q_folio and q_tarjeta and q_codigo):
            st.warning("Escribe tu folio, tu tarjeta y tu clave.")
        else:
            try:
                encontrada = buscar_queja_segura(q_folio, q_tarjeta, q_codigo)
                if encontrada:
                    st.session_state["queja_encontrada"] = encontrada
                else:
                    st.error("Los datos no coinciden. Revisa tu folio, tu tarjeta y tu clave.")
            except LimiteExcedido as e:
                st.error(f"⚠️ {md(str(e))}")
            except Exception:
                logger.exception("Error en la consulta de estatus")
                st.error("No pudimos hacer la consulta. Intenta de nuevo en unos minutos.")

    queja = st.session_state.get("queja_encontrada")
    if not queja:
        return

    estatus = queja.get("estatus", "")
    st.markdown(
        f'<div class="card"><div class="muted">Folio</div><div class="big"><b>{html.escape(str(queja["folio"]))}</b> &nbsp; {badge(estatus)}</div></div>',
        unsafe_allow_html=True)
    st.markdown(stepper_estatus(estatus), unsafe_allow_html=True)

    with st.container(border=True):
        st.write(f"**Tipo de queja:** {md(queja.get('tipo_nombre', ''))}")
        st.write(f"**Quincena:** {md(queja.get('quincena_afectada', ''))}")
        if queja.get("nombre"):
            st.write(f"**Nombre:** {md(queja['nombre'])}")
        if queja.get("turno"):
            st.write(f"**Turno:** {md(queja['turno'])}")
        if queja.get("dias_incidencia"):
            st.write(f"**Días de la incidencia:** {md(queja['dias_incidencia'])}")
        if queja.get("monto_reclamado"):
            st.write(f"**Monto:** \\${queja['monto_reclamado']:,.2f}")
        st.write(f"**Lo que registraste:** {md(queja.get('motivo', ''))}")

    db = obtener_conexion()
    docs = db.collection("quejas").document(queja["id"]).collection("comentarios").where("es_interno", "==", False).stream()
    minimo = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    comentarios = sorted((c.to_dict() for c in docs), key=lambda c: c.get("fecha") or minimo)

    st.subheader("💬 Respuestas de Recursos Humanos")
    if comentarios:
        for c in comentarios:
            propio = str(c.get("usuario", "")).startswith("Empleado")     # no se muestran usuarios internos de RH
            with st.container(border=True):
                st.markdown(f"**{'Tú' if propio else 'Recursos Humanos'}** · {fecha_local(c.get('fecha'))}")
                st.write(md(c.get("comentario", "")))
    else:
        st.caption("Todavía no hay respuestas. Cuando Recursos Humanos te escriba, lo verás aquí.")

    if estatus == "Requiere información":
        st.warning("⚠️ **Recursos Humanos necesita más información para seguir con tu queja.** Respóndele aquí abajo.")
        with st.form(f"form_aclaracion_emp_{queja['id']}"):
            texto = st.text_area("Tu respuesta para Recursos Humanos *", max_chars=2000,
                                 placeholder="Escribe aquí lo que te pidieron...")
            st.caption("Si te pidieron documentos, puedes adjuntar hasta 3 (PDF, PNG o JPG).")
            arch1 = st.file_uploader("Archivo 1", type=FORMATOS_ARCHIVO, key=f"ac_file1_{queja['id']}")
            arch2 = st.file_uploader("Archivo 2", type=FORMATOS_ARCHIVO, key=f"ac_file2_{queja['id']}")
            arch3 = st.file_uploader("Archivo 3", type=FORMATOS_ARCHIVO, key=f"ac_file3_{queja['id']}")
            enviar = st.form_submit_button("📤 Enviar mi respuesta", type="primary")

        if enviar:
            registrada = False
            try:
                registrar_aclaracion(queja["id"], texto, [f for f in (arch1, arch2, arch3) if f is not None])
                st.session_state["queja_encontrada"] = None
                st.session_state["aclaracion_ok"] = True
                registrada = True
            except (ErrorValidacion, LimiteExcedido) as e:
                st.error(f"⚠️ {md(str(e))}")
            except Exception:
                logger.exception("Error al registrar la aclaración")
                st.error("No se pudo guardar tu respuesta. Intenta de nuevo.")
            if registrada:
                st.rerun()


# ===========================================================================
# PÁGINA: ACCESO RH (panel interno)
# ===========================================================================
def permiso(accion):
    return puede(st.session_state.get("rh_rol", ""), accion)


def cerrar_sesion_rh():
    for k in ("rh_logueado", "rh_usuario", "rh_rol", "rh_inicio", "rh_ultimo", "descarga_lista",
              "ultimo_wa_envio", "mostrar_toast_login", "aviso_panel", "rh_filtro", "rh_ticket_id"):
        st.session_state.pop(k, None)


def login_rh():
    st.info("🔒 Acceso solo para el personal autorizado.")
    with st.form("form_login_rh"):
        usuario_input = st.text_input("Usuario", max_chars=40)
        password_input = st.text_input("Contraseña", type="password", max_chars=128)
        btn_login = st.form_submit_button("Entrar", type="primary")

    if not btn_login:
        return
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
                rol_usuario = str(datos_usuario.get("rol", ""))
                if not rol_valido(rol_usuario):
                    logger.warning("Inicio de sesión rechazado: el usuario %s tiene un rol no válido", usuario_input)
                    st.error("Tu usuario no tiene un rol válido asignado. Contacta al administrador.")
                else:
                    limpiar(clave_login)
                    st.session_state.rh_logueado = True
                    st.session_state.rh_usuario = usuario_input
                    st.session_state.rh_rol = rol_usuario
                    st.session_state.rh_inicio = time.time()
                    st.session_state.rh_ultimo = time.time()
                    st.session_state.mostrar_toast_login = True
                    registrar_auditoria(obtener_conexion(), usuario_input, "login", "")
                    entro = True
            else:
                registrar_fallo(clave_login, max_fallos=5, ventana_seg=900, bloqueo_seg=900)
                time.sleep(1)
                st.error("Usuario o contraseña incorrectos.")
    except Exception:
        logger.exception("Error durante el inicio de sesión")
        st.error("No se pudo validar el acceso. Intenta de nuevo.")
    if entro:
        st.rerun()


def _hace(valor):
    """Texto corto tipo 'hace 5 min' a partir de una fecha UTC."""
    if not hasattr(valor, "astimezone"):
        return ""
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=datetime.timezone.utc)
    seg = (datetime.datetime.now(datetime.timezone.utc) - valor).total_seconds()
    if seg < 60:
        return "hace un momento"
    if seg < 3600:
        return f"hace {int(seg // 60)} min"
    if seg < 86400:
        return f"hace {int(seg // 3600)} h"
    dias = int(seg // 86400)
    return "ayer" if dias == 1 else f"hace {dias} días"


def bloque_notificaciones(usuario, rol):
    try:
        notifs = obtener_notificaciones(usuario, rol)
    except Exception:
        logger.exception("No se pudieron cargar las notificaciones")
        notifs = []

    if st.session_state.pop("mostrar_toast_login", False) and notifs:
        st.toast(f"🔔 Tienes {len(notifs)} novedad(es) sin revisar")

    if not notifs:
        st.markdown(notificaciones_vacias(), unsafe_allow_html=True)
        return

    with st.container(border=True):
        col_titulo, col_boton = st.columns([3, 1])
        with col_titulo:
            st.markdown(notificaciones_cabecera(len(notifs)), unsafe_allow_html=True)
        with col_boton:
            marcar = st.button("✅ Marcar como vistas", key="btn_marcar_vistas")
        if marcar:
            marcar_notificaciones_vistas(usuario, max(n["fecha"] for n in notifs))
            st.rerun()

        try:
            ordenadas = sorted(notifs, key=lambda n: n.get("fecha"), reverse=True)   # lo más nuevo primero
        except Exception:
            ordenadas = notifs
        items = [
            notificacion_item(n.get("tipo"), ICONOS_EVENTO.get(n.get("tipo"), "•"), n.get("detalle", ""),
                              _hace(n.get("fecha")), fecha_local(n.get("fecha")))
            for n in ordenadas
        ]
        st.markdown(notificaciones_lista(items), unsafe_allow_html=True)


def _set_filtro(valor):
    st.session_state["rh_filtro"] = valor


def _coincide_filtro(q, filtro):
    estatus = q.get("estatus")
    if filtro == "Todas":
        return True
    if filtro == "cerradas":
        return estatus in ESTADOS_CERRADOS
    if filtro == "control":
        return q.get("solicitud_control_estado") == "Pendiente"
    return estatus == filtro


def _dias_abierto(q):
    if q.get("estatus") in ESTADOS_CERRADOS:
        return None
    f = q.get("fecha_creacion")
    if not hasattr(f, "astimezone"):
        return None
    return (datetime.datetime.now(datetime.timezone.utc) - f).days


def bandeja(lista_q):
    """Tarjetas-filtro + tabla. Devuelve los tickets visibles con el filtro actual."""
    st.subheader("📥 Bandeja de tickets")
    st.session_state.setdefault("rh_filtro", "Todas")
    actual = st.session_state["rh_filtro"]
    definiciones = [("Todas", "📚 Todas"), ("Pendiente", "🟡 Pendientes"), ("En proceso", "🔵 En proceso"),
                    ("Requiere información", "🟠 Falta info"), ("cerradas", "✅ Cerradas"), ("control", "🕒 En Control")]
    for col, (i, (valor, etiqueta)) in zip(st.columns(len(definiciones)), enumerate(definiciones)):
        n = sum(1 for q in lista_q if _coincide_filtro(q, valor))
        with col:
            st.button(f"{etiqueta} ({n})", key=f"filtro_{i}", type="primary" if actual == valor else "secondary",
                      on_click=_set_filtro, args=(valor,))

    quincenas = sorted({q["quincena_afectada"] for q in lista_q if q.get("quincena_afectada")}, reverse=True)
    quincena_sel = st.selectbox("Filtrar por quincena", ["Todas las quincenas"] + quincenas)

    visibles = [q for q in lista_q if _coincide_filtro(q, actual)
                and (quincena_sel == "Todas las quincenas" or q.get("quincena_afectada") == quincena_sel)]
    visibles.sort(key=lambda q: (q.get("estatus") in ESTADOS_CERRADOS, -(_dias_abierto(q) or 0)))   # lo más viejo abierto, primero
    st.caption(f"Mostrando {len(visibles)} de {len(lista_q)} tickets · los abiertos más antiguos aparecen primero.")

    if visibles:
        filas = []
        for q in visibles:
            fila = {
                "Folio": q.get("folio", ""), "Nombre": q.get("nombre", ""), "Tarjeta": q.get("tarjeta_empleado", ""),
                "Tipo": q.get("tipo_nombre", ""), "Quincena": q.get("quincena_afectada", ""),
                "Estatus": f"{icono_estado(q.get('estatus'))} {q.get('estatus', '')}",
                "Días abierto": _dias_abierto(q), "Control de asistencia": q.get("solicitud_control_estado") or "",
            }
            if "monto_reclamado" in q:
                fila["Monto"] = q.get("monto_reclamado")
            fila["Registrada"] = fecha_local(q.get("fecha_creacion"))
            filas.append(fila)
        config = {"Monto": st.column_config.NumberColumn("Monto", format="$%.2f")} if any("Monto" in f for f in filas) else None
        st.dataframe(pd.DataFrame(filas), hide_index=True, column_config=config)
    return visibles


def _elegir_estatus(clave, estatus):
    st.session_state[clave] = estatus


def _insertar_plantilla(clave_txt, texto):
    """Pone el texto en el cuadro de respuesta (si ya había algo escrito, lo agrega después)."""
    actual = str(st.session_state.get(clave_txt, "")).strip()
    st.session_state[clave_txt] = ((actual + "\n\n" + texto) if actual else texto)[:2000]


def _botones_plantillas(t, elegido, clave_txt):
    def boton(i, p):
        st.button(p["etiqueta"], key=f"plantilla_{i}_{t['id']}", on_click=_insertar_plantilla,
                  args=(clave_txt, rellenar(p["texto"], t)))

    sugeridas = [(i, p) for i, p in enumerate(PLANTILLAS) if p["estatus"] == elegido]
    otras = [(i, p) for i, p in enumerate(PLANTILLAS) if p["estatus"] != elegido]
    if sugeridas:
        st.caption(f"Sugeridas para «{elegido}»:")
        for col, (i, p) in zip(st.columns(len(sugeridas)), sugeridas):
            with col:
                boton(i, p)
    if otras:
        with st.expander("Ver todas las respuestas rápidas"):
            for i, p in otras:
                boton(i, p)


def tab_resumen(t):
    c1, c2, c3 = st.columns(3)
    c1.write(f"**Tarjeta:** {md(t.get('tarjeta_empleado'))}")
    c2.write(f"**Nombre:** {md(t.get('nombre'))}")
    c3.write(f"**Turno:** {md(t.get('turno', 'N/A'))}")
    st.write(f"**Tipo:** {md(t.get('tipo_nombre', ''))} · **Quincena:** {md(t.get('quincena_afectada'))}")
    if t.get("dias_incidencia"):
        st.write(f"**Días de incidencia:** {md(t['dias_incidencia'])}")
    if t.get("monto_reclamado") is not None:
        st.write(f"**Monto reclamado:** \\${float(t['monto_reclamado']):,.2f}")
    st.info(f"**Motivo del empleado:** {md(t.get('motivo'))}")

    if permiso("whatsapp") and t.get("telefono"):
        texto = f"Hola, te contactamos de Recursos Humanos respecto a tu queja de nómina con folio {t['folio']}."
        enlace = link_whatsapp(t["telefono"], texto)
        if enlace:
            st.link_button(f"💬 Escribir por WhatsApp ({t['telefono']})", enlace)
        else:
            st.caption("El teléfono registrado no tiene un formato válido.")


def tab_atender(t, db):
    actual = t.get("estatus")
    clave_sel = f"est_sel_{t['id']}_{actual}"      # incluye el estatus actual: al cambiar, la selección se reinicia
    elegido = st.session_state.get(clave_sel, actual)

    st.markdown("**1. Elige el nuevo estatus**")
    for col, est in zip(st.columns(len(ESTADOS_QUEJA)), ESTADOS_QUEJA):
        with col:
            st.button(f"{icono_estado(est)} {est}", key=f"est_{CLAVE_CSS_ESTADO[est]}_{t['id']}",
                      type="primary" if est == elegido else "secondary",
                      on_click=_elegir_estatus, args=(clave_sel, est))
    st.caption(f"Estatus actual: **{actual}** → nuevo estatus elegido: **{elegido}**")

    n_resp = st.session_state.get(f"resp_n_{t['id']}", 0)      # sube al guardar: así el cuadro queda vacío
    clave_txt = f"resp_txt_{t['id']}_{n_resp}"
    st.markdown("**2. Respuestas rápidas** (opcional: insertan un texto que puedes editar)")
    _botones_plantillas(t, elegido, clave_txt)

    with st.form(f"form_atencion_{t['id']}"):
        st.markdown("**3. Escribe la respuesta** (obligatoria si rechazas la queja)")
        comentario = st.text_area("Respuesta o nota de seguimiento", max_chars=2000, key=clave_txt,
                                  placeholder="Escribe la respuesta para el empleado o el motivo del rechazo...")
        es_nota_interna = st.checkbox("Es una nota interna (el empleado no la verá)", key=f"resp_int_{t['id']}_{n_resp}")
        guardar = st.form_submit_button("💾 Guardar cambios", type="primary")

    if guardar:
        comentario = comentario.strip()
        guardado = False
        if elegido not in ESTADOS_QUEJA:
            st.error("Estatus no válido.")
        elif elegido == "Rechazada" and not comentario:
            st.error("⚠️ Para rechazar una queja debes escribir el motivo en la respuesta.")
        elif MARCA_COMPLETAR in comentario:
            st.error(f"⚠️ Completa el texto marcado como {MARCA_COMPLETAR} antes de guardar.")
        else:
            try:
                q_ref = db.collection("quejas").document(t["id"])
                anterior = (q_ref.get().to_dict() or {}).get("estatus")        # estatus real en este momento
                ahora_utc = datetime.datetime.now(datetime.timezone.utc)
                lote = db.batch()
                lote.update(q_ref, {"estatus": elegido})
                lote.set(q_ref.collection("historial_estatus").document(), {
                    "estatus_anterior": anterior, "estatus_nuevo": elegido,
                    "usuario_cambio": st.session_state.rh_usuario, "comentario": comentario, "fecha": ahora_utc,
                })
                if comentario:
                    lote.set(q_ref.collection("comentarios").document(), {
                        "usuario": f"RH ({st.session_state.rh_usuario})", "comentario": comentario,
                        "es_interno": bool(es_nota_interna), "fecha": ahora_utc,
                    })
                lote.commit()
                cargar_quejas.clear()
                st.session_state[f"resp_n_{t['id']}"] = n_resp + 1
                st.session_state["ultimo_wa_envio"] = {
                    "telefono": t.get("telefono"), "folio": t["folio"], "estatus": elegido,
                    "comentario": "" if es_nota_interna else comentario,
                }
                guardado = True
            except Exception:
                logger.exception("Error al actualizar el ticket")
                st.error("No se pudo actualizar el ticket. Intenta de nuevo.")
        if guardado:
            st.rerun()

    wa = st.session_state.get("ultimo_wa_envio")
    if wa and wa["folio"] == t["folio"] and wa["telefono"] and permiso("whatsapp"):
        st.success("📲 **Aviso listo para enviar al empleado**")
        mensaje = f"Hola, te informamos que el estatus de tu queja con folio *{wa['folio']}* cambió a: *{wa['estatus']}*."
        if wa["comentario"]:
            mensaje += "\n\n*Respuesta de Recursos Humanos:* " + wa["comentario"]
        enlace = link_whatsapp(wa["telefono"], mensaje)
        if enlace:
            st.link_button(f"👉 Enviar por WhatsApp ({wa['telefono']})", enlace)


def tab_archivos(t, db):
    adjuntos = [a.to_dict() for a in db.collection("quejas").document(t["id"]).collection("adjuntos").stream()]
    if not permiso("ver_talon"):
        adjuntos = [a for a in adjuntos if a.get("tipo_archivo") != "Talon_Pago"]
    if not adjuntos:
        st.caption("No hay archivos adjuntos en este ticket.")
        return
    st.caption("Los archivos son privados: se descargan desde aquí, no tienen enlace público.")
    for adj in adjuntos:
        file_id = adj.get("drive_file_id") or adj.get("ruta_dropbox") or ""
        nombre = adj.get("nombre_archivo", "Archivo")
        tipo = adj.get("tipo_archivo", "Adjunto")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"📄 **{md(tipo)}:** `{sanear_nombre(nombre)}`")
        with col2:
            if permiso("descargar_adjuntos") and RE_ID_DRIVE.fullmatch(str(file_id)):
                if st.button("📥 Preparar descarga", key=f"prep_{file_id}"):
                    try:
                        contenido, mime = descargar_evidencia(file_id)
                        st.session_state["descarga_lista"] = {"id": file_id, "data": contenido, "mime": mime, "nombre": sanear_nombre(nombre)}
                        registrar_auditoria(db, st.session_state.rh_usuario, "descarga_adjunto", f"{t['folio']} / {sanear_nombre(nombre)}")
                    except Exception:
                        logger.exception("Error al descargar adjunto")
                        st.error("No se pudo descargar el archivo.")
                lista = st.session_state.get("descarga_lista")
                if lista and lista["id"] == file_id:
                    st.download_button("⬇️ Guardar archivo", data=lista["data"], file_name=lista["nombre"],
                                       mime=lista["mime"], key=f"dl_{file_id}", type="primary")
            else:
                st.caption("Archivo no disponible")


def tab_conversacion(t, db):
    ref = db.collection("quejas").document(t["id"])
    minimo = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    eventos = []
    for c in (d.to_dict() for d in ref.collection("comentarios").stream()):
        autor = ("🔒 Nota interna · " if c.get("es_interno") else "") + str(c.get("usuario", ""))
        eventos.append((c.get("fecha") or minimo, "💬", autor, c.get("comentario", "")))
    for h in (d.to_dict() for d in ref.collection("historial_estatus").stream()):
        cambio = f"{h.get('estatus_anterior') or '—'} → {h.get('estatus_nuevo', '')}"
        eventos.append((h.get("fecha") or minimo, "🔁", str(h.get("usuario_cambio", "")), cambio))
    if not eventos:
        st.caption("Todavía no hay movimientos en este ticket.")
        return
    eventos.sort(key=lambda e: e[0])
    with st.container(height=420):
        for fecha, icono, autor, texto in eventos:
            st.markdown(f"{icono} **{fecha_local(fecha)}** · {md(autor)}")
            st.write(md(texto))


def tab_control(t, db, rol_actual):
    try:
        solicitudes = obtener_solicitudes_control(t["id"])
    except Exception:
        logger.exception("No se pudieron cargar las solicitudes")
        solicitudes = []
        st.error("No se pudieron cargar las solicitudes.")
    pendiente = next((s for s in solicitudes if s.get("estado") == "Pendiente"), None)

    if not solicitudes:
        st.caption("Aún no hay solicitudes en este ticket.")
    for s in solicitudes:
        icono = {"Pendiente": "🟡", "Respondida": "🟢", "Cancelada": "⚪"}.get(s.get("estado"), "⚪")
        with st.expander(f"{icono} {s.get('estado', '')} — {fecha_local(s.get('solicitada_en'))}", expanded=(s is pendiente)):
            st.write(f"**Solicitó:** {md(s.get('solicitada_por'))}")
            st.write(f"**Solicitud:** {md(s.get('texto'))}")
            if s.get("estado") == "Respondida":
                st.write(f"**Respondió:** {md(s.get('respondida_por'))} ({fecha_local(s.get('respondida_en'))})")
                st.write(f"**Respuesta:** {md(s.get('respuesta'))}")
                if s.get("n_archivos"):
                    st.caption(f"📎 {s['n_archivos']} archivo(s): están en la pestaña Archivos como «Respuesta_Control_Asistencia».")

    def _terminar(mensaje, ok, exito):
        if ok:
            cargar_quejas.clear()
            st.session_state["aviso_panel"] = exito
            st.rerun()

    if permiso("solicitar_info_control"):
        if pendiente:
            st.info("Hay una solicitud pendiente de respuesta de Control de asistencia.")
            if st.button("✖️ Cancelar la solicitud pendiente", key=f"cancel_sol_{pendiente['id']}"):
                hecho = False
                try:
                    cancelar_solicitud_control(t["id"], pendiente["id"], st.session_state.rh_usuario, rol_actual)
                    registrar_auditoria(db, st.session_state.rh_usuario, "solicitud_control_cancelar", t["folio"])
                    hecho = True
                except (ErrorValidacion, LimiteExcedido) as e:
                    st.error(f"⚠️ {md(str(e))}")
                except Exception:
                    logger.exception("Error al cancelar la solicitud")
                    st.error("No se pudo cancelar la solicitud.")
                _terminar("", hecho, "Solicitud cancelada.")
        else:
            with st.form(f"form_solicitud_control_{t['id']}"):
                texto_sol = st.text_area("¿Qué información necesitas de Control de asistencia?", max_chars=2000,
                                         placeholder="Ej. Confirmar la asistencia del 3 y 4 de octubre...")
                enviar_sol = st.form_submit_button("📨 Enviar solicitud", type="primary")
            if enviar_sol:
                hecho = False
                try:
                    crear_solicitud_control(t["id"], st.session_state.rh_usuario, rol_actual, texto_sol)
                    registrar_auditoria(db, st.session_state.rh_usuario, "solicitud_control_crear", t["folio"])
                    hecho = True
                except (ErrorValidacion, LimiteExcedido) as e:
                    st.error(f"⚠️ {md(str(e))}")
                except Exception:
                    logger.exception("Error al crear la solicitud")
                    st.error("No se pudo enviar la solicitud. Intenta de nuevo.")
                _terminar("", hecho, "✅ Solicitud enviada a Control de asistencia.")

    if permiso("responder_solicitud_control"):
        if pendiente:
            with st.form(f"form_respuesta_control_{pendiente['id']}"):
                st.markdown("**Responder a la solicitud** (texto obligatorio; hasta 5 documentos opcionales)")
                texto_resp = st.text_area("Respuesta *", max_chars=2000)
                archivos_resp = st.file_uploader("Documentos (PDF, PNG o JPG; máx. 5 archivos)", type=FORMATOS_ARCHIVO,
                                                 accept_multiple_files=True, key=f"resp_files_{pendiente['id']}")
                enviar_resp = st.form_submit_button("📤 Enviar respuesta", type="primary")
            if enviar_resp:
                hecho = False
                try:
                    with st.spinner("Enviando respuesta..."):
                        responder_solicitud_control(t["id"], pendiente["id"], st.session_state.rh_usuario,
                                                    rol_actual, texto_resp, archivos_resp or [])
                    registrar_auditoria(db, st.session_state.rh_usuario, "solicitud_control_responder", t["folio"])
                    hecho = True
                except (ErrorValidacion, LimiteExcedido) as e:
                    st.error(f"⚠️ {md(str(e))}")
                except Exception:
                    logger.exception("Error al responder la solicitud")
                    st.error("No se pudo enviar la respuesta. Intenta de nuevo.")
                _terminar("", hecho, "✅ Respuesta enviada. El analista fue notificado.")
        else:
            st.caption("No hay solicitudes pendientes para ti en este ticket. Solo puedes responder cuando el analista lo solicite.")


def detalle_ticket(t, db, rol_actual):
    st.markdown(
        f'<div class="card"><div class="big">Folio <b>{html.escape(str(t.get("folio", "")))}</b> &nbsp; {badge(t.get("estatus"))}</div>'
        f'<div class="muted">{html.escape(str(t.get("tipo_nombre", "")))} · Quincena {html.escape(str(t.get("quincena_afectada", "")))}</div></div>',
        unsafe_allow_html=True)
    if not permiso("gestionar_ticket"):
        st.caption("🔒 Tu rol es de solo lectura: no puedes modificar este ticket.")

    nombres = ["📋 Resumen"]
    if permiso("gestionar_ticket"):
        nombres.append("✍️ Atender")
    nombres.append("📂 Archivos")
    if permiso("gestionar_ticket"):
        nombres.append("💬 Conversación")
    if permiso("ver_solicitudes_control"):
        nombres.append("🕒 Control de asistencia")
    # st.tabs vuelve a la primera pestaña cuando se hace rerun al presionar un botón.
    # Con st.radio + key la sección elegida se queda guardada en session_state.
    clave_vista = f"rh_vista_{t['id']}"
    if st.session_state.get(clave_vista) not in nombres:
        st.session_state[clave_vista] = "✍️ Atender" if "✍️ Atender" in nombres else nombres[0]
    vista = st.radio("Sección del ticket", nombres, key=clave_vista, horizontal=True, label_visibility="collapsed")
    st.write("")

    if vista == "📋 Resumen":
        tab_resumen(t)
    elif vista == "✍️ Atender":
        tab_atender(t, db)
    elif vista == "📂 Archivos":
        tab_archivos(t, db)
    elif vista == "💬 Conversación":
        tab_conversacion(t, db)
    elif vista == "🕒 Control de asistencia":
        tab_control(t, db, rol_actual)


def _valor_exportacion(valor):
    """Convierte valores Firestore a contenido seguro para CSV."""
    if isinstance(valor, (datetime.datetime, datetime.date)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return json.dumps({str(k): _valor_exportacion(v) for k, v in valor.items()}, ensure_ascii=False)
    if isinstance(valor, (list, tuple)):
        return json.dumps([_valor_exportacion(v) for v in valor], ensure_ascii=False)
    if valor is None:
        return ""
    return valor


def _csv_en_zip(archivo_zip, nombre, registros):
    registros = list(registros)
    if not registros:
        return
    columnas = sorted({str(k) for r in registros for k in r.keys()})
    salida = io.StringIO(newline="")
    escritor = csv.DictWriter(salida, fieldnames=columnas, extrasaction="ignore")
    escritor.writeheader()
    for registro in registros:
        escritor.writerow({k: _valor_exportacion(v) for k, v in registro.items()})
    archivo_zip.writestr(nombre, salida.getvalue().encode("utf-8-sig"))


def _generar_exportacion(db, quincena=None):
    """Exporta quejas y sus subcolecciones; el alcance global incluye catálogos y auditoría."""
    memoria = io.BytesIO()
    quejas = []
    relacionados = {"adjuntos": [], "historial_estatus": [], "comentarios": [], "solicitudes_control": []}
    for doc in db.collection("quejas").stream():
        datos = doc.to_dict() or {}
        datos["documento_id"] = doc.id
        if quincena and datos.get("quincena_afectada") != quincena:
            continue
        quejas.append(datos)
        ref = db.collection("quejas").document(doc.id)
        for subcoleccion in relacionados:
            for subdoc in ref.collection(subcoleccion).stream():
                fila = subdoc.to_dict() or {}
                fila["documento_id"] = subdoc.id
                fila["queja_id"] = doc.id
                fila["folio"] = datos.get("folio", "")
                relacionados[subcoleccion].append(fila)

    with zipfile.ZipFile(memoria, "w", compression=zipfile.ZIP_DEFLATED) as z:
        _csv_en_zip(z, "quejas.csv", quejas)
        for nombre, filas in relacionados.items():
            _csv_en_zip(z, f"{nombre}.csv", filas)
        if not quincena:
            for coleccion in ("tipos_queja", "auditoria", "notificaciones", "estado_usuarios", "contadores"):
                filas = []
                for doc in db.collection(coleccion).stream():
                    fila = doc.to_dict() or {}
                    fila["documento_id"] = doc.id
                    filas.append(fila)
                _csv_en_zip(z, f"{coleccion}.csv", filas)
    return memoria.getvalue(), len(quejas)


def zona_exportacion_admin(db):
    """Herramienta exclusiva del rol Administrador, validada por permiso."""
    if not permiso("exportar_datos"):
        return
    with st.expander("📦 Exportar información de la base de datos", expanded=False):
        st.caption("Descarga los registros en archivos CSV UTF-8 dentro de un ZIP. La exportación completa incluye las quejas, sus documentos e historial, además de catálogos, notificaciones y auditoría.")
        alcance = st.radio(
            "¿Qué información deseas exportar?",
            ["Toda la base de datos", "Una quincena específica"],
            horizontal=True, key="adm_export_alcance",
        )
        quincena = None
        if alcance == "Una quincena específica":
            disponibles = sorted({
                str((d.to_dict() or {}).get("quincena_afectada", ""))
                for d in db.collection("quejas").stream()
                if (d.to_dict() or {}).get("quincena_afectada")
            }, reverse=True)
            if not disponibles:
                st.info("Todavía no hay quincenas con quejas registradas para exportar.")
                return
            quincena = st.selectbox("Selecciona la quincena", disponibles, key="adm_export_quincena")
        if st.button("⬇️ Preparar exportación", type="primary", key="adm_generar_exportacion"):
            try:
                with st.spinner("Preparando los archivos de exportación..."):
                    contenido, total = _generar_exportacion(db, quincena)
                if total == 0:
                    st.warning("No se encontraron quejas para el criterio seleccionado.")
                else:
                    sufijo = quincena if quincena else "completa"
                    st.download_button(
                        f"📥 Descargar exportación ({total} quejas)", data=contenido,
                        file_name=f"exportacion_quejas_{sufijo}.zip", mime="application/zip",
                        key=f"adm_descargar_exportacion_{sufijo}",
                    )
            except Exception:
                logger.exception("Error al generar la exportación administrativa")
                st.error("No fue posible preparar la exportación. Revisa los registros de la aplicación.")


def zona_admin(lista_q, db):
    st.write("---")
    st.subheader("⚙️ Administración: depurar folios")
    st.caption("Los folios se marcan como eliminados (borrado lógico): salen de la bandeja pero quedan en la base para auditoría.")
    with st.expander("🔴 Abrir el panel de eliminación múltiple", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            busqueda = st.text_input("🔍 Buscar por folio o tarjeta", placeholder="Ej. Q-2026-0001", key="busqueda_del_input").strip().lower()
        with c2:
            quincenas = sorted({str(q.get("quincena_afectada", "")) for q in lista_q if q.get("quincena_afectada")}, reverse=True)
            periodo = st.selectbox("Filtrar por quincena", ["Todas las quincenas"] + quincenas, key="filtro_periodo_del_select")

        candidatos = {}
        for q in lista_q:
            ok_texto = (not busqueda) or busqueda in str(q.get("folio", "")).lower() or busqueda in str(q.get("tarjeta_empleado", "")).lower()
            ok_periodo = periodo == "Todas las quincenas" or periodo == q.get("quincena_afectada", "")
            if ok_texto and ok_periodo:
                etiqueta = f"{q.get('folio', 'S/F')} — {q.get('tarjeta_empleado', '')} — {q.get('quincena_afectada', '')} ({q.get('estatus', '')}) [{q['id'][:4]}]"
                candidatos[etiqueta] = q["id"]

        st.markdown(f"**Folios que coinciden:** {len(candidatos)}")
        if not candidatos:
            st.info("No hay folios que coincidan con la búsqueda.")
            return

        def _todos(etiquetas):
            st.session_state["adm_del_sel"] = list(etiquetas)

        st.session_state["adm_del_sel"] = [s for s in st.session_state.get("adm_del_sel", []) if s in candidatos]
        st.button("☑️ Seleccionar todos los visibles", on_click=_todos, args=(list(candidatos.keys()),))
        seleccion = st.multiselect("Folios a eliminar", options=list(candidatos.keys()), key="adm_del_sel")
        n_del = st.session_state.get("adm_del_n", 0)
        confirmacion = st.text_input("Para confirmar escribe ELIMINAR", key=f"adm_del_confirm_{n_del}")

        if st.button("🔥 Eliminar folios seleccionados", type="primary", key="btn_eliminar_folios"):
            eliminado = 0
            if not permiso("eliminar_folios"):
                st.error("No tienes permiso para esta acción.")
            elif not seleccion:
                st.warning("⚠️ No has seleccionado ningún folio.")
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
                                "eliminada": True, "eliminada_por": st.session_state.rh_usuario, "eliminada_en": ahora_utc})
                        lote.commit()
                    registrar_auditoria(db, st.session_state.rh_usuario, "eliminar_folios", ", ".join(s.split(" — ")[0] for s in seleccion))
                    cargar_quejas.clear()
                    st.session_state["adm_del_n"] = n_del + 1
                    st.session_state["aviso_panel"] = f"Se marcaron como eliminados {len(ids)} folio(s)."
                    eliminado = len(ids)
                except Exception:
                    logger.exception("Error al eliminar folios")
                    st.error("No se pudieron eliminar los folios.")
            if eliminado:
                st.rerun()


def panel_rh():
    db = obtener_conexion()
    rol_actual = st.session_state.rh_rol
    usuario = st.session_state.rh_usuario

    col_info, col_salir = st.columns([4, 1])
    with col_info:
        st.success(f"Conectado como: **{md(usuario)}** ({md(rol_actual)})")
    with col_salir:
        if st.button("Cerrar sesión", key="btn_logout"):
            registrar_auditoria(db, usuario, "logout", "")
            cerrar_sesion_rh()
            st.rerun()

    aviso = st.session_state.pop("aviso_panel", None)
    if aviso:
        st.success(aviso)

    bloque_notificaciones(usuario, rol_actual)

    if st.button("🔄 Actualizar bandeja", key="btn_actualizar"):
        cargar_quejas.clear()
        obtener_notificaciones.clear()
        st.rerun()

    # Cada rol recibe solo los tipos y campos que le corresponden
    lista_q = quejas_visibles_para_rol(cargar_quejas(), rol_actual)
    lista_q = [limpiar_queja_para_rol(q, rol_actual) for q in lista_q]
    if permiso("exportar_datos"):
        zona_exportacion_admin(db)
    if not lista_q:
        st.info("No hay quejas registradas en el sistema.")
        return

    visibles = bandeja(lista_q)

    st.write("---")
    st.subheader("🎫 Ticket seleccionado")
    if not visibles:
        st.warning("No hay tickets con el filtro elegido.")
    else:
        por_etiqueta = {}
        for t in visibles:
            etiqueta = f"{t.get('folio', 'S/F')} — {t.get('tarjeta_empleado', '')}"
            if etiqueta in por_etiqueta:
                etiqueta += f" [{t['id'][:4]}]"
            por_etiqueta[etiqueta] = t
        # Si el ticket que estabas atendiendo ya no cumple el filtro (p. ej. pasó de Pendiente a
        # En proceso), se conserva en la lista para que no salte a otro folio.
        id_actual = st.session_state.get("rh_ticket_id")
        if id_actual and all(t["id"] != id_actual for t in por_etiqueta.values()):
            previo = next((q for q in lista_q if q["id"] == id_actual), None)
            if previo:
                por_etiqueta = {f"{previo.get('folio', 'S/F')} — {previo.get('tarjeta_empleado', '')}": previo, **por_etiqueta}

        etiquetas = list(por_etiqueta.keys())
        indice = next((n for n, e in enumerate(etiquetas) if por_etiqueta[e]["id"] == id_actual), 0)
        elegido = st.selectbox("Elige un folio", etiquetas, index=indice)
        ticket = por_etiqueta.get(elegido) or next(iter(por_etiqueta.values()))   # por si el filtro cambió y ya no existe
        st.session_state["rh_ticket_id"] = ticket["id"]
        detalle_ticket(ticket, db, rol_actual)

    if permiso("eliminar_folios"):
        zona_admin(lista_q, db)


def pagina_rh():
    st.markdown(css_ancho(1500), unsafe_allow_html=True)
    boton_inicio()
    st.header("🗂️ Panel interno")

    for k, v in (("rh_logueado", False), ("rh_usuario", ""), ("rh_rol", ""), ("rh_inicio", 0.0), ("rh_ultimo", 0.0)):
        st.session_state.setdefault(k, v)

    ahora = time.time()
    if st.session_state.rh_logueado:
        if (ahora - st.session_state.rh_ultimo > INACTIVIDAD_SEG) or (ahora - st.session_state.rh_inicio > SESION_MAX_SEG):
            cerrar_sesion_rh()
            st.warning("Tu sesión expiró por seguridad. Vuelve a iniciar sesión.")
        else:
            st.session_state.rh_ultimo = ahora

    if not st.session_state.get("rh_logueado"):
        login_rh()
    else:
        panel_rh()


# ===========================================================================
# ENRUTADOR + PIE
# ===========================================================================
_pagina = st.session_state.get("pagina", "Inicio")
if _pagina == "Registrar una queja":
    pagina_registrar()
elif _pagina == "Consultar mi queja":
    pagina_consultar()
elif _pagina == "Acceso RH":
    pagina_rh()
else:
    pagina_inicio()

st.markdown(pie_legal(URL_PRIVACIDAD, URL_TERMINOS), unsafe_allow_html=True)

# Firma flotante
# Firma flotante
url_imagen_drive = "https://i.redd.it/snoovatar/avatars/98e5bfa6-95f3-46d8-8754-7a64c0099533.png"
enlace_perfil = "https://github.com/DanyFlow"

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
        <img src="{url_imagen_drive}" alt="Dany FloVel">
        <div class="firma-texto">
            <span class="firma-titulo">By Dany FloVel</span>
            <span class="firma-sub">⚡ Ver perfil ⚡</span>
        </div>
    </div>
</a>
"""
st.markdown(firma_html, unsafe_allow_html=True)

