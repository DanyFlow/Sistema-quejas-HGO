"""Límite de intentos y cupos usando Firestore (colección `intentos`).

Las claves se guardan como SHA-256, así que en la base no queda la tarjeta,
el folio ni el usuario en claro. Cada documento trae un campo `expira`
(configura una política TTL en Firestore para que se limpien solos).
"""
import datetime as dt
import hashlib

from firebase_admin import firestore

from database import obtener_conexion

COLECCION = "intentos"


def _ahora():
    return dt.datetime.now(dt.timezone.utc)


def _ref(clave: str):
    huella = hashlib.sha256(clave.encode("utf-8")).hexdigest()
    return obtener_conexion().collection(COLECCION).document(huella)


# ------------------------- bloqueo por intentos fallidos -------------------------
@firestore.transactional
def _tx_fallo(tx, ref, ahora, max_fallos, ventana_seg, bloqueo_seg):
    snap = ref.get(transaction=tx)
    datos = snap.to_dict() if snap.exists else {}
    inicio = datos.get("inicio")
    fallos = datos.get("fallos", 0)
    if not inicio or (ahora - inicio).total_seconds() > ventana_seg:
        inicio, fallos = ahora, 0
    fallos += 1
    nuevo = {
        "inicio": inicio,
        "fallos": fallos,
        "expira": ahora + dt.timedelta(seconds=max(ventana_seg, bloqueo_seg) + 3600),
    }
    if fallos >= max_fallos:
        nuevo["bloqueado_hasta"] = ahora + dt.timedelta(seconds=bloqueo_seg)
    tx.set(ref, nuevo)


def esta_bloqueado(clave: str) -> int:
    """Segundos restantes de bloqueo (0 si no está bloqueado)."""
    snap = _ref(clave).get()
    if not snap.exists:
        return 0
    hasta = (snap.to_dict() or {}).get("bloqueado_hasta")
    if not hasta:
        return 0
    restante = (hasta - _ahora()).total_seconds()
    return int(restante) + 1 if restante > 0 else 0


def registrar_fallo(clave: str, max_fallos: int = 5, ventana_seg: int = 900, bloqueo_seg: int = 900):
    tx = obtener_conexion().transaction()
    _tx_fallo(tx, _ref(clave), _ahora(), max_fallos, ventana_seg, bloqueo_seg)


def limpiar(clave: str):
    _ref(clave).delete()


# ------------------------------ cupos por ventana --------------------------------
@firestore.transactional
def _tx_cupo(tx, ref, ahora, maximo, ventana_seg):
    snap = ref.get(transaction=tx)
    datos = snap.to_dict() if snap.exists else {}
    inicio = datos.get("inicio")
    usados = datos.get("usados", 0)
    if not inicio or (ahora - inicio).total_seconds() > ventana_seg:
        inicio, usados = ahora, 0
    if usados >= maximo:
        return False
    tx.set(ref, {
        "inicio": inicio,
        "usados": usados + 1,
        "expira": ahora + dt.timedelta(seconds=ventana_seg + 3600),
    })
    return True


def consumir_cupo(clave: str, maximo: int, ventana_seg: int) -> bool:
    """True si todavía hay cupo (y lo consume); False si ya se agotó."""
    tx = obtener_conexion().transaction()
    return _tx_cupo(tx, _ref(clave), _ahora(), maximo, ventana_seg)
