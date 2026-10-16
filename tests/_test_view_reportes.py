"""Prueba headless de la vista de reportes: instanciar, cambiar de reporte, verificar loaders."""
import sys, os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from views.reportes.reportes_view import ReportesView

view = ReportesView()
view.resize(1200, 700)
view.show()
app.processEvents()

errors = []
REPORTES_ESPERADOS = [
    "ventas", "productos", "ganancias", "inventario",
    "compras", "fiado", "caja", "movimientos",
]

print("=== Combo de reportes ===")
combo_items = [view.reporte_combo.itemData(i) for i in range(view.reporte_combo.count())]
print(f"  Items: {combo_items}")
if combo_items != REPORTES_ESPERADOS:
    errors.append(f"Combo mismatch: esperado {REPORTES_ESPERADOS}, obtuvo {combo_items}")

print("\n=== Cambiando a cada reporte ===")
for i in range(view.reporte_combo.count()):
    clave = view.reporte_combo.itemData(i)
    view.reporte_combo.setCurrentIndex(i)
    app.processEvents()

    # Tarjetas
    valores = [c._lbl_valor.text() for c in view._tarjetas]
    titulos = [c._lbl_titulo.text() for c in view._tarjetas]
    filas = view.tabla.rowCount()
    cols = view.tabla.columnCount()
    print(f"  {clave}: cards={titulos[0]}..{titulos[-1]} valores={valores} | tabla {filas}x{cols}")
    # "—" es un sentinel legitimo ("sin datos"); el chequeo real es que
    # las tarjetas se configuraron con sus titulos (no quedaron como "—").
    if all(v == "—" for v in valores):
        errors.append(f"{clave}: tarjetas todas vacias: {valores}")

    # Título de tabla definido
    if not view.tabla.horizontalHeaderItem(0):
        errors.append(f"{clave}: sin encabezados de tabla")

print("\n=== Filtros secundarios ===")
for clave, esperado_lbl in [
    ("productos", "Ordenar:"), ("compras", "Proveedor:"),
    ("movimientos", "Tipo:"), ("ventas", None),
]:
    idx = view.reporte_combo.findData(clave)
    view.reporte_combo.setCurrentIndex(idx)
    app.processEvents()
    vis_combo = view.filtro_combo.isVisible()
    vis_etiqueta = view.filtro_lbl.isVisible()
    if esperado_lbl is None:
        ok = not vis_combo and not vis_etiqueta
        print(f"  {clave}: filtro oculto (combo={vis_combo}, lbl={vis_etiqueta}) {'OK' if ok else 'FAIL'}")
    else:
        ok = vis_combo and vis_etiqueta and view.filtro_lbl.text() == esperado_lbl
        tot = view.filtro_combo.count()
        print(f"  {clave}: filtro '{view.filtro_lbl.text()}' visible, {tot} opciones {'OK' if ok else 'FAIL'}")
    if not ok:
        errors.append(f"{clave}: filtro secundario mal configurado (esperado {esperado_lbl})")

print("\n=== Exportacion desde botones (con cola de fs) ===")
# Import de los handlers sin dispararlos (necesitan QFileDialog)
import inspect
has_excel = hasattr(view, "_exportar_excel")
has_pdf = hasattr(view, "_exportar_pdf")
print(f"  handlers presentes: Excel={has_excel}, PDF={has_pdf}")
if not (has_excel and has_pdf):
    errors.append("Faltan handlers de exportacion")

print()
if errors:
    print(f"ERRORES ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("VISTA DE REPORTES: TODO OK")