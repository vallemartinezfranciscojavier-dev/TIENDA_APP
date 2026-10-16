"""Prueba headless integral de los 8 reportes + exportación Excel/PDF."""
import sys, os, tempfile
from datetime import datetime, timedelta
from decimal import Decimal

from services.reportes_service import ReportesService
from services.exportacion_service import exportar_reporte_excel, exportar_reporte_pdf

svc = ReportesService()
fin = datetime.now()
ini = fin - timedelta(days=90)

def base(titulo, clave, resumen, tabla, extra=None):
    return {
        "reporte": clave,
        "titulo": titulo,
        "periodo_label": "del 01/09/2026 al 13/09/2026",
        "fecha_generacion": datetime.now(),
        "resumen": resumen,
        "tabla": tabla,
        "tablas_extra": extra or [],
    }

errors = []

# ── 1) Ventas ────────────────────────────────────────────────────────
try:
    r = svc.resumen_periodo(ini, fin)
    d = svc.descuentos_periodo(ini, fin)
    m = svc.por_metodo_pago(ini, fin)
    v = svc.ventas_periodo(ini, fin, 300)
    filas = []
    for vv in v:
        filas.append([vv["folio"], str(vv["fecha"]), vv["usuario"],
                      vv["cliente"], vv["metodo"], float(vv["total"])])
    met_extra = {
        "titulo": "Metodos de pago",
        "encabezados": ["Metodo", "Total"],
        "filas": [[mm["etiqueta"], float(mm["total"])] for mm in m],
        "columnas_moneda": [1], "columnas_cantidad": [], "columnas_enteros": [],
    }
    datos = base("Reporte de ventas", "ventas", [
        ("Total vendido", r["total"], "moneda"),
        ("Tickets", r["tickets"], "numero"),
        ("Descuentos", d["total"], "moneda"),
        ("Promedio", r["promedio"], "moneda"),
    ], {
        "encabezados": ["Folio", "Fecha", "Usuario", "Cliente", "Metodo", "Total"],
        "filas": filas,
        "columnas_moneda": [5], "columnas_cantidad": [], "columnas_enteros": [],
    }, [met_extra])
    exportar_reporte_excel(tempfile.gettempdir() + "/rep_ventas.xlsx", datos)
    exportar_reporte_pdf(tempfile.gettempdir() + "/rep_ventas.pdf", datos)
    print("1 Ventas: OK")
except Exception as e:
    errors.append(("Ventas", e))
    import traceback; traceback.print_exc()
    print("1 Ventas: FAIL", e)

# ── 2) Productos vendidos ────────────────────────────────────────────
try:
    p = svc.productos_vendidos_detalle(ini, fin, "mas", 100)
    filas = []
    for i, pp in enumerate(p, 1):
        nombre = pp.get("name") or pp.get("nombre") or ""
        filas.append([i, nombre, pp["cantidad"],
                       float(pp["precio_promedio"]), float(pp["monto"])])
    cant = sum((pp["cantidad"] for pp in p), Decimal("0"))
    monto = sum((pp["monto"] for pp in p), Decimal("0"))
    datos = base("Productos vendidos", "productos", [
        ("Productos", len(p), "numero"),
        ("Unidades", cant, "cantidad"),
        ("Monto", monto, "moneda"),
        ("Precio prom.", Decimal("22"), "moneda"),
    ], {
        "encabezados": ["#", "Producto", "Cant", "Pprom", "Monto"],
        "filas": filas,
        "columnas_moneda": [3, 4], "columnas_cantidad": [2], "columnas_enteros": [0],
    })
    exportar_reporte_excel(tempfile.gettempdir() + "/rep_prod.xlsx", datos)
    exportar_reporte_pdf(tempfile.gettempdir() + "/rep_prod.pdf", datos)
    print("2 Productos: OK")
except Exception as e:
    errors.append(("Productos", e))
    import traceback; traceback.print_exc()
    print("2 Productos: FAIL", e)

# ── 3) Ganancias ─────────────────────────────────────────────────────
try:
    g = svc.ganancias_resumen(ini, fin)
    gd = svc.ganancias_periodo(ini, fin, 100)
    filas = []
    for i, gg in enumerate(gd, 1):
        filas.append([i, gg["nombre"], gg["cantidad"],
                       float(gg["ingreso"]), float(gg["costo"]),
                       float(gg["ganancia"]), float(gg["margen"])])
    datos = base("Ganancias", "ganancias", [
        ("Ventas", g["ventas"], "moneda"),
        ("Costo", g["costo"], "moneda"),
        ("Ganancia", g["ganancia"], "moneda"),
        ("Margen", g["margen"], "porcentaje"),
    ], {
        "encabezados": ["#", "Prod", "Cant", "Ingr", "Cost", "Gan", "Margen"],
        "filas": filas,
        "columnas_moneda": [3, 4, 5], "columnas_cantidad": [2, 6], "columnas_enteros": [0],
    })
    exportar_reporte_excel(tempfile.gettempdir() + "/rep_gan.xlsx", datos)
    exportar_reporte_pdf(tempfile.gettempdir() + "/rep_gan.pdf", datos)
    print("3 Ganancias: OK")
except Exception as e:
    errors.append(("Ganancias", e))
    import traceback; traceback.print_exc()
    print("3 Ganancias: FAIL", e)

# ── 4) Inventario ────────────────────────────────────────────────────
try:
    inv = svc.inventario_estado()
    invd = svc.inventario_detallado(100)
    filas = []
    for ii in invd:
        filas.append([ii["nombre"], ii["categoria"], ii["existencia"],
                       ii["unidad"], float(ii["costo"]), float(ii["precio_venta"]),
                       float(ii["valor_inv"]), ii["stock_minimo"], ii["estado"]])
    datos = base("Inventario", "inventario", [
        ("Valor costo", inv["valor_costo"], "moneda"),
        ("Valor venta", inv["valor_venta"], "moneda"),
        ("Sin stock", inv["sin_stock"], "numero"),
        ("Stock bajo", inv["bajo"], "numero"),
    ], {
        "encabezados": ["Prod", "Cat", "Exist", "Unid", "Costo", "PVenta", "Valor", "SMin", "Estado"],
        "filas": filas,
        "columnas_moneda": [4, 5, 6], "columnas_cantidad": [2, 7], "columnas_enteros": [],
    })
    exportar_reporte_excel(tempfile.gettempdir() + "/rep_inv.xlsx", datos)
    exportar_reporte_pdf(tempfile.gettempdir() + "/rep_inv.pdf", datos)
    print("4 Inventario: OK")
except Exception as e:
    errors.append(("Inventario", e))
    import traceback; traceback.print_exc()
    print("4 Inventario: FAIL", e)

# ── 5) Compras ───────────────────────────────────────────────────────
try:
    cr = svc.compras_resumen(ini, fin)
    cd = svc.compras_periodo(ini, fin, None, 200)
    filas = []
    for cc in cd:
        filas.append([cc["folio"], str(cc["fecha"]), cc["proveedor"],
                       cc["productos"], float(cc["total"])])
    datos = base("Compras", "compras", [
        ("Total", cr["total"], "moneda"),
        ("Ordenes", cr["ordenes"], "numero"),
        ("Proveedor", cr["proveedor_top"], "texto"),
        ("Unidades", sum((cc["productos"] for cc in cd), Decimal("0")), "cantidad"),
    ], {
        "encabezados": ["Folio", "Fecha", "Proveedor", "Prod", "Total"],
        "filas": filas,
        "columnas_moneda": [4], "columnas_cantidad": [3], "columnas_enteros": [],
    })
    exportar_reporte_excel(tempfile.gettempdir() + "/rep_compras.xlsx", datos)
    exportar_reporte_pdf(tempfile.gettempdir() + "/rep_compras.pdf", datos)
    print("5 Compras: OK")
except Exception as e:
    errors.append(("Compras", e))
    import traceback; traceback.print_exc()
    print("5 Compras: FAIL", e)

# ── 6) Fiado ─────────────────────────────────────────────────────────
try:
    fr = svc.clientes_resumen()
    fd = svc.clientes_fiados()
    filas = []
    for ff in fd:
        filas.append([ff["cliente"], ff["telefono"],
                       float(ff["total_fiado"]), float(ff["total_abonado"]),
                       float(ff["pendiente"])])
    datos = base("Fiado", "fiado", [
        ("Pendiente", fr["total_pendiente"], "moneda"),
        ("Fiado total", fr["total_fiado"], "moneda"),
        ("Abonado", fr["total_abonado"], "moneda"),
        ("Deudores", fr["deudores"], "numero"),
    ], {
        "encabezados": ["Cliente", "Tel", "Fiado", "Abonado", "Pendiente"],
        "filas": filas,
        "columnas_moneda": [2, 3, 4], "columnas_cantidad": [], "columnas_enteros": [],
    })
    exportar_reporte_excel(tempfile.gettempdir() + "/rep_fiado.xlsx", datos)
    exportar_reporte_pdf(tempfile.gettempdir() + "/rep_fiado.pdf", datos)
    print("6 Fiado: OK")
except Exception as e:
    errors.append(("Fiado", e))
    import traceback; traceback.print_exc()
    print("6 Fiado: FAIL", e)

# ── 7) Caja ──────────────────────────────────────────────────────────
try:
    cr = svc.cortes_resumen(ini, fin)
    cd = svc.cortes_caja_periodo(ini, fin, 200)
    filas = []
    for cc in cd:
        estado = "Cerrado" if cc["cerrado"] else "Abierto"
        filas.append([cc["id"], str(cc["fecha_apertura"]),
                       str(cc["fecha_cierre"] or "-"),
                       float(cc["monto_inicial"]), float(cc["esperado"]),
                       float(cc["contado"]), float(cc["diferencia"]),
                       float(cc["total_ventas"]), estado])
    datos = base("Caja", "caja", [
        ("Cortes", cr["cortes"], "numero"),
        ("Efectivo contado", cr["efectivo_contado"], "moneda"),
        ("Diferencia", cr["diferencia_total"], "moneda"),
        ("Ventas cortes", cr["ventas"], "moneda"),
    ], {
        "encabezados": ["ID", "Apertura", "Cierre", "Inicial", "Esperado", "Contado", "Dif", "Ventas", "Estado"],
        "filas": filas,
        "columnas_moneda": [3, 4, 5, 6, 7], "columnas_cantidad": [], "columnas_enteros": [0],
    })
    exportar_reporte_excel(tempfile.gettempdir() + "/rep_caja.xlsx", datos)
    exportar_reporte_pdf(tempfile.gettempdir() + "/rep_caja.pdf", datos)
    print("7 Caja: OK")
except Exception as e:
    errors.append(("Caja", e))
    import traceback; traceback.print_exc()
    print("7 Caja: FAIL", e)

# ── 8) Movimientos ───────────────────────────────────────────────────
try:
    mr = svc.movimientos_resumen(ini, fin)
    md = svc.movimientos_periodo(ini, fin, None, 300)
    filas = []
    for mm in md:
        filas.append([str(mm["fecha"]), mm["producto"],
                       mm["tipo"].capitalize(), float(mm["cantidad"]),
                       mm["usuario"], mm["referencia"]])
    datos = base("Movimientos", "movimientos", [
        ("Total", mr["total"], "numero"),
        ("Entradas", mr["entradas"], "numero"),
        ("Salidas", mr["salidas"], "numero"),
        ("Ajustes+Dev", mr["ajustes"] + mr["devoluciones"], "numero"),
    ], {
        "encabezados": ["Fecha", "Producto", "Tipo", "Cant", "Usuario", "Ref"],
        "filas": filas,
        "columnas_moneda": [], "columnas_cantidad": [3], "columnas_enteros": [],
    })
    exportar_reporte_excel(tempfile.gettempdir() + "/rep_mov.xlsx", datos)
    exportar_reporte_pdf(tempfile.gettempdir() + "/rep_mov.pdf", datos)
    print("8 Movimientos: OK")
except Exception as e:
    errors.append(("Movimientos", e))
    import traceback; traceback.print_exc()
    print("8 Movimientos: FAIL", e)

# ── Resumen ──────────────────────────────────────────────────────────
print()
if errors:
    print(f"FALLARON {len(errors)} reportes:")
    for nombre, e in errors:
        print(f"  - {nombre}: {type(e).__name__}: {e}")
    sys.exit(1)
else:
    print("TODOS LOS REPORTES EXPORTARON OK")
    for nombre in ["ventas", "prod", "gan", "inv", "compras", "fiado", "caja", "mov"]:
        for ext in ["xlsx", "pdf"]:
            p = os.path.join(tempfile.gettempdir(), f"rep_{nombre}.{ext}")
            sz = os.path.getsize(p) if os.path.exists(p) else 0
            print(f"  {p}: {sz} bytes")
