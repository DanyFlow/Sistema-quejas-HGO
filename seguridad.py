"""Utilidades de seguridad SIN dependencias de Streamlit ni Firebase.

Aquí vive todo lo que valida o sanea datos que escribe el usuario:
formatos, texto libre, archivos subidos, hashing de contraseñas/códigos,
escape de Markdown y construcción segura de enlaces de WhatsApp.
"""
import base64
import hashlib
import hmac
import os
import re
import secrets
from urllib.parse import quote


# ----------------------------------------------------------------------------
# Excepciones propias (mensajes pensados para mostrarse al usuario)
# ----------------------------------------------------------------------------
class ErrorValidacion(Exception):
    """Dato inválido; el mensaje es seguro de mostrar al usuario."""


class LimiteExcedido(Exception):
    """Demasiados intentos / cupo agotado; el mensaje es seguro de mostrar."""


# ----------------------------------------------------------------------------
# Formatos permitidos
# ----------------------------------------------------------------------------
RE_TARJETA = re.compile(r"[A-Za-z0-9]{3,15}")          # ajústalo a solo dígitos si tus tarjetas lo son
RE_TELEFONO = re.compile(r"\d{10}")
RE_NOMBRE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'\-]{2,59}")
RE_FOLIO = re.compile(r"Q-\d{4}-\d{4,6}")
RE_QUINCENA = re.compile(r"(\d{4})-(0[1-9]|1[0-2])Q([12])")
RE_ID_DRIVE = re.compile(r"[A-Za-z0-9_-]{10,100}")

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def limpiar_texto(valor, max_len=2000):
    """Quita caracteres de control, normaliza saltos de línea y recorta."""
    texto = "" if valor is None else str(valor)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = _CONTROL.sub("", texto)
    return texto.strip()[:max_len]


def normalizar_telefono(valor):
    return re.sub(r"[\s\-()]", "", str(valor or ""))


def validar_tarjeta(valor):
    return bool(RE_TARJETA.fullmatch(str(valor or "")))


def validar_telefono(valor):
    return bool(RE_TELEFONO.fullmatch(normalizar_telefono(valor)))


def validar_nombre(valor):
    return bool(RE_NOMBRE.fullmatch(str(valor or "")))


# ----------------------------------------------------------------------------
# Hash de contraseñas y códigos de seguimiento (PBKDF2-SHA256, solo stdlib)
# ----------------------------------------------------------------------------
ITERACIONES_PBKDF2 = 600_000
_MAX_ITERACIONES = 2_000_000
_SAL_DUMMY = b"\x00" * 16


def _b64(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")


def hash_secreto(valor: str, iteraciones: int = ITERACIONES_PBKDF2) -> str:
    sal = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", valor.encode("utf-8"), sal, iteraciones)
    return f"pbkdf2_sha256${iteraciones}${_b64(sal)}${_b64(dk)}"


def verificar_secreto(valor: str, almacenado: str) -> bool:
    """Compara en tiempo constante. Si el hash es inválido hace un cálculo
    de relleno para que el tiempo de respuesta no delate si el usuario existe."""
    try:
        algoritmo, it, sal_b64, dk_b64 = str(almacenado).split("$")
        iteraciones = int(it)
        if algoritmo != "pbkdf2_sha256" or not (1 <= iteraciones <= _MAX_ITERACIONES):
            raise ValueError
        sal = base64.b64decode(sal_b64)
        esperado = base64.b64decode(dk_b64)
    except Exception:
        hashlib.pbkdf2_hmac("sha256", str(valor).encode("utf-8"), _SAL_DUMMY, ITERACIONES_PBKDF2)
        return False
    calculado = hashlib.pbkdf2_hmac("sha256", str(valor).encode("utf-8"), sal, iteraciones)
    return hmac.compare_digest(calculado, esperado)


# Código de seguimiento: 8 caracteres sin ambiguos (sin 0/O/1/I) -> ~1.1e12 combinaciones
_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generar_codigo_seguimiento() -> str:
    return "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(8))


def formatear_codigo(codigo: str) -> str:
    return f"{codigo[:4]}-{codigo[4:]}"


def normalizar_codigo(valor) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(valor or "").upper())


def comparar_texto(a, b) -> bool:
    return hmac.compare_digest(str(a or "").encode("utf-8"), str(b or "").encode("utf-8"))


# ----------------------------------------------------------------------------
# Escape de Markdown (evita enlaces/imagenes/formato inyectado por empleados)
# ----------------------------------------------------------------------------
_MD_ESPECIALES = re.compile(r"([\\`*_{}\[\]()#+\-.!|>~<$:&])")


def escapar_md(valor) -> str:
    """Devuelve el texto listo para usarse dentro de st.write/st.markdown
    sin que se interprete como Markdown, LaTeX o directivas de Streamlit."""
    texto = "" if valor is None else str(valor)
    texto = _MD_ESPECIALES.sub(r"\\\1", texto)
    return texto.replace("\r", "").replace("\n", "  \n")


# ----------------------------------------------------------------------------
# WhatsApp
# ----------------------------------------------------------------------------
def link_whatsapp(telefono, texto):
    """Enlace wa.me seguro o None si el teléfono no es válido."""
    tel = normalizar_telefono(telefono)
    if not RE_TELEFONO.fullmatch(tel):
        return None
    return f"https://wa.me/521{tel}?text={quote(str(texto), safe='')}"


# ----------------------------------------------------------------------------
# Archivos subidos
# ----------------------------------------------------------------------------
MAX_BYTES_ARCHIVO = 5 * 1024 * 1024
_FIRMAS = (
    (b"%PDF-", "application/pdf", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
)
_MARCAS_PDF_PELIGROSAS = (b"/JavaScript", b"/Launch", b"/EmbeddedFile")


def sanear_nombre(nombre, ext=None, max_len=60):
    """Nombre de archivo seguro: solo [A-Za-z0-9._-]."""
    base, ext_orig = os.path.splitext(os.path.basename(str(nombre or "archivo")))
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("._") or "archivo"
    ext = (ext or ext_orig.lstrip(".") or "bin")
    ext = re.sub(r"[^A-Za-z0-9]", "", ext)[:5] or "bin"
    return f"{base[:max_len]}.{ext}"


def validar_archivo(archivo):
    """Valida un archivo de st.file_uploader mirando su CONTENIDO real
    (no la extensión ni el tipo que declara el navegador).

    Devuelve (bytes, mime, extension). Lanza ErrorValidacion si no es válido.
    """
    nombre = sanear_nombre(getattr(archivo, "name", "archivo"))
    datos = archivo.getvalue()
    if not datos:
        raise ErrorValidacion(f"El archivo {nombre} está vacío.")
    if len(datos) > MAX_BYTES_ARCHIVO:
        raise ErrorValidacion(f"El archivo {nombre} pesa más de {MAX_BYTES_ARCHIVO // (1024 * 1024)} MB.")
    for firma, mime, ext in _FIRMAS:
        if datos.startswith(firma):
            break
    else:
        raise ErrorValidacion(f"El archivo {nombre} no es un PDF, PNG o JPG válido.")
    if mime == "application/pdf" and any(m in datos for m in _MARCAS_PDF_PELIGROSAS):
        raise ErrorValidacion(f"El PDF {nombre} contiene elementos activos (scripts/archivos incrustados) y no se permite.")
    return datos, mime, ext
