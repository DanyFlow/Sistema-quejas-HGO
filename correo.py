"""Notificaciones opcionales por correo para nuevas quejas."""
import logging
import smtplib
from email.message import EmailMessage

import streamlit as st

logger = logging.getLogger("quejas")


def notificar_nueva_queja_por_correo(queja):
    """Envía una notificación si existe destinatario y configuración SMTP.

    La ausencia de configuración o cualquier fallo de correo nunca debe
    impedir que se registre una queja en Firestore.
    """
    try:
        cfg = dict(st.secrets.get("notificaciones_email", {}))
        destinatario = str(cfg.get("destinatario", "")).strip()
        if not destinatario:
            return False  # Funcionalidad desactivada: no hay destinatario.

        host = str(cfg.get("smtp_host", "")).strip()
        usuario = str(cfg.get("smtp_usuario", "")).strip()
        password = str(cfg.get("smtp_password", "")).strip()
        remitente = str(cfg.get("remitente", usuario)).strip()
        if not all((host, usuario, password, remitente)):
            logger.warning("Hay destinatario de notificaciones, pero falta configurar SMTP; se omite el correo.")
            return False

        folio = str(queja.get("folio", ""))
        tipo = str(queja.get("tipo", "Nueva queja"))
        quincena = str(queja.get("quincena", ""))
        mensaje = EmailMessage()
        mensaje["Subject"] = f"Nueva queja de nómina registrada · {folio}"
        mensaje["From"] = remitente
        mensaje["To"] = destinatario
        mensaje.set_content(
            "Se ha registrado una nueva queja en el sistema de quejas de nómina.\n\n"
            f"Folio: {folio}\nTipo de queja: {tipo}\nQuincena: {quincena}\n\n"
            "Ingresa al panel interno para consultar los detalles."
        )

        puerto = int(cfg.get("smtp_port", 465))
        usar_ssl = str(cfg.get("smtp_ssl", "true")).strip().lower() in ("1", "true", "sí", "si", "yes")
        if usar_ssl:
            with smtplib.SMTP_SSL(host, puerto, timeout=15) as servidor:
                servidor.login(usuario, password)
                servidor.send_message(mensaje)
        else:
            with smtplib.SMTP(host, puerto, timeout=15) as servidor:
                servidor.ehlo()
                servidor.starttls()
                servidor.ehlo()
                servidor.login(usuario, password)
                servidor.send_message(mensaje)
        return True
    except Exception:
        logger.exception("No se pudo enviar la notificación por correo; el registro de la queja continúa.")
        return False
