"""
Prueba headless integral de la Fase 14 (USUARIOS, ROLES Y SEGURIDAD).

Cubre:
  A) Matriz de permisos por rol sobre las 13 acciones.
  B) Bloqueo de operaciones SIN sesión y SIN permiso (PermisoDenegado).
  C) cancelar_venta en EFECTIVO: repone stock, mueve DEVOLUCION,
     excluye de reportes, sin doble cancelación.
  D) cancelar_venta en FIADO: perdona el crédito y recalcula el saldo.
  E) buscar_por_folio.
  F) Visibilidad del botón "Cancelar Venta" en el PDV por rol (offscreen).

Usa una base de datos TEMPORAL para no tocar data/tienda.db.
"""

import sys
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# ── 0. Redirigir a BD temporal ANTES de importar los servicios ─────────
_tmp = Path(tempfile.mkdtemp(prefix="f14_"))
from config import settings  # noqa: E402

settings.DATABASE_DIR = _tmp
settings.DATABASE_PATH = _tmp / "test.db"
settings.DATABASE_URL = f"sqlite:///{settings.DATABASE_PATH}"
settings.BACKUPS_DIR = _tmp / "backups"

# Ahora sí se pueden importar los módulos que dependen de connection/engine
from database.connection import get_db, SessionLocal  # noqa: E402
from database.models import (  # noqa: E402
    Usuario,
    Categoria,
    Producto,
    Inventario,
    Cliente,
    RegistroActividad,
    MovimientoInventario,
    RolUsuarioEnum,
    EstadoVentaEnum,
    TipoMovimientoEnum,
)
from services.db_init_service import inicializar_base_datos  # noqa: E402
from services.ventas_service import VentasService  # noqa: E402
from services.creditos_service import CreditosService  # noqa: E402
from services.reportes_service import ReportesService  # noqa: E402
from services.permisos_service import (  # noqa: E402
    ACCIONES,
    PERMISOS_ACCION,
    tiene_permiso,
    hay_permiso_actual,
)
from services.seguridad_service import PermisoDenegado, requiere_permiso  # noqa: E402
import services.sesion_service as sesion  # noqa: E402

# ── Herramientas de la prueba ──────────────────────────────────────────
fallos = []
ok_count = 0


def check(nombre, cond, extra=""):
    global ok_count
    if cond:
        ok_count += 1
        print(f"  ✔ {nombre}")
    else:
        fallos.append(nombre)
        print(f"  ✘ {nombre} {extra}")


def set_sesion(rol, user_id=1):
    sesion._usuario_actual = {
        "id": user_id,
        "nombre": "Test",
        "usuario": "test",
        "rol": rol,
    }


def crear_producto(db, codigo, nombre, precio, stock):
    cat = db.query(Categoria).first()
    p = Producto(
        codigo=codigo,
        nombre=nombre,
        categoria_id=cat.id,
        precio_venta=precio,
        precio_compra=Decimal("0.01"),
        activo=True,
    )
    db.add(p)
    db.flush()
    db.add(Inventario(producto_id=p.id, cantidad=stock))
    db.flush()
    return p


def cantidad_inventario(db, producto_id):
    inv = db.query(Inventario).filter(Inventario.producto_id == producto_id).first()
    return Decimal(str(inv.cantidad)) if inv else Decimal("0")


# ── 1. Inicializar BD temporal ─────────────────────────────────────────
init = inicializar_base_datos()
check("inicializar_base_datos: exito", init["exito"], str(init))
check("admin sembrado", init.get("usuario_admin_creado") or
      SessionLocal().query(Usuario).filter(Usuario.usuario == "admin").first() is not None)

db = next(get_db())
p1 = crear_producto(db, "P001", "Arroz", Decimal("20"), Decimal("50"))
p2 = crear_producto(db, "P002", "Frijol", Decimal("30"), Decimal("40"))
cliente = Cliente(nombre="Cliente Prueba", limite_credito=Decimal("5000"), activo=True)
db.add(cliente)
db.flush()
p1_id = p1.id
p2_id = p2.id
cliente_id = cliente.id
db.commit()
db.close()
check("productos y cliente sembrados", True)

# ── 2. A) Matriz de permisos ───────────────────────────────────────────
check("ACCIONES: 13 permisos", len(ACCIONES) == 13, f"len={len(ACCIONES)}")
check("ADMIN tiene todo", all(tiene_permiso(RolUsuarioEnum.ADMIN, a) for a in ACCIONES))
check("VENDEDOR solo vender",
      setup_ok := (
          tiene_permiso(RolUsuarioEnum.VENDEDOR, "realizar_ventas")
          and not any(tiene_permiso(RolUsuarioEnum.VENDEDOR, a)
                      for a in ACCIONES if a != "realizar_ventas")
      ))
check("CAJERO: vender + cortes",
      tiene_permiso(RolUsuarioEnum.CAJERO, "realizar_ventas")
      and tiene_permiso(RolUsuarioEnum.CAJERO, "realizar_cortes")
      and not tiene_permiso(RolUsuarioEnum.CAJERO, "administrar_usuarios"))
check("ALMACEN sin vender",
      not tiene_permiso(RolUsuarioEnum.ALMACEN, "realizar_ventas")
      and tiene_permiso(RolUsuarioEnum.ALMACEN, "ajustar_inventario"))

# ── 3. B) Bloqueos sin sesión / sin permiso ────────────────────────────
sesion.cerrar_sesion()
vs = VentasService()
try:
    vs.crear_venta(items=[{"producto_id": p1_id, "cantidad": 1}],
                   metodo_pago="efectivo", usuario_id=1)
    check("crear_venta SIN sesión BLOQUEADO", False, "(no lanzó)")
except PermisoDenegado as e:
    check("crear_venta SIN sesión BLOQUEADO", True)
except Exception as e:
    check("crear_venta SIN sesión BLOQUEADO", False, f"({type(e).__name__})")

# VENDEDOR: puede vender
set_sesion(RolUsuarioEnum.VENDEDOR, 1)
v1 = vs.crear_venta(items=[{"producto_id": p1_id, "cantidad": 3}],
                    metodo_pago="efectivo", usuario_id=1)
check("VENDEDOR crea venta", v1 is not None and v1.estado == EstadoVentaEnum.COMPLETADA)
db = next(get_db())
check("stock tras venta (50-3=47)", cantidad_inventario(db, p1_id) == Decimal("47"),
      str(cantidad_inventario(db, p1_id)))
db.close()

# ALMACEN: NO puede vender
set_sesion(RolUsuarioEnum.ALMACEN, 2)
try:
    vs.crear_venta(items=[{"producto_id": p1_id, "cantidad": 1}],
                   metodo_pago="efectivo", usuario_id=2)
    check("ALMACEN SIN permiso de venta BLOQUEADO", False, "(no lanzó)")
except PermisoDenegado:
    check("ALMACEN SIN permiso de venta BLOQUEADO", True)
except Exception as e:
    check("ALMACEN SIN permiso de venta BLOQUEADO", False, f"({type(e).__name__})")

# VENDEDOR: NO puede cancelar
try:
    vs.cancelar_venta(v1.id, motivo="test")
    check("VENDEDOR SIN permiso de cancelación BLOQUEADO", False, "(no lanzó)")
except PermisoDenegado:
    check("VENDEDOR SIN permiso de cancelación BLOQUEADO", True)
except Exception as e:
    check("VENDEDOR SIN permiso de cancelación BLOQUEADO", False, f"({type(e).__name__})")

# ── 4. C) Cancelar venta en EFECTIVO (ADMIN) ───────────────────────────
set_sesion(RolUsuarioEnum.ADMIN, 3)
db = next(get_db())
stock_frijol_antes = cantidad_inventario(db, p2_id)  # 40
db.close()
v2 = vs.crear_venta(items=[{"producto_id": p2_id, "cantidad": 10}],
                    metodo_pago="efectivo", usuario_id=3)
cancelada = vs.cancelar_venta(v2.id, motivo="error de caja")
check("cancelar_venta devuelve venta", cancelada is not None)
check("estado → CANCELADA", cancelada.estado == EstadoVentaEnum.CANCELADA)

db = next(get_db())
# stock restaurado
stock_frijol_despues = cantidad_inventario(db, p2_id)
check("stock repuesto (40 otra vez)", stock_frijol_despues == stock_frijol_antes,
      f"{stock_frijol_despues} vs {stock_frijol_antes}")

# movimiento DEVOLUCION registrado
movs = (db.query(MovimientoInventario)
        .filter(MovimientoInventario.referencia_id == v2.id)
        .all())
check("movimientos DEVOLUCION registrados",
      any(m.tipo == TipoMovimientoEnum.DEVOLUCION and m.referencia_tipo == "cancelacion"
          and m.cantidad > 0
          for m in movs),
      str([(m.tipo.value, m.referencia_tipo, str(m.cantidad)) for m in movs]))

# bitácora de cancelación
bit = db.query(RegistroActividad).filter(
    RegistroActividad.accion == "cancelacion_venta"
).first()
check("bitácora registra cancelacion_venta", bit is not None,
      "(" + (bit.detalle or "") + ")")
db.close()

# doble cancelación → ValueError
try:
    vs.cancelar_venta(v2.id, motivo="otra vez")
    check("doble cancelación rechazada", False, "(no lanzó)")
except ValueError:
    check("doble cancelación rechazada", True)

# excluida de reportes
fin = datetime.now()
ini = fin - timedelta(days=90)
filas_ventas = ReportesService().ventas_periodo(ini, fin, 500)
folios_reporte = [f["folio"] for f in filas_ventas]
check("venta CANCELADA excluida de reportes",
      v2.folio not in folios_reporte, f"folios={folios_reporte}")

# ── 5. D) Cancelar venta FIADO: perdona crédito y saldo ────────────────
v3 = vs.crear_venta(items=[{"producto_id": p1_id, "cantidad": 2}],
                    metodo_pago="fiado", cliente_id=cliente_id, usuario_id=3)
total_fiado = Decimal(str(v3.total))
db = next(get_db())
cred = CreditosService()._saldo_en_sesion(db, cliente_id)
check("crédito creado (saldo = total)", cred == total_fiado, f"{cred} vs {total_fiado}")
cliente_db = db.query(Cliente).filter(Cliente.id == cliente_id).first()
check("cliente.saldo_actual = total", Decimal(str(cliente_db.saldo_actual)) == total_fiado,
      str(cliente_db.saldo_actual))
db.close()

vs.cancelar_venta(v3.id, motivo="cliente devolvió")
db = next(get_db())
cliente_db = db.query(Cliente).filter(Cliente.id == cliente_id).first()
saldo = Decimal(str(cliente_db.saldo_actual))
check("fiado perdonado: saldo cliente = 0", saldo == 0, str(saldo))
db.close()

# ── 6. E) buscar_por_folio ─────────────────────────────────────────────
check("buscar_por_folio existe", vs.buscar_por_folio(v1.folio) is not None)
check("buscar_por_folio normaliza a mayúsculas", vs.buscar_por_folio("vta-000001") is not None)
check("buscar_por_folio vacío → None", vs.buscar_por_folio("") is None)

# ── 7. F) Botón en PDV por rol (offscreen) ─────────────────────────────
from PySide6.QtWidgets import QApplication  # noqa: E402
app = QApplication.instance() or QApplication([])

set_sesion(None)  # sin sesión
from views.punto_venta.punto_venta_view import PuntoVentaView  # noqa: E402
v_none = PuntoVentaView()
check("PDV: botón oculto sin sesión", v_none.btn_cancelar_venta.isHidden())
set_sesion(RolUsuarioEnum.ADMIN, 3)
v_admin = PuntoVentaView()
check("PDV: botón visible ADMIN", not v_admin.btn_cancelar_venta.isHidden())
set_sesion(RolUsuarioEnum.VENDEDOR, 1)
v_ven = PuntoVentaView()
check("PDV: botón oculto VENDEDOR", v_ven.btn_cancelar_venta.isHidden())
sesion.cerrar_sesion()

# ── Resumen ────────────────────────────────────────────────────────────
print()
print("=" * 60)
if fallos:
    print(f"FASE 14: {ok_count} OK, {len(fallos)} FALLOS:")
    for f in fallos:
        print("  -", f)
    sys.exit(1)
else:
    print(f"FASE 14: TODAS LAS PRUEBAS PASARON ({ok_count} checks OK)")
    print("BD temporal:", settings.DATABASE_PATH)
    sys.exit(0)