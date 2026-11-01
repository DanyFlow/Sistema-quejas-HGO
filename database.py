import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st


@st.cache_resource
def init_firebase():
    """Inicializa Firestore con la cuenta de servicio guardada en st.secrets["firebase"]."""
    if not firebase_admin._apps:
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def obtener_conexion():
    """Retorna la instancia del cliente de Firestore"""
    return init_firebase()


_TIPOS_POR_DEFECTO = [
    {"nombre": "Descuento por omisión", "requiere_monto": True, "activo": True},
    {"nombre": "Permiso no aplicado", "requiere_monto": True, "activo": True},
    {"nombre": "Falta de pago de horas extra", "requiere_monto": True, "activo": True},
    {"nombre": "Descuento indebido de nómina", "requiere_monto": True, "activo": True},
    {"nombre": "Incapacidad no aplicada", "requiere_monto": True, "activo": True},
    {"nombre": "Diferencia en pago de bono", "requiere_monto": True, "activo": True},
    {"nombre": "Otro tipo de incidencia", "requiere_monto": True, "activo": True},
]


@st.cache_data(ttl=300, show_spinner=False)
def obtener_catálogo_tipos():
    """Catálogo de tipos de queja activos (cacheado 5 min: es público y casi no cambia)."""
    db = obtener_conexion()
    catalogo = []
    for doc in db.collection("tipos_queja").where("activo", "==", True).stream():
        data = doc.to_dict()
        data["id"] = doc.id
        catalogo.append(data)

    # Si la colección está vacía se crean los valores por defecto
    if not catalogo:
        batch = db.batch()
        for base in _TIPOS_POR_DEFECTO:
            item = dict(base)
            doc_ref = db.collection("tipos_queja").document()
            batch.set(doc_ref, item)
            item["id"] = doc_ref.id
            catalogo.append(item)
        batch.commit()

    return catalogo


def verificar_queja_duplicada(tarjeta, tipo_id, quincena):
    """¿Existe una queja activa (no resuelta/rechazada/eliminada) con la misma tarjeta, tipo y quincena?"""
    db = obtener_conexion()
    query = (
        db.collection("quejas")
        .where("tarjeta_empleado", "==", tarjeta)
        .where("tipo_queja_id", "==", tipo_id)
        .where("quincena_afectada", "==", quincena)
        .stream()
    )
    for doc in query:
        data = doc.to_dict()
        if data.get("eliminada"):
            continue
        if data.get("estatus") not in ["Resuelto", "Rechazada"]:
            return True
    return False
