"""
Script para generar PDFs de los manuales usando reportlab
"""
import re
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.platypus import Table, TableStyle, ListFlowable, ListItem
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors

def markdown_to_pdf(md_file, pdf_file):
    """Convierte Markdown a PDF con formato básico"""

    # Leer contenido
    content = Path(md_file).read_text(encoding='utf-8')

    # Crear PDF
    doc = SimpleDocTemplate(
        str(pdf_file),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
    )

    # Estilos
    styles = getSampleStyleSheet()

    # Estilos personalizados
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        name='CustomHeading1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='CustomHeading2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='CustomHeading3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#555555'),
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='CustomCode',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#c7254e'),
        backColor=colors.HexColor('#f9f2f4'),
        fontName='Courier',
        leftIndent=20,
        rightIndent=20,
        spaceAfter=10,
        spaceBefore=10
    ))

    styles.add(ParagraphStyle(
        name='CodeBlock',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Courier',
        leftIndent=30,
        rightIndent=30,
        spaceAfter=12,
        spaceBefore=12,
        backColor=colors.HexColor('#f4f4f4')
    ))

    story = []
    lines = content.split('\n')
    i = 0
    in_code_block = False
    code_block_lines = []
    in_table = False
    table_lines = []

    while i < len(lines):
        line = lines[i]

        # Bloques de código
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_block_lines = []
            else:
                # Cerrar bloque de código
                code_text = '\n'.join(code_block_lines)
                # Escapar caracteres especiales
                code_text = code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(f'<font name="Courier" size="8">{code_text}</font>', styles['CodeBlock']))
                story.append(Spacer(1, 0.1*inch))
                in_code_block = False
                code_block_lines = []
            i += 1
            continue

        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue

        # Tablas markdown
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(line)
            i += 1
            continue
        elif in_table and not line.strip():
            # Procesar tabla
            if len(table_lines) > 2:
                table_data = []
                for tline in table_lines:
                    if '---' not in tline:  # Saltar separador
                        cells = [cell.strip() for cell in tline.split('|')[1:-1]]
                        table_data.append(cells)

                if table_data:
                    t = Table(table_data)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 0.2*inch))

            in_table = False
            table_lines = []
            i += 1
            continue
        elif in_table:
            table_lines.append(line)
            i += 1
            continue

        # Línea vacía
        if not line.strip():
            story.append(Spacer(1, 0.1*inch))
            i += 1
            continue

        # Separador horizontal
        if line.strip() == '---':
            story.append(Spacer(1, 0.05*inch))
            story.append(PageBreak())
            i += 1
            continue

        # Título principal (primer # del documento)
        if line.startswith('# ') and i < 5:
            text = line[2:].strip()
            story.append(Paragraph(text, styles['CustomTitle']))
            story.append(Spacer(1, 0.1*inch))
            i += 1
            continue

        # Headers
        if line.startswith('## '):
            text = line[3:].strip()
            # Remover enlaces de ancla
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
            story.append(Paragraph(text, styles['CustomHeading1']))
            i += 1
            continue

        if line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(text, styles['CustomHeading2']))
            i += 1
            continue

        if line.startswith('#### '):
            text = line[5:].strip()
            story.append(Paragraph(text, styles['CustomHeading3']))
            i += 1
            continue

        # Listas
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            list_items = []
            while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                item_text = lines[i].strip()[2:]
                # Procesar checkboxes
                item_text = item_text.replace('✅', '&#10003;').replace('❌', '&#10007;')
                list_items.append(ListItem(Paragraph(item_text, styles['Normal']), leftIndent=20))
                i += 1

            story.append(ListFlowable(list_items, bulletType='bullet', start='•'))
            story.append(Spacer(1, 0.1*inch))
            continue

        # Listas numeradas
        if re.match(r'^\d+\.\s', line.strip()):
            list_items = []
            while i < len(lines) and re.match(r'^\d+\.\s', lines[i].strip()):
                item_text = re.sub(r'^\d+\.\s', '', lines[i].strip())
                list_items.append(ListItem(Paragraph(item_text, styles['Normal']), leftIndent=20))
                i += 1

            story.append(ListFlowable(list_items, bulletType='1'))
            story.append(Spacer(1, 0.1*inch))
            continue

        # Texto normal (procesar negritas, código inline, etc.)
        text = line.strip()

        # Saltar metadatos del encabezado
        if text.startswith('**') and ':**' in text and i < 10:
            story.append(Paragraph(text, styles['CustomSubtitle']))
            i += 1
            continue

        # Procesar formato
        # Negritas
        text = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', text)
        # Cursivas
        text = re.sub(r'\*([^\*]+)\*', r'<i>\1</i>', text)
        # Código inline
        text = re.sub(r'`([^`]+)`', r'<font name="Courier" color="#c7254e" backColor="#f9f2f4">\1</font>', text)
        # Enlaces (mostrar solo el texto)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'<u>\1</u>', text)

        # Bloques de advertencia
        if text.startswith('> '):
            text = text[2:]
            story.append(Paragraph(f'<i>{text}</i>', styles['Normal']))
            story.append(Spacer(1, 0.05*inch))
        else:
            story.append(Paragraph(text, styles['Normal']))

        i += 1

    # Generar PDF
    doc.build(story)
    print(f"[OK] PDF generado: {pdf_file}")

if __name__ == '__main__':
    base_dir = Path(__file__).parent

    print("Generando PDFs de los manuales...")
    print()

    # Manual de Usuario
    markdown_to_pdf(
        base_dir / 'MANUAL_USUARIO.md',
        base_dir / 'MANUAL_USUARIO.pdf'
    )

    # Manual Técnico
    markdown_to_pdf(
        base_dir / 'MANUAL_TECNICO.md',
        base_dir / 'MANUAL_TECNICO.pdf'
    )

    print()
    print("=" * 60)
    print("PDFs generados exitosamente")
    print("=" * 60)
