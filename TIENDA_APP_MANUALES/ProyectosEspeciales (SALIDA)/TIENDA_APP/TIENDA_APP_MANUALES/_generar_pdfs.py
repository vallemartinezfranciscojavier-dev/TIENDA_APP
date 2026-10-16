"""
Generador de PDFs: compacto, pasos claros, ejemplos visuales
"""
import re
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# Colores
C_PRIMARY = colors.HexColor('#2c3e50')
C_SECONDARY = colors.HexColor('#3498db')
C_SUCCESS = colors.HexColor('#27ae60')
C_WARNING = colors.HexColor('#f39c12')
C_DANGER = colors.HexColor('#e74c3c')
C_LIGHT = colors.HexColor('#ecf0f1')
C_DARK = colors.HexColor('#34495e')
C_CODE_BG = colors.HexColor('#f4f4f4')

class NumCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.doc_title = kwargs.pop('dt', 'Manual')
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._states = []

    def showPage(self):
        self._states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        np = len(self._states)
        for s in self._states:
            self.__dict__.update(s)
            self._draw_decor(np)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _draw_decor(self, pc):
        if self._pageNumber == 1:
            return
        self.setStrokeColor(C_SECONDARY)
        self.setLineWidth(2)
        self.line(0.75*inch, 10.5*inch, 7.75*inch, 10.5*inch)
        self.setFont('Helvetica', 8)
        self.setFillColor(C_DARK)
        self.drawString(0.75*inch, 10.6*inch, self.doc_title)
        self.drawRightString(7.75*inch, 0.5*inch, f"P{self._pageNumber}")

def portada(tit, sub, tipo):
    S = []
    S.append(Spacer(1, 1.2*inch))
    S.append(Paragraph("👤" if tipo == 'u' else "⚙",
              ParagraphStyle('ic', fontSize=60, textColor=C_SECONDARY, alignment=TA_CENTER, spaceAfter=10)))
    S.append(Paragraph(tit, ParagraphStyle('tt', fontSize=28, textColor=C_PRIMARY, alignment=TA_CENTER,
              fontName='Helvetica-Bold', spaceAfter=8, leading=32)))
    S.append(Paragraph(sub, ParagraphStyle('st', fontSize=14, textColor=C_DARK, alignment=TA_CENTER,
              fontName='Helvetica', spaceAfter=25)))
    T = Table([['Versión:', '1.0'], ['Fecha:', datetime.now().strftime("%d/%m/%Y")], ['Sistema:', 'Tienda Abarrotes']],
              colWidths=[1.3*inch, 2.5*inch])
    T.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), C_SECONDARY), ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    S.append(T)
    S.append(PageBreak())
    return S

def paso(n, txt):
    """Paso numerado visual - formato: [1] Instruccion"""
    ns = ParagraphStyle('ns', fontSize=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    ts = ParagraphStyle('ts', fontSize=10, textColor=C_DARK, leading=13)
    np = Paragraph(str(n), ns)
    tp = Paragraph(txt, ts)
    return Table([[np, tp]], colWidths=[0.35*inch, 6*inch], rowHeights=[0.35*inch]).setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), C_SECONDARY), ('BOX', (0, 0), (0, 0), 1, C_SECONDARY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 0), ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('LEFTPADDING', (1, 0), (1, 0), 10),
    ]))

def ejemplo(tit, lines):
    """Cuadro de ejemplo visual con contenido"""
    # Procesar líneas
    contenido = []
    for l in lines[:8]:  # máximo 8 líneas
        l = l.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        contenido.append(f"<br/>{l}")

    body = '<font name="Courier" size="9">' + ''.join(contenido) + '</font>'

    ts = ParagraphStyle('ts', fontSize=9, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=11)
    cs = ParagraphStyle('cs', fontSize=9, fontName='Courier', leading=11, leftIndent=5, rightIndent=5)

    tp = Paragraph(tit.replace('**', '').replace(':', ''), ts)
    cp = Paragraph(body, cs)

    return Table([[tp], [cp]], colWidths=[5.5*inch], rowHeights=[0.25*inch, None]).setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), C_SECONDARY), ('BACKGROUND', (0, 1), (0, 1), C_CODE_BG),
        ('BOX', (0, 0), (-1, -1), 2, C_SECONDARY), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, 1), 8), ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
    ]))

def alerta(txt, tp='i'):
    """Caja de alerta pequeña"""
    icons = {'i': 'ℹ', 'w': '⚠', 's': '✓', 'd': '✗'}
    bgs = {'i': colors.HexColor('#d5f4e6'), 'w': colors.HexColor('#fef5e7'),
           's': colors.HexColor('#d4efdf'), 'd': colors.HexColor('#fadbd8')}
    bds = {'i': C_SECONDARY, 'w': C_WARNING, 's': C_SUCCESS, 'd': C_DANGER}

    txt = txt.replace('**', '')
    as_ = ParagraphStyle('as', fontSize=9, textColor=C_DARK, leading=11, leftIndent=5)
    ap = Paragraph(f"<b>{icons.get(tp,'ℹ')}</b> {txt}", as_)

    return Table([[ap]], colWidths=[6.5*inch]).setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bgs.get(tp, bgs['i'])),
        ('BOX', (0, 0), (-1, -1), 2, bds.get(tp, bds['i'])),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

def gen_pdf(md, pdf, tipo):
    txt = Path(md).read_text(encoding='utf-8')
    tit = txt.split('\n')[0].replace('#', '').strip()[:40] or 'Manual'

    doc = SimpleDocTemplate(str(pdf), pagesize=letter, rightMargin=0.75, leftMargin=0.75,
                            topMargin=0.9, bottomMargin=0.7)

    st = getSampleStyleSheet()
    st.add(ParagraphStyle('h1', fontSize=17, textColor=C_PRIMARY, spaceAfter=6, spaceBefore=10, fontName='Helvetica-Bold'))
    st.add(ParagraphStyle('h2', fontSize=13, textColor=C_SECONDARY, spaceAfter=5, spaceBefore=8, fontName='Helvetica-Bold'))
    st.add(ParagraphStyle('h3', fontSize=11, textColor=C_DARK, spaceAfter=4, spaceBefore=6, fontName='Helvetica-Bold'))
    st.add(ParagraphStyle('h4', fontSize=10, textColor=C_DARK, spaceAfter=3, spaceBefore=5, fontName='Helvetica-Bold'))
    st.add(ParagraphStyle('p', fontSize=10, textColor=C_DARK, alignment=TA_JUSTIFY, spaceAfter=4, leading=13))
    st.add(ParagraphStyle('l', fontSize=10, textColor=C_DARK, leftIndent=20, spaceAfter=2, leading=12))
    st.add(ParagraphStyle('c', fontSize=8, fontName='Courier', backColor=C_CODE_BG, leftIndent=10, rightIndent=10,
                          spaceAfter=4, spaceBefore=4, leading=10))

    story = []
    story.extend(portada("Manual de Usuario" if tipo == 'u' else "Manual Técnico",
                         "Sistema de Gestión Comercial", tipo))

    lines = txt.split('\n')
    i = 0
    skip_h1 = True
    en_pasos = False
    num_paso = 0

    while i < len(lines):
        l = lines[i]

        # Detectar sección de pasos
        if 'Paso' in l and ('paso' in l or 'Pasos' in l):
            en_pasos = True
            num_paso = 0

        # Saltar primer H1 (ya está en portada)
        if l.startswith('# ') and skip_h1:
            skip_h1 = False
            i += 1
            continue

        # Headers
        if l.startswith('# '):
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(l[2:].strip(), st['h1']))
            en_pasos = False
            i += 1
            continue
        if l.startswith('## '):
            story.append(Paragraph("📍 " + l[3:].strip(), st['h2']))
            en_pasos = False
            i += 1
            continue
        if l.startswith('### '):
            txt3 = l[4:].strip()
            # Si es paso numerado
            if en_pasos and re.match(r'^\d+\.', txt3):
                num_paso += 1
                txtp = re.sub(r'^\d+\.\s*', '', txt3)
                story.append(paso(num_paso, txtp))
                i += 1
                continue
            story.append(Paragraph("▸ " + txt3, st['h3']))
            i += 1
            continue
        if l.startswith('#### '):
            story.append(Paragraph(l[5:].strip(), st['h4']))
            i += 1
            continue

        # Bloques de código
        if l.strip().startswith('```'):
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code.append(lines[i].replace('<', '&lt;').replace('>', '&gt;'))
                i += 1
            if code:
                ct = Paragraph('<font name="Courier" size="8">' + '<br/>'.join(code) + '</font>', st['c'])
                story.append(Table([[ct]], colWidths=[6.5*inch]).setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), C_CODE_BG), ('BOX', (0, 0), (-1, -1), 1, colors.grey),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10), ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ])))
                story.append(Spacer(1, 0.05*inch))
            i += 1
            continue

        # Listas numeradas (pasos)
        if re.match(r'^\d+\.\s', l.strip()):
            num_paso += 1
            t = re.sub(r'^\d+\.\s*', '', l.strip())
            story.append(paso(num_paso, t))
            i += 1
            continue

        # Listas con bullets
        if l.strip().startswith(('- ', '* ')):
            bt = l.strip()[2:]
            bt = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', bt)
            bt = re.sub(r'`([^`]+)`', r'<font color="#c7254e">\1</font>', bt)
            story.append(Paragraph(f"• {bt}", st['l']))
            i += 1
            continue

        # Ejemplos: detectar línea con "**Ejemplo:**" o "Ejemplo:"
        if '**Ejemplo**' in l or '**Ejemplo:**' in l or l.strip().startswith('Ejemplo:'):
            # Recolectar siguientes líneas
            ej_lines = []
            j = i + 1
            while j < len(lines) and lines[j].strip():
                if lines[j].startswith('#') or lines[j].startswith('```'):
                    break
                ej_lines.append(lines[j].strip())
                j += 1
            if ej_lines:
                tit_ej = l.replace('**', '').replace(':', '')
                story.append(ejemplo(tit_ej, ej_lines))
                story.append(Spacer(1, 0.05*inch))
                i = j
                continue

        # Bloques de alerta
        if l.strip().startswith('>'):
            txt_a = l.strip()[2:].replace('**', '')
            tp_a = 'w' if ('IMPORTANTE' in txt_a.upper() or '⚠' in txt_a) else 'i'
            story.append(alerta(txt_a, tp_a))
            i += 1
            continue

        # Línea vacía
        if not l.strip():
            story.append(Spacer(1, 0.03*inch))
            i += 1
            continue

        # Separador
        if l.strip() == '---' and i > 10:
            story.append(PageBreak())
            i += 1
            continue

        # Párrafo normal
        p = l.strip()
        p = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', p)
        p = re.sub(r'\*([^\*]+)\*', r'<i>\1</i>', p)
        p = re.sub(r'`([^`]+)`', r'<font color="#c7254e">\1</font>', p)

        # Saltar metadatos al inicio
        if p.startswith('**') and ':**' in p and i < 15:
            i += 1
            continue

        story.append(Paragraph(p, st['p']))
        i += 1

    doc.build(story, canvasmaker=lambda *a, **kw: NumCanvas(*a, dt=tit, **kw))
    print(f"[OK] {Path(pdf).name}")

if __name__ == '__main__':
    d = Path('.')
    print("="*50)
    print("Generando PDFs optimizados...")
    gen_pdf(d / 'MANUAL_USUARIO.md', d / 'MANUAL_USUARIO.pdf', 'u')
    gen_pdf(d / 'MANUAL_TECNICO.md', d / 'MANUAL_TECNICO.pdf', 't')
    print("="*50)
    print("Listo!")