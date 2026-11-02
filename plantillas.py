"""Respuestas rápidas del panel RH (sin dependencias de Streamlit/Firebase).

PARA CAMBIAR O AGREGAR FRASES: edita la lista PLANTILLAS (no hace falta tocar app.py).

Cada plantilla tiene:
  etiqueta -> texto del botón
  estatus  -> para qué estatus se sugiere (debe ser: Pendiente, En proceso, Requiere información,
              Resuelto o Rechazada)
  texto    -> lo que se inserta en el cuadro de respuesta. Puede usar {nombre} (solo el primer
              nombre) y {folio}. Lo que lleve [COMPLETAR] OBLIGA al analista a escribirlo antes
              de guardar: así no se envía una frase a medias.
"""

MARCA_COMPLETAR = "[COMPLETAR]"

PLANTILLAS = [
    {"etiqueta": "🔎 Estamos revisando", "estatus": "En proceso",
     "texto": "Hola {nombre}, recibimos tu queja con folio {folio} y ya la estamos revisando. "
              "Te daremos respuesta a la brevedad."},
    {"etiqueta": "🕒 Validando asistencia", "estatus": "En proceso",
     "texto": "Hola {nombre}, estamos validando tu asistencia de los días indicados en tu queja con folio {folio}. "
              "Te avisaremos en cuanto tengamos respuesta."},
    {"etiqueta": "📞 Te contactaremos", "estatus": "En proceso",
     "texto": "Hola {nombre}, nos pondremos en contacto contigo por teléfono o WhatsApp para aclarar tu queja "
              "con folio {folio}."},
    {"etiqueta": "📎 Necesitamos documentos", "estatus": "Requiere información",
     "texto": "Hola {nombre}, para continuar con tu queja con folio {folio} necesitamos que nos envíes lo siguiente: "
              "[COMPLETAR]. Puedes responder desde «Consultar mi queja»."},
    {"etiqueta": "❓ Falta aclarar un dato", "estatus": "Requiere información",
     "texto": "Hola {nombre}, para resolver tu queja con folio {folio} necesitamos que nos aclares lo siguiente: "
              "[COMPLETAR]. Puedes responder desde «Consultar mi queja»."},
    {"etiqueta": "✅ Ajuste aplicado", "estatus": "Resuelto",
     "texto": "Hola {nombre}, se aplicó el ajuste correspondiente a tu queja con folio {folio}. "
              "Lo verás reflejado en tu siguiente pago."},
    {"etiqueta": "💰 Pago programado", "estatus": "Resuelto",
     "texto": "Hola {nombre}, el pago pendiente de tu queja con folio {folio} quedó programado y se te cubrirá el "
              "[COMPLETAR]."},
    {"etiqueta": "❌ No procede", "estatus": "Rechazada",
     "texto": "Hola {nombre}, revisamos tu queja con folio {folio} y no procede porque [COMPLETAR]. "
              "Si tienes más información, puedes registrarla de nuevo."},
    {"etiqueta": "🔁 Queja duplicada", "estatus": "Rechazada",
     "texto": "Hola {nombre}, tu queja con folio {folio} ya estaba registrada con el folio [COMPLETAR], "
              "por eso la cerramos. Puedes seguir el avance en ese folio."},
]


def primer_nombre(nombre):
    partes = str(nombre or "").split()
    return partes[0] if partes else ""


def rellenar(texto, ticket):
    """Sustituye {nombre} y {folio}. Usa reemplazo simple (no .format) para que nada más se interprete."""
    nombre = primer_nombre(ticket.get("nombre"))
    if not nombre:
        texto = texto.replace(" {nombre}", "")
    return texto.replace("{folio}", str(ticket.get("folio", ""))).replace("{nombre}", nombre)
