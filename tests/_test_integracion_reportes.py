"""Integración: la estructura que construye la vista se exporta correctamente a Excel/PDF."""
import sys, os, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from datetime import timedelta

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from views.reportes.reportes_view import ReportesView
from services.exportacion_service import exportar_reporte_excel, exportar_reporte_pdf

view = ReportesView()
view.resize(1200, 700)
view.show()
app.processEvents()

# Periodo personalizado: ultimos 90 dias
idx = view.periodo_combo.findData("personalizado")
view.periodo_combo.setCurrentIndex(idx)
app.processEvents()
view.desde_edit.setDate(view.desde_edit.date().addDays(-90))
app.processEvents()

errors = []

print("=== Exportacion de la estructura de la vista (periodo 90 dias) ===")
for i in range(view.reporte_combo.count()):
    clave = view.reporte_combo.itemData(i)
    view.reporte_combo.setCurrentIndex(i)
    app.processEvents()

    datos = view._datos
    ruta_x = os.path.join(tempfile.gettempdir(), f"view_{clave}.xlsx")
    ruta_p = os.path.join(tempfile.gettempdir(), f"view_{clave}.pdf")
    try:
        exportar_reporte_excel(ruta_x, datos)
        exportar_reporte_pdf(ruta_p, datos)
        sx, sp = os.path.getsize(ruta_x), os.path.getsize(ruta_p)
        filas = len(datos["tabla"].get("filas", []))
        print(f"  {clave:11s}: tabla {filas} filas | xlsx {sx}B pdf {sp}B  periodo='{datos.get('periodo_label')}'")
    except Exception as e:
        import traceback; traceback.print_exc()
        errors.append((clave, e))

# Verificacion clave: ventas en 90 dias debe traer el ticket real
view.reporte_combo.setCurrentIndex(view.reporte_combo.findData("ventas"))
app.processEvents()
tot_sql = view._datos["resumen"][0]  # (Total vendido, valor, tipo)
print(f"\n  VENTAS 90d resumen[0] = {tot_sql}  (esperado $22.00)")
if abs(float(tot_sql[1]) - 22.0) > 0.001:
    errors.append(("ventas_90d", f"total esperado 22, obtuvo {tot_sql[1]}"))

view.reporte_combo.setCurrentIndex(view.reporte_combo.findData("compras"))
app.processEvents()
comp = view._datos["resumen"][0]
print(f"  COMPRAS 90d resumen[0] = {comp}  (esperado $1,178.00)")
if abs(float(comp[1]) - 1178.0) > 0.001:
    errors.append(("compras_90d", f"total esperado 1178, obtuvo {comp[1]}"))

view.reporte_combo.setCurrentIndex(view.reporte_combo.findData("inventario"))
app.processEvents()
inv_first = view._datos["resumen"][0]
print(f"  INVENTARIO resumen[0] = {inv_first}  (esperado $1,652.00)")
if abs(float(inv_first[1]) - 1652.0) > 0.001:
    errors.append(("inventario", f"valor costo esperado 1652, obtuvo {inv_first[1]}"))

print()
if errors:
    print(f"ERRORES ({len(errors)}):")
    for e in errors:
        print(f"  - {e[0]}: {e[1]}")
    sys.exit(1)
else:
    print("INTEGRACION VISTA → EXPORT: TODOS LOS REPORTES OK")