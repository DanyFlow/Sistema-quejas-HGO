"""Roles y permisos del panel interno (sin dependencias de Streamlit/Firebase).

REGLA: un rol que no esté en PERMISOS no puede iniciar sesión ni hacer nada
("denegar por defecto"). Para crear un rol nuevo agrega una entrada en PERMISOS
y asígnalo en los secretos: [usuarios_rh.<usuario>] rol = "<nombre exacto>".
"""

ROL_RH = "RH"                                   # analista
ROL_ADMIN = "Administrador"
ROL_CONTROL = "Control de asistencia"

_PERMISOS_ANALISTA = frozenset({
    "ver_telefono",              # ve el teléfono del empleado
    "ver_monto",                 # ve el monto reclamado
    "ver_talon",                 # ve el talón de pago adjunto
    "descargar_adjuntos",
    "gestionar_ticket",          # cambiar estatus, responder al empleado, notas internas, WhatsApp
    "whatsapp",
    "solicitar_info_control",    # pedir información a Control de asistencia
    "ver_solicitudes_control",
})

PERMISOS = {
    ROL_RH: _PERMISOS_ANALISTA,
    ROL_ADMIN: _PERMISOS_ANALISTA | {"eliminar_folios"},
    # Control de asistencia: solo lectura + responder solicitudes que el analista le haga.
    # No ve teléfono, monto ni talón de pago, y no modifica tickets.
    ROL_CONTROL: frozenset({
        "descargar_adjuntos",
        "ver_solicitudes_control",
        "responder_solicitud_control",
    }),
}

# Si quieres que Control de asistencia solo vea ciertos tipos de queja, pon aquí sus nombres
# (por ejemplo ["Permiso no aplicado", "Descuento por omisión"]). None = ve todos.
TIPOS_VISIBLES_CONTROL = None

# Campos que se QUITAN de los datos de quien no tenga el permiso
CAMPOS_RESTRINGIDOS = {
    "telefono": "ver_telefono",
    "monto_reclamado": "ver_monto",
}

# A quién le avisa cada tipo de evento (notificaciones al iniciar sesión)
DESTINATARIOS = {
    "nueva_queja": (ROL_RH, ROL_ADMIN, ROL_CONTROL),
    "aclaracion_empleado": (ROL_RH, ROL_ADMIN, ROL_CONTROL),
    "solicitud_control": (ROL_CONTROL,),
    "respuesta_control": (ROL_RH, ROL_ADMIN),
}

ICONOS_EVENTO = {
    "nueva_queja": "🆕",
    "aclaracion_empleado": "📎",
    "solicitud_control": "🕒",
    "respuesta_control": "✅",
}


def rol_valido(rol) -> bool:
    return rol in PERMISOS


def puede(rol, accion) -> bool:
    return accion in PERMISOS.get(rol, frozenset())


def limpiar_queja_para_rol(queja: dict, rol) -> dict:
    """Copia de la queja sin los campos que el rol no puede ver."""
    return {k: v for k, v in queja.items()
            if not (k in CAMPOS_RESTRINGIDOS and not puede(rol, CAMPOS_RESTRINGIDOS[k]))}


def quejas_visibles_para_rol(quejas: list, rol) -> list:
    if rol == ROL_CONTROL and TIPOS_VISIBLES_CONTROL:
        return [q for q in quejas if q.get("tipo_nombre") in TIPOS_VISIBLES_CONTROL]
    return quejas
