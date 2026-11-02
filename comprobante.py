"""Comprobante en PDF con el folio y la clave de cada queja (letra grande, fácil de imprimir)."""
import io
import textwrap

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _s(texto):
    """Texto seguro para las fuentes estándar del PDF (Latin-1/cp1252)."""
    return str(texto if texto is not None else "").encode("cp1252", "replace").decode("cp1252")


def generar_pdf(resultados, empresa="", fecha_txt="", pie_lineas=()):
    """resultados: lista de dicts con 'folio', 'codigo' (clave de 8 caracteres) y 'tipo'."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("Comprobante de queja de nómina")
    ancho, alto = A4
    margen = 50
    util = ancho - 2 * margen

    def encabezado():
        y = alto - 60
        c.setFont("Helvetica-Bold", 20)
        c.drawString(margen, y, "Comprobante de queja de nómina")
        y -= 22
        c.setFont("Helvetica", 11)
        if empresa:
            c.drawString(margen, y, _s(empresa))
            y -= 16
        if fecha_txt:
            c.drawString(margen, y, _s(f"Fecha de registro: {fecha_txt}"))
            y -= 16
        return y - 10

    y = encabezado()
    c.setFont("Helvetica", 12)
    intro = ("Guarda este documento. Con tu folio, tu número de tarjeta y tu clave puedes consultar "
             "cómo va tu queja en la aplicación, cuando quieras.")
    for linea in textwrap.wrap(intro, 82):
        c.drawString(margen, y, _s(linea))
        y -= 16
    y -= 12

    alto_bloque = 100
    for r in resultados:
        if y - alto_bloque < 110:           # salto de página si ya no cabe
            c.showPage()
            y = encabezado()
        c.setLineWidth(1.2)
        c.roundRect(margen, y - alto_bloque, util, alto_bloque, 10)
        c.setFont("Helvetica", 11)
        c.drawString(margen + 14, y - 20, _s(f"Queja: {r.get('tipo', '')}")[:90])
        c.setFont("Helvetica", 10)
        c.drawString(margen + 14, y - 46, "FOLIO")
        c.drawString(margen + util / 2, y - 46, "TU CLAVE PARA CONSULTAR")
        c.setFont("Helvetica-Bold", 22)
        c.drawString(margen + 14, y - 74, _s(r.get("folio", "")))
        clave = _s(r.get("codigo", ""))
        clave = f"{clave[:4]}-{clave[4:]}" if len(clave) == 8 else clave
        c.setFont("Courier-Bold", 26)
        c.drawString(margen + util / 2, y - 76, clave)
        y -= alto_bloque + 16

    y -= 6
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margen, y, "No compartas tu clave con nadie.")
    y -= 16
    c.setFont("Helvetica", 11)
    for linea in textwrap.wrap("Si la pierdes, comunícate con Recursos Humanos para que te ayuden.", 90):
        c.drawString(margen, y, _s(linea))
        y -= 15
    y -= 8
    c.setFont("Helvetica", 9)
    for linea in pie_lineas:
        c.drawString(margen, y, _s(linea))
        y -= 12

    c.save()
    return buf.getvalue()
