"""Estilos y piezas de HTML de la interfaz.

Todo lo que se arma aquí es texto FIJO de la app o texto escapado con html.escape:
nunca se inserta contenido escrito por empleados sin escapar.

Compatibilidad con modo claro/oscuro: el CSS NO fija el color de fondo ni de texto
de la página. Deja que Streamlit use el de su tema y solo añade acentos con colores
translúcidos (rgba(128,128,128,x)) o pares fondo/texto completos (insignias, botones).
"""
import html

# estatus -> (ícono, fondo, texto)  [pares con buen contraste en cualquier tema]
ESTADOS = {
    "Pendiente": ("🟡", "#fef3c7", "#78350f"),
    "En proceso": ("🔵", "#dbeafe", "#1e3a8a"),
    "Requiere información": ("🟠", "#ffedd5", "#7c2d12"),
    "Resuelto": ("🟢", "#dcfce7", "#14532d"),
    "Rechazada": ("🔴", "#fee2e2", "#7f1d1d"),
}
ESTADOS_ORDEN = list(ESTADOS)
CLAVE_CSS_ESTADO = {"Pendiente": "pend", "En proceso": "proc", "Requiere información": "info",
                    "Resuelto": "res", "Rechazada": "rech"}


def icono_estado(estatus):
    return ESTADOS.get(estatus, ("⚪",))[0]


CSS = """
<style>
html { font-size: 112.5%; }
[data-testid="stMainBlockContainer"] { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
h1, h2, h3 { letter-spacing: -.02em; }
h1 { font-weight: 800; }
p, label, .stMarkdown { line-height: 1.55; }

/* ---- barra lateral (colores propios, se ve igual en claro y oscuro) ---- */
[data-testid="stSidebar"] { background: linear-gradient(180deg,#12233f 0%,#172f50 100%); border-right: 1px solid #203c60; }
[data-testid="stSidebar"] * { color: #edf5ff; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12); border-radius: 12px; padding: .6rem .8rem; margin: .3rem 0; font-size: 1.02rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: rgba(255,255,255,.15); }
[data-testid="stSidebar"] .side-legal a { color: #bcd8ff !important; text-decoration: underline; }
[data-testid="stSidebar"] .side-legal { font-size: .88rem; line-height: 1.9; }

/* ---- tarjetas: translúcidas, funcionan con fondo claro u oscuro ---- */
[data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] { border: 1px solid rgba(128,128,128,.30); border-radius: 18px; background: rgba(128,128,128,.07); box-shadow: 0 6px 22px rgba(0,0,0,.06); padding: 1.1rem; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stSelectbox"] div[data-baseweb="select"] { border-radius: 10px; }
[data-testid="stAlert"] { border-radius: 12px; }
[data-testid="stDataFrame"] { border: 1px solid rgba(128,128,128,.30); border-radius: 14px; overflow: hidden; }
[data-testid="stFileUploader"] section { border: 1px dashed rgba(128,128,128,.55); border-radius: 12px; background: rgba(128,128,128,.07); }
hr { border-color: rgba(128,128,128,.30); margin: 1.4rem 0; }

.card { border: 1px solid rgba(128,128,128,.30); border-radius: 16px; padding: 1rem 1.25rem; background: rgba(128,128,128,.07); margin: .4rem 0 .8rem; }
.card .muted { opacity: .75; }
.card .big { font-size: 1.3rem; margin: .15rem 0; }
.card .icon { font-size: 2.2rem; line-height: 1; }
.card h3 { margin: .35rem 0 .25rem; }
.card p { margin: 0; opacity: .85; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: .12em; font-weight: 800; }
.section-intro { opacity: .8; margin-top: -.45rem; margin-bottom: 1.1rem; }

/* ---- portada ---- */
.hero-app { padding: 1.6rem 1.8rem; border-radius: 20px; margin: 0 0 1.4rem; background: linear-gradient(115deg,#12233f 0%,#1f528f 65%,#3279c8 100%); box-shadow: 0 12px 30px rgba(26,65,120,.25); }
.hero-app, .hero-app * { color: #ffffff; }
.hero-app .eyebrow { color: #bcd8ff; text-transform: uppercase; letter-spacing: .13em; font-size: .78rem; font-weight: 750; margin-bottom: .45rem; }
.hero-app h1 { font-size: clamp(1.8rem,3.2vw,2.6rem); line-height: 1.12; margin: 0 0 .6rem; padding: 0; }
.hero-app p { color: #e0edff; margin: 0; font-size: 1.08rem; }

/* ---- botones ---- */
[data-testid="stButton"] button, .stButton > button, [data-testid="stFormSubmitButton"] button, [data-testid="stDownloadButton"] button, [data-testid="stLinkButton"] a { width: 100%; min-height: 3rem; border-radius: 12px; font-weight: 650; transition: box-shadow .15s ease, transform .15s ease; }
button[kind="primary"], [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] { background: linear-gradient(135deg,#2868c7,#1d4f9e) !important; color: #ffffff !important; border: 1px solid #1d4f9e !important; }
button[kind="secondary"], [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] { border: 1px solid rgba(128,128,128,.55) !important; }
[data-testid="stButton"] button:hover, [data-testid="stFormSubmitButton"] button:hover { box-shadow: 0 6px 16px rgba(36,95,186,.25); }
button:focus-visible, a:focus-visible, input:focus-visible, textarea:focus-visible { outline: 3px solid #f59e0b !important; outline-offset: 2px; }

/* botones grandes de la portada */
.st-key-home_registrar button, .st-key-home_consultar button { min-height: 4.6rem; font-size: 1.3rem; border-radius: 18px; }
.st-key-home_consultar button { background: linear-gradient(135deg,#0e7490,#0b5d75) !important; border-color: #0b5d75 !important; color: #fff !important; }
.st-key-btn_inicio button { min-height: 2.5rem; width: auto; font-size: .95rem; }

/* botones de estatus (panel RH): un color por estatus; el elegido lleva aro azul */
[class*="st-key-est_"] button { height: 4.4rem; min-height: 4.4rem; width: 100%; padding: .4rem .6rem; font-weight: 750; border-width: 2px !important; opacity: .78; display: flex; align-items: center; justify-content: center; text-align: center; }
[data-testid="stColumn"]:has([class*="st-key-est_"]) { flex: 1 1 0 !important; min-width: 0 !important; }
[class*="st-key-est_"] { width: 100% !important; min-width: 0; }
[class*="st-key-est_"] button { box-sizing: border-box; }
[class*="st-key-est_"] button > div, [class*="st-key-est_"] button p { width: 100%; margin: 0; text-align: center; line-height: 1.2; white-space: normal; }
[class*="st-key-est_"] button[kind="primary"], [class*="st-key-est_"] [data-testid="stBaseButton-primary"] { opacity: 1; box-shadow: 0 0 0 4px rgba(37,99,235,.55); }
[class*="st-key-est_pend_"] button { background: #fef3c7 !important; color: #78350f !important; border-color: #f59e0b !important; }
[class*="st-key-est_proc_"] button { background: #dbeafe !important; color: #1e3a8a !important; border-color: #3b82f6 !important; }
[class*="st-key-est_info_"] button { background: #ffedd5 !important; color: #7c2d12 !important; border-color: #f97316 !important; }
[class*="st-key-est_res_"] button { background: #dcfce7 !important; color: #14532d !important; border-color: #22c55e !important; }
[class*="st-key-est_rech_"] button { background: #fee2e2 !important; color: #7f1d1d !important; border-color: #ef4444 !important; }

/* ---- secciones del ticket (Resumen / Atender / Archivos...): se ven como botones grandes ---- */
[class*="st-key-rh_vista_"] [role="radiogroup"] { gap: .6rem; flex-wrap: wrap; }
[class*="st-key-rh_vista_"] label { cursor: pointer; margin: 0 !important; padding: .7rem 1.2rem; min-height: 3rem; border-radius: 12px; border: 2px solid rgba(128,128,128,.55); background: rgba(128,128,128,.12); transition: background .15s ease, box-shadow .15s ease; }
[class*="st-key-rh_vista_"] label > div:first-child { display: none; }  /* oculta el circulito del radio */
[class*="st-key-rh_vista_"] label p { font-size: 1.05rem; font-weight: 700; margin: 0; }
[class*="st-key-rh_vista_"] label:hover { background: rgba(128,128,128,.25); box-shadow: 0 4px 12px rgba(0,0,0,.12); }
[class*="st-key-rh_vista_"] label:has(input:checked) { background: linear-gradient(135deg,#2868c7,#1d4f9e); border-color: #1d4f9e; box-shadow: 0 0 0 3px rgba(37,99,235,.35); }
[class*="st-key-rh_vista_"] label:has(input:checked) p, [class*="st-key-rh_vista_"] label:has(input:checked) div { color: #ffffff !important; }
[class*="st-key-rh_vista_"] label:has(input:focus-visible) { outline: 3px solid #f59e0b; outline-offset: 2px; }

/* ---- bandeja de notificaciones ---- */
.notif-head { display: flex; align-items: center; gap: .6rem; margin: .2rem 0 .7rem; }
.notif-head .t { font-size: 1.15rem; font-weight: 800; }
.notif-count { background: #dc2626; color: #fff; border-radius: 999px; padding: .05rem .7rem; font-weight: 800; font-size: .95rem; }
.notif-list { max-height: 330px; overflow-y: auto; padding-right: .3rem; display: flex; flex-direction: column; gap: .5rem; }
.notif-item { display: flex; gap: .8rem; align-items: flex-start; padding: .65rem .85rem; border-radius: 12px; border: 1px solid rgba(128,128,128,.28); border-left: 5px solid var(--nc,#9ca3af); background: rgba(128,128,128,.08); }
.notif-ico { flex: 0 0 2.3rem; height: 2.3rem; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.15rem; background: rgba(128,128,128,.20); background: color-mix(in srgb, var(--nc,#9ca3af) 22%, transparent); }
.notif-body { flex: 1; min-width: 0; }
.notif-title { font-weight: 750; font-size: .8rem; text-transform: uppercase; letter-spacing: .07em; color: var(--nc,#6b7280); }
.notif-text { margin-top: .1rem; line-height: 1.4; word-break: break-word; }
.notif-when { flex: 0 0 auto; text-align: right; white-space: nowrap; line-height: 1.3; }
.notif-when .rel { font-weight: 700; font-size: .9rem; }
.notif-when .abs { font-size: .78rem; opacity: .65; }
.notif-empty { display: inline-block; padding: .35rem .9rem; border-radius: 999px; background: rgba(128,128,128,.12); border: 1px solid rgba(128,128,128,.28); font-size: .92rem; opacity: .85; margin: .2rem 0 .4rem; }
@media (max-width: 700px) { .notif-item { flex-wrap: wrap; } .notif-when { width: 100%; text-align: left; } }

/* ---- insignias de estatus ---- */
.badge { display: inline-block; padding: .25rem .85rem; border-radius: 999px; font-weight: 700; font-size: .95rem; }

/* ---- indicador de pasos / progreso ---- */
.stepper { display: flex; align-items: flex-start; justify-content: space-between; gap: .25rem; margin: .4rem 0 1.3rem; }
.stepper .step { flex: 1; text-align: center; position: relative; }
.stepper .step:not(:last-child)::after { content: ""; position: absolute; top: 1.15rem; left: calc(50% + 1.5rem); right: calc(-50% + 1.5rem); height: 3px; background: rgba(128,128,128,.35); }
.stepper .step.done:not(:last-child)::after { background: #0e7490; }
.stepper .dot { display: inline-flex; width: 2.3rem; height: 2.3rem; border-radius: 50%; align-items: center; justify-content: center; font-weight: 800; background: rgba(128,128,128,.30); }
.stepper .done .dot { background: #0e7490; color: #fff; }
.stepper .current .dot { background: #1d4ed8; color: #fff; box-shadow: 0 0 0 4px rgba(29,78,216,.25); }
.stepper .warn .dot { background: #ea580c; color: #fff; box-shadow: 0 0 0 4px rgba(234,88,12,.25); }
.stepper .error .dot { background: #dc2626; color: #fff; box-shadow: 0 0 0 4px rgba(220,38,38,.25); }
.stepper .lbl { display: block; margin-top: .4rem; font-size: .92rem; line-height: 1.25; }
.stepper .current .lbl, .stepper .warn .lbl, .stepper .error .lbl { font-weight: 800; }
.stepper .todo .lbl { opacity: .65; }

/* ---- pie legal ---- */
.legal-footer { text-align: center; margin: 2.2rem 0 1rem; padding-top: 1rem; border-top: 1px solid rgba(128,128,128,.30); font-size: .95rem; opacity: .9; }
.legal-footer a { margin: 0 .5rem; }

@media (max-width: 700px) {
  html { font-size: 106.25%; }
  [data-testid="stMainBlockContainer"] { padding: 1rem .8rem 2rem; }
  .hero-app { padding: 1.2rem; border-radius: 15px; }
  [data-testid="stForm"] { padding: .7rem; }
  .stepper .lbl { font-size: .8rem; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
"""


def css_ancho(max_px):
    """Limita el ancho del contenido (las pantallas del empleado se leen mejor angostas)."""
    return f"<style>[data-testid='stMainBlockContainer'] {{ max-width: {int(max_px)}px; }}</style>"


def hero(eyebrow, titulo, texto):
    e, t, p = html.escape(eyebrow), html.escape(titulo), html.escape(texto)
    return f'<div class="hero-app"><div class="eyebrow">{e}</div><h1>{t}</h1><p>{p}</p></div>'


def tarjeta(icono, titulo, texto):
    return (f'<div class="card"><div class="icon">{html.escape(icono)}</div>'
            f'<h3>{html.escape(titulo)}</h3><p>{html.escape(texto)}</p></div>')


def badge(estatus):
    texto = html.escape(str(estatus or "Sin estatus"))
    if estatus in ESTADOS:
        icono, fondo, color = ESTADOS[estatus]
        return f'<span class="badge" style="background:{fondo};color:{color}">{icono} {texto}</span>'
    return f'<span class="badge" style="background:#e5e7eb;color:#374151">{texto}</span>'


def _pasos_html(items):
    """items: lista de (clase, simbolo, etiqueta)."""
    partes = []
    for clase, simbolo, etiqueta in items:
        partes.append(f'<div class="step {clase}"><span class="dot">{html.escape(simbolo)}</span>'
                      f'<span class="lbl">{html.escape(etiqueta)}</span></div>')
    return '<div class="stepper">' + "".join(partes) + "</div>"


def stepper_pasos(paso_actual, etiquetas):
    """Indicador del formulario: paso_actual empieza en 1."""
    items = []
    for i, etiqueta in enumerate(etiquetas, start=1):
        if i < paso_actual:
            items.append(("done", "✓", etiqueta))
        elif i == paso_actual:
            items.append(("current", str(i), etiqueta))
        else:
            items.append(("todo", str(i), etiqueta))
    return _pasos_html(items)


def stepper_estatus(estatus):
    """Línea de progreso que ve el empleado: Recibida -> En revisión -> Resuelta."""
    if estatus == "Pendiente":
        items = [("current", "1", "Recibida"), ("todo", "2", "En revisión"), ("todo", "3", "Resuelta")]
    elif estatus == "En proceso":
        items = [("done", "✓", "Recibida"), ("current", "2", "En revisión"), ("todo", "3", "Resuelta")]
    elif estatus == "Requiere información":
        items = [("done", "✓", "Recibida"), ("warn", "!", "Necesitamos información tuya"), ("todo", "3", "Resuelta")]
    elif estatus == "Resuelto":
        items = [("done", "✓", "Recibida"), ("done", "✓", "En revisión"), ("done", "✓", "Resuelta")]
    elif estatus == "Rechazada":
        items = [("done", "✓", "Recibida"), ("done", "✓", "En revisión"), ("error", "✕", "Rechazada")]
    else:
        items = [("todo", "1", "Recibida"), ("todo", "2", "En revisión"), ("todo", "3", "Resuelta")]
    return _pasos_html(items)


def _url_segura(url):
    """Solo se aceptan enlaces https://; cualquier otra cosa (javascript:, data:, etc.) se vuelve '#'."""
    url = str(url or "")
    return html.escape(url, quote=True) if url.startswith("https://") else "#"


def pie_legal(url_privacidad, url_terminos):
    p, t = _url_segura(url_privacidad), _url_segura(url_terminos)
    return ('<div class="legal-footer">'
            f'<a href="{p}" target="_blank" rel="noopener noreferrer">🔒 Aviso de privacidad</a>·'
            f'<a href="{t}" target="_blank" rel="noopener noreferrer">📄 Condiciones de servicio</a>'
            '</div>')


def enlaces_legales_lateral(url_privacidad, url_terminos):
    p, t = _url_segura(url_privacidad), _url_segura(url_terminos)
    return ('<div class="side-legal">'
            f'<a href="{p}" target="_blank" rel="noopener noreferrer">🔒 Aviso de privacidad</a><br>'
            f'<a href="{t}" target="_blank" rel="noopener noreferrer">📄 Condiciones de servicio</a>'
            '</div>')


def tarjeta_codigos(tipo, folio, clave):
    """Tarjeta grande con el folio y la clave de una queja recién registrada."""
    return ('<div class="card">'
            f'<div class="muted">{html.escape(str(tipo))}</div>'
            f'<div class="big">Folio: <b>{html.escape(str(folio))}</b></div>'
            f'<div class="big">Tu clave: <span class="mono">{html.escape(str(clave))}</span></div>'
            '</div>')


# tipo de aviso -> (etiqueta, color de acento)
_NOTIF_TIPOS = {
    "nueva_queja": ("Nueva queja", "#3b82f6"),
    "aclaracion_empleado": ("Respuesta del empleado", "#f97316"),
    "solicitud_control": ("Solicitud a Control", "#0e7490"),
    "respuesta_control": ("Respuesta de Control", "#16a34a"),
}


def notificaciones_cabecera(n):
    texto = "novedad sin revisar" if n == 1 else "novedades sin revisar"
    return f'<div class="notif-head"><span class="notif-count">{int(n)}</span><span class="t">🔔 {texto}</span></div>'


def notificacion_item(tipo, icono, detalle, relativo="", absoluto=""):
    etiqueta, color = _NOTIF_TIPOS.get(tipo, (str(tipo or "Aviso").replace("_", " ").capitalize(), "#9ca3af"))
    return (f'<div class="notif-item" style="--nc:{color}">'
            f'<div class="notif-ico">{html.escape(str(icono))}</div>'
            f'<div class="notif-body"><div class="notif-title">{html.escape(etiqueta)}</div>'
            f'<div class="notif-text">{html.escape(str(detalle))}</div></div>'
            f'<div class="notif-when"><div class="rel">{html.escape(relativo)}</div>'
            f'<div class="abs">{html.escape(absoluto)}</div></div></div>')


def notificaciones_lista(items_html):
    return '<div class="notif-list">' + "".join(items_html) + "</div>"


def notificaciones_vacias():
    return '<span class="notif-empty">🔔 Sin novedades nuevas</span>'
