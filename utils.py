import datetime
import io
import logging
import os
import re
import secrets

import streamlit as st
from firebase_admin import firestore
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from database import obtener_conexion, obtener_catálogo_tipos, verificar_queja_duplicada
from limitador import consumir_cupo, esta_bloqueado, limpiar, registrar_fallo
from seguridad import (
    RE_FOLIO, RE_ID_DRIVE, RE_QUINCENA,
    ErrorValidacion, LimiteExcedido,
    comparar_texto, generar_codigo_seguimiento, hash_secreto, limpiar_texto,
    normalizar_codigo, normalizar_telefono, sanear_nombre, validar_archivo,
    validar_nombre, validar_tarjeta, validar_telefono, verificar_secreto,
)

logger = logging.getLogger("quejas")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TIPOS_CON_DIAS = ("Descuento por omisión", "Permiso no aplicado")

MAX_QUEJAS_POR_LOTE = 5
MAX_EVIDENCIAS = 5
MAX_QUEJAS_POR_TARJETA_DIA = 10
MAX_QUEJAS_GLOBAL_DIA = 500
LIMITE_MONTO = 1_000_000.0
_DUMMY_HASH = "pbkdf2_sha256$600000$AAAAAAAAAAAAAAAAAAAAAA==$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


# =============================================================================
# GOOGLE DRIVE (archivos PRIVADOS: nunca se comparten con "cualquiera con el enlace")
# =============================================================================
def _cargar_credenciales():
    cfg = st.secrets.get("google_oauth", {})
    creds = None

    if cfg and cfg.get("refresh_token"):
        # Streamlit Cloud (y también local si pones el refresh_token en secrets)
        creds = Credentials(
            token=None,
            refresh_token=cfg["refresh_token"],
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
            token_uri=cfg.get("token_uri", "https://oauth2.googleapis.com/token"),
            scopes=SCOPES,
        )
    elif os.path.exists("token.json"):
        # Solo desarrollo local (JSON en lugar de pickle: pickle puede ejecutar código)
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if creds is not None and not creds.valid and creds.refresh_token:
        creds.refresh(Request())

    if creds is None or not creds.valid:
        # Primera vez en tu PC: flujo OAuth local con navegador
        from google_auth_oauthlib.flow import InstalledAppFlow  # import perezoso: solo se usa en local
        client_config = {"installed": {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": cfg.get("token_uri", "https://oauth2.googleapis.com/token"),
            "redirect_uris": ["http://localhost"],
        }}
        creds = InstalledAppFlow.from_client_config(client_config, SCOPES).run_local_server(port=0)
        fd = os.open("token.json", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(creds.to_json())
    return creds


@st.cache_resource
def _credenciales_drive():
    return _cargar_credenciales()


def servicio_drive():
    """Cliente de Drive nuevo por uso (los clientes httplib2 no son thread-safe;
    las credenciales sí se comparten y se refrescan solas)."""
    return build("drive", "v3", credentials=_credenciales_drive(), cache_discovery=False)


def _carpeta_raiz():
    cid = st.secrets.get("drive", {}).get("carpeta_raiz_id", "")
    if not RE_ID_DRIVE.fullmatch(str(cid)):
        raise RuntimeError("Falta [drive] carpeta_raiz_id en los secretos de la app.")
    return cid


def _q(valor):
    """Escapa un valor para usarlo dentro de comillas simples en una consulta de Drive."""
    return str(valor).replace("\\", "\\\\").replace("'", "\\'")


def obtener_o_crear_carpeta(service, nombre_carpeta, parent_id=None):
    query = f"name='{_q(nombre_carpeta)}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{_q(parent_id)}' in parents"
    files = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute().get("files", [])
    if files:
        return files[0]["id"]
    metadata = {"name": nombre_carpeta, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        metadata["parents"] = [parent_id]
    return service.files().create(body=metadata, fields="id").execute()["id"]


def guardar_evidencia(tarjeta_empleado, archivo_subido, tipo_archivo="Evidencia"):
    """Valida y sube el archivo a Drive de forma PRIVADA.

    Devuelve (file_id, nombre_guardado, "") — el tercer valor se conserva solo por
    compatibilidad: ya no existe URL pública. Lanza excepción si algo falla
    (antes se devolvía vacío y la queja se guardaba sin evidencia).
    """
    if not validar_tarjeta(tarjeta_empleado):
        raise ErrorValidacion("Número de tarjeta inválido.")
    datos, mime, ext = validar_archivo(archivo_subido)

    ahora = datetime.datetime.now()
    nombre = (f"{ahora:%H%M%S}_{sanear_nombre(tipo_archivo, 'x', 30).rsplit('.', 1)[0]}_"
              f"{sanear_nombre(archivo_subido.name, ext)[:-len(ext) - 1]}_{secrets.token_hex(3)}.{ext}")

    service = servicio_drive()
    tarjeta_id = obtener_o_crear_carpeta(service, str(tarjeta_empleado), _carpeta_raiz())
    fecha_id = obtener_o_crear_carpeta(service, f"{ahora:%d%m%y}", tarjeta_id)

    media = MediaIoBaseUpload(io.BytesIO(datos), mimetype=mime, resumable=False)
    archivo = service.files().create(
        body={"name": nombre, "parents": [fecha_id]}, media_body=media, fields="id"
    ).execute()
    return archivo["id"], nombre, ""


def descargar_evidencia(file_id):
    """Descarga un adjunto desde Drive (solo se llama desde el panel RH autenticado)."""
    if not RE_ID_DRIVE.fullmatch(str(file_id or "")):
        raise ErrorValidacion("Identificador de archivo inválido.")
    service = servicio_drive()
    meta = service.files().get(fileId=file_id, fields="mimeType,size").execute()
    if int(meta.get("size", 0)) > 25 * 1024 * 1024:
        raise ErrorValidacion("El archivo es demasiado grande para descargarse desde la app.")
    contenido = service.files().get_media(fileId=file_id).execute()
    return contenido, meta.get("mimeType", "application/octet-stream")


# =============================================================================
# FOLIOS (contador transaccional: sin duplicados aunque borres o haya concurrencia)
# =============================================================================
@firestore.transactional
def _tx_siguiente(tx, ref, semilla):
    snap = ref.get(transaction=tx)
    actual = (snap.to_dict() or {}).get("valor", semilla) if snap.exists else semilla
    nuevo = actual + 1
    tx.set(ref, {"valor": nuevo})
    return nuevo


def _max_folio_existente(db, prefijo):
    mayor = 0
    docs = (db.collection("quejas")
            .where("folio", ">=", prefijo).where("folio", "<=", prefijo + "\uf8ff").stream())
    for d in docs:
        m = re.search(r"(\d+)$", str(d.to_dict().get("folio", "")))
        if m:
            mayor = max(mayor, int(m.group(1)))
    return mayor


def generar_folio(db):
    """Folio anual consecutivo tipo Q-2026-0001 (contador en Firestore)."""
    anio = datetime.datetime.now().year
    ref = db.collection("contadores").document(f"folio_{anio}")
    semilla = 0 if ref.get().exists else _max_folio_existente(db, f"Q-{anio}-")
    numero = _tx_siguiente(db.transaction(), ref, semilla)
    return f"Q-{anio}-{numero:04d}"


# =============================================================================
# LECTURA PARA EL PANEL RH
# =============================================================================
@st.cache_data(ttl=60, show_spinner=False)
def cargar_quejas():
    """Últimas 1000 quejas no eliminadas. Cache de 60 s para no leer la colección en cada clic.
    Solo se llama desde el panel RH ya autenticado."""
    db = obtener_conexion()
    docs = (db.collection("quejas")
            .order_by("fecha_creacion", direction=firestore.Query.DESCENDING)
            .limit(1000).stream())
    salida = []
    for d in docs:
        item = d.to_dict()
        if item.get("eliminada"):
            continue
        item.pop("codigo_hash", None)
        item["id"] = d.id
        salida.append(item)
    return salida


# =============================================================================
# AUDITORÍA
# =============================================================================
def registrar_auditoria(db, usuario, accion, detalle=""):
    try:
        db.collection("auditoria").add({
            "usuario": str(usuario)[:60],
            "accion": str(accion)[:60],
            "detalle": str(detalle)[:500],
            "fecha": datetime.datetime.now(datetime.timezone.utc),
        })
    except Exception:
        logger.exception("No se pudo escribir la auditoría")


# =============================================================================
# VALIDACIÓN Y REGISTRO DE QUEJAS
# =============================================================================
def validar_queja(q):
    """Devuelve una lista de problemas (vacía = válida). Se ejecuta al revisar
    el lote Y otra vez en el servidor justo antes de guardar."""
    p = []
    if not validar_tarjeta(q.get("tarjeta", "")):
        p.append("El número de tarjeta debe tener de 3 a 15 caracteres (solo letras y números).")
    if not validar_nombre(q.get("nombre", "")):
        p.append("El nombre solo puede llevar letras, espacios y . ' - (de 3 a 60 caracteres).")
    if not validar_telefono(q.get("telefono", "")):
        p.append("El teléfono debe tener exactamente 10 dígitos.")
    motivo = limpiar_texto(q.get("motivo", ""), 5000)
    if len(motivo) < 10:
        p.append("El motivo debe tener al menos 10 caracteres.")
    elif len(motivo) > 2000:
        p.append("El motivo no puede pasar de 2000 caracteres.")
    try:
        monto = float(q.get("monto", 0))
        if not (0 < monto <= LIMITE_MONTO):
            raise ValueError
    except (TypeError, ValueError):
        p.append(f"El monto debe ser mayor a $0.00 y no exceder ${LIMITE_MONTO:,.0f}.")

    m = RE_QUINCENA.fullmatch(str(q.get("quincena", "")))
    anio_actual = datetime.datetime.now().year
    if not m or not (anio_actual - 3 <= int(m.group(1)) <= anio_actual + 1):
        p.append("La quincena afectada no es válida.")
    if not q.get("tipo_id") or not q.get("tipo_nombre"):
        p.append("Seleccione un tipo de queja válido.")

    if q.get("tipo_nombre") in TIPOS_CON_DIAS:
        dias = q.get("dias_incidencia_lista") or []
        if not dias:
            p.append("Debe seleccionar al menos 1 día de la incidencia.")
        elif len(dias) > 5 or not all(isinstance(d, int) and 1 <= d <= 31 for d in dias):
            p.append("Los días de incidencia no son válidos (máximo 5).")

    evidencias = q.get("evidencias") or []
    if not evidencias:
        p.append("Debe adjuntar al menos una Evidencia Principal.")
    elif len(evidencias) > MAX_EVIDENCIAS:
        p.append(f"Solo se permite un máximo de {MAX_EVIDENCIAS} archivos de evidencia.")
    for archivo in list(evidencias) + ([q["talon"]] if q.get("talon") is not None else []):
        try:
            validar_archivo(archivo)
        except ErrorValidacion as e:
            p.append(str(e))
    return p


def registrar_lote(quejas):
    """Registra el lote completo. Orden pensado para no dejar quejas a medias:
    1) revalidar todo, 2) consumir cupos, 3) subir archivos, 4) escribir en Firestore."""
    db = obtener_conexion()
    if not quejas or len(quejas) > MAX_QUEJAS_POR_LOTE:
        raise ErrorValidacion(f"El lote debe tener entre 1 y {MAX_QUEJAS_POR_LOTE} quejas.")

    catalogo = {t["id"]: t["nombre"] for t in obtener_catálogo_tipos()}
    vistos = set()
    for idx, q in enumerate(quejas, start=1):
        problemas = validar_queja(q)
        if q.get("tipo_id") not in catalogo or catalogo[q["tipo_id"]] != q.get("tipo_nombre"):
            problemas.append("El tipo de queja no es válido.")
        clave = (q.get("tarjeta"), q.get("tipo_id"), q.get("quincena"))
        if clave in vistos:
            problemas.append("Está repetida dentro del mismo lote.")
        elif not problemas and verificar_queja_duplicada(*clave):
            problemas.append("Ya existe una queja activa para esa tarjeta, tipo y quincena.")
        vistos.add(clave)
        if problemas:
            raise ErrorValidacion(f"Queja #{idx}: " + " ".join(problemas))

    for tarjeta in {q["tarjeta"] for q in quejas}:
        if not consumir_cupo(f"crear:{tarjeta}", MAX_QUEJAS_POR_TARJETA_DIA, 86400):
            raise LimiteExcedido("Se alcanzó el máximo de quejas por día para esta tarjeta. Intenta mañana.")
    if not consumir_cupo("crear:global", MAX_QUEJAS_GLOBAL_DIA, 86400):
        raise LimiteExcedido("El sistema recibió demasiadas solicitudes hoy. Intenta más tarde.")

    # Archivos primero: si alguno falla, todavía no se escribió nada en Firestore
    subidos = []
    for q in quejas:
        adj = [("Evidencia", guardar_evidencia(q["tarjeta"], f, "Evidencia")) for f in q["evidencias"]]
        if q.get("talon") is not None:
            adj.append(("Talon_Pago", guardar_evidencia(q["tarjeta"], q["talon"], "Talon_Pago")))
        subidos.append(adj)

    ahora = datetime.datetime.now(datetime.timezone.utc)
    resultados = []
    for q, adj in zip(quejas, subidos):
        folio = generar_folio(db)
        codigo = generar_codigo_seguimiento()
        ref = db.collection("quejas").document()
        lote = db.batch()
        lote.set(ref, {
            "folio": folio,
            "codigo_hash": hash_secreto(codigo),
            "nombre": limpiar_texto(q["nombre"], 60),
            "tarjeta_empleado": q["tarjeta"],
            "telefono": normalizar_telefono(q["telefono"]),
            "turno": q["turno"],
            "tipo_queja_id": q["tipo_id"],
            "tipo_nombre": q["tipo_nombre"],
            "quincena_afectada": q["quincena"],
            "monto_reclamado": float(q["monto"]),
            "dias_incidencia": q.get("dias_str"),
            "motivo": limpiar_texto(q["motivo"], 2000),
            "estatus": "Pendiente",
            "eliminada": False,
            "fecha_creacion": ahora,
        })
        for tipo, (file_id, nombre_arch, _) in adj:
            lote.set(ref.collection("adjuntos").document(), {
                "nombre_archivo": nombre_arch,
                "drive_file_id": file_id,
                "tipo_archivo": tipo,
                "fecha_subida": ahora,
            })
        lote.set(ref.collection("historial_estatus").document(), {
            "estatus_anterior": None,
            "estatus_nuevo": "Pendiente",
            "usuario_cambio": f"Emp-{q['tarjeta']}",
            "comentario": "Creación inicial de ticket",
            "fecha": ahora,
        })
        lote.commit()
        resultados.append({"folio": folio, "codigo": codigo, "tipo": q["tipo_nombre"]})
    return resultados


# =============================================================================
# CONSULTA DE ESTATUS (folio + tarjeta + código, con bloqueo por intentos)
# =============================================================================
def buscar_queja_segura(folio, tarjeta, codigo):
    """Devuelve la queja (sin datos sensibles internos) o None si los datos no coinciden.
    Lanza LimiteExcedido si hay demasiados intentos fallidos."""
    folio = str(folio or "").strip().upper()[:20]
    tarjeta = str(tarjeta or "").strip()[:40]
    codigo = normalizar_codigo(codigo)[:20]

    claves = (f"consulta:tarjeta:{tarjeta}", f"consulta:folio:{folio}")
    espera = max(esta_bloqueado(c) for c in claves)
    if espera:
        raise LimiteExcedido(f"Demasiados intentos fallidos. Intenta de nuevo en {-(-espera // 60)} minuto(s).")

    encontrada = None
    if RE_FOLIO.fullmatch(folio) and validar_tarjeta(tarjeta) and len(codigo) == 8:
        db = obtener_conexion()
        for doc in db.collection("quejas").where("folio", "==", folio).stream():
            d = doc.to_dict()
            if d.get("eliminada"):
                continue
            ok_codigo = verificar_secreto(codigo, d.get("codigo_hash") or _DUMMY_HASH)
            if comparar_texto(d.get("tarjeta_empleado"), tarjeta) and ok_codigo and d.get("codigo_hash"):
                d["id"] = doc.id
                d.pop("codigo_hash", None)
                encontrada = d
                break
    else:
        verificar_secreto(codigo, _DUMMY_HASH)   # mismo costo de tiempo en cualquier caso

    if encontrada:
        for c in claves:
            limpiar(c)
        return encontrada
    for c in claves:
        registrar_fallo(c, max_fallos=5, ventana_seg=900, bloqueo_seg=900)
    return None


def registrar_aclaracion(queja_id, texto, archivos):
    """El empleado responde a una solicitud de información adicional de RH."""
    db = obtener_conexion()
    ref = db.collection("quejas").document(queja_id)
    snap = ref.get()
    q = snap.to_dict() if snap.exists else None
    if not q or q.get("eliminada") or q.get("estatus") != "Requiere información":
        raise ErrorValidacion("Esta queja ya no está esperando información adicional.")

    texto = limpiar_texto(texto, 2000)
    if len(texto) < 5:
        raise ErrorValidacion("Escriba una aclaración de al menos 5 caracteres.")
    if len(archivos) > 3:
        raise ErrorValidacion("Máximo 3 archivos adicionales.")
    for a in archivos:
        validar_archivo(a)
    if not consumir_cupo(f"aclaracion:{queja_id}", 5, 3600):
        raise LimiteExcedido("Demasiados envíos. Intenta de nuevo más tarde.")

    subidos = [guardar_evidencia(q["tarjeta_empleado"], a, f"Aclaracion_{i}") for i, a in enumerate(archivos, 1)]

    ahora = datetime.datetime.now(datetime.timezone.utc)
    usuario = f"Empleado ({q['tarjeta_empleado']})"
    lote = db.batch()
    lote.set(ref.collection("comentarios").document(), {
        "usuario": usuario, "comentario": texto, "es_interno": False, "fecha": ahora})
    for file_id, nombre_arch, _ in subidos:
        lote.set(ref.collection("adjuntos").document(), {
            "nombre_archivo": nombre_arch, "drive_file_id": file_id,
            "tipo_archivo": "Aclaracion_Empleado", "fecha_subida": ahora})
    lote.update(ref, {"estatus": "En proceso"})
    lote.set(ref.collection("historial_estatus").document(), {
        "estatus_anterior": "Requiere información", "estatus_nuevo": "En proceso",
        "usuario_cambio": usuario, "comentario": "Se brindó aclaración y/o nuevos documentos", "fecha": ahora})
    lote.commit()
