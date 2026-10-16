"""
Servicio de generación de etiquetas de precios en PDF (lector de códigos).

Imprime etiquetas de 40 mm x 25 mm sobre hojas A4. Cada etiqueta lleva el
nombre del producto, su precio y su código de barras EAN-13/UPC-A, de modo
que el lector del punto de venta lo reconozca directamente.
"""

from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.graphics.barcode.eanbc import Ean13BarcodeWidget, UPCA
from reportlab.graphics.shapes import Drawing

# Dimensiones de la etiqueta y de la hoja
ANCHO = 40 * mm
ALTO = 25 * mm
MARGEN = 5 * mm          # margen de la hoja A4
SEPARACION = 2 * mm      # separación entre etiquetas
PADDING = 2 * mm         # relleno dentro de cada etiqueta

# Colores
BORDE = (0.85, 0.85, 0.85)     # guía de corte gris claro
TEXTO = (0.16, 0.25, 0.32)     # #2c3e50 (azul oscuro de la app)
PRECIO = (0.05, 0.12, 0.18)    # casi negro


def _grid():
    """Número de columnas y filas de etiquetas por hoja A4."""
    uso_w = A4[0] - 2 * MARGEN
    uso_h = A4[1] - 2 * MARGEN
    cols = max(1, int((uso_w + SEPARACION) // (ANCHO + SEPARACION)))
    filas = max(1, int((uso_h + SEPARACION) // (ALTO + SEPARACION)))
    return cols, filas


def _dibujar_etiqueta(c, x, y_superior, nombre, codigo, precio):
    """
    Dibujar una etiqueta cuya esquina superior-izquierda quede en (x, y_superior).
    y crece hacia arriba en reportlab, por eso se resta ALTO.
    """
    c.saveState()

    # Marco de corte
    c.setStrokeColor(BORDE)
    c.setLineWidth(0.4)
    c.rect(x, y_superior - ALTO, ANCHO, ALTO, stroke=1, fill=0)

    cx = x + ANCHO / 2.0
    ancho_contenido = ANCHO - 2 * PADDING

    # --- Nombre del producto (hasta 2 líneas, centrado) ---
    c.setFillColor(TEXTO)
    c.setFont("Helvetica", 6.5)
    lineas = simpleSplit(str(nombre), "Helvetica", 6.5, ancho_contenido)[:2]
    y = y_superior - PADDING
    alto_linea = 2.6 * mm
    for linea in lineas:
        y -= alto_linea
        c.drawString(
            x + (ANCHO - stringWidth(linea, "Helvetica", 6.5)) / 2.0,
            y,
            linea,
        )
    y -= 0.3 * mm

    # --- Precio ---
    if precio:
        c.setFillColor(PRECIO)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(cx, y - 3.2 * mm, str(precio))
        y -= 3.2 * mm + 0.5 * mm

    # --- Código de barras (rellena el espacio restante) ---
    y_base = y_superior - ALTO + PADDING
    alto_barra = max(10 * mm, y - 0.8 * mm - y_base)
    codigo_txt = str(codigo).strip()

    if len(codigo_txt) == 13 and codigo_txt.isdigit():
        cls_bar = Ean13BarcodeWidget
    elif len(codigo_txt) == 12 and codigo_txt.isdigit():
        cls_bar = UPCA
    else:
        # Sin un EAN/UPC válido: se imprime el texto tal cual.
        c.setFillColor(TEXTO)
        c.setFont("Courier", 7)
        c.drawCentredString(cx, y_base + 2 * mm, codigo_txt or "—")
        c.restoreState()
        return

    try:
        bar = cls_bar(
            codigo_txt,
            barHeight=alto_barra,
            barWidth=0.30 * mm,
            fontSize=6.5,
            humanReadable=1,
        )
        grupo = bar.draw()
        x0, y0, x1, y1 = grupo.getBounds()
        anc, alto = x1 - x0, y1 - y0
        d = Drawing(max(anc, 1), max(alto, 1))
        d.add(grupo)
        # Centrar horizontalmente y colocar en vertical centrado en el hueco.
        y_dibujo = y_base + max(0.0, (alto_barra - alto) / 2.0)
        d.drawOn(c, cx - anc / 2.0, y_dibujo)
    except Exception:
        # Nunca romper el PDF por un código raro: se imprime el número.
        c.setFillColor(TEXTO)
        c.setFont("Courier", 7)
        c.drawCentredString(cx, y_base + 2 * mm, codigo_txt)

    c.restoreState()


def generar_etiquetas(entradas, archivo_salida=None):
    """
    Generar un PDF con etiquetas de precio de 40x25 mm.

    Args:
        entradas: lista de dicts {"nombre": str, "codigo": str, "precio": str}.
            Una entrada por etiqueta (las cantidades ya vienen expandidas).
        archivo_salida: ruta del archivo .pdf. Si es None, se usa
            "etiquetas_AAAA_MM_DD_HH-MM.pdf" en el directorio actual.

    Returns:
        dict con {"exito", "total", "hojas", "ruta", "mensaje"}.
    """
    if not entradas:
        return {
            "exito": False,
            "total": 0,
            "hojas": 0,
            "ruta": "",
            "mensaje": "No hay etiquetas que generar.",
        }

    if archivo_salida is None:
        archivo_salida = Path(f"etiquetas_{datetime.now():%Y-%m-%d_%H-%M}.pdf")
    archivo_salida = Path(archivo_salida)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)

    try:
        cols, filas = _grid()
        c = pdf_canvas.Canvas(str(archivo_salida), pagesize=A4)

        for i, e in enumerate(entradas):
            col = i % cols
            fila = (i // cols) % filas
            if col == 0 and fila == 0 and i > 0:
                c.showPage()  # hoja llena -> nueva página

            x = MARGEN + col * (ANCHO + SEPARACION)
            y_superior = A4[1] - MARGEN - fila * (ALTO + SEPARACION)
            _dibujar_etiqueta(
                c,
                x,
                y_superior,
                e.get("nombre") or "",
                e.get("codigo") or "",
                e.get("precio") or "",
            )

        c.showPage()
        c.save()
    except Exception as exc:
        return {
            "exito": False,
            "total": 0,
            "hojas": 0,
            "ruta": str(archivo_salida),
            "mensaje": str(exc),
        }

    por_hoja = cols * filas
    hojas = (len(entradas) + por_hoja - 1) // por_hoja

    return {
        "exito": True,
        "total": len(entradas),
        "hojas": hojas,
        "ruta": str(archivo_salida),
        "mensaje": f"{len(entradas)} etiqueta(s) generadas ({hojas} hoja(s) A4).",
    }