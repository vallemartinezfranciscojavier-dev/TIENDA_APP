"""
Prueba headless de VALIDACIÓN de la Fase 14 (USUARIOS, ROLES Y SEGURIDAD).

Cubre lo que pide el documento guía y que NO probaba ``_test_fase14.py``:

  A) LOGIN: correcto, incorrecto, usuario desactivado.
  B) BITÁCORA: login y logout quedan registrados (inicio/cierre de sesión).
  C) ADMINISTRACIÓN DE USUARIOS: crear (con rol), editar rol/nombre,
     cambio de contraseña con re-autenticación, activar/desactivar,
     protección del último administrador activo, y bloqueo sin sesión.
  D) ENFORCEMENT: cada permiso del catálogo se aplica en la lógica, no solo
     ocultando botones (compras, clientes, cortes, inventario, fiados,
     reportes, respaldos, usuarios, ventas).
  E) modificar_precios: permiso fino aplicado al cambiar un precio.
  F) configurar_sistema: reservado (solo ADMIN lo tiene) — no se inventa módulo.

Usa una base de datos TEMPORAL (no toca data/tienda.db).
"""

import sys
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# ── 0. Redirigir a BD temporal ANTES de importar los servicios ─────────
_tmp = Path(tempfile.mkdtemp(prefix="f14v_"))
from config import settings  # noqa: E402

settings.DATABASE_DIR = _tmp
settings.DATABASE_PATH = _tmp / "test.db"
settings.DATABASE_URL = f"sqlite:///{settings.DATABASE_PATH}"
settings.BACKUPS_DIR = _tmp / "backups"

from database.connection import get_db, SessionLocal  # noqa: E402
from database.models import (  # noqa: E402
    Usuario,
    Categoria,
    Producto,
    Inventario,
    Cliente,
    Credito,
    RolUsuarioEnum,
)
from services.db_init_service import inicializar_base_datos  # noqa: E402
from services.usuarios_service import UsuarioService  # noqa: E402
from services.ventas_service import VentasService  # noqa: E402
from services.compras_service import ComprasService  # noqa: E402
from services.clientes_service import ClientesService  # noqa: E402
from services.cortes_caja_service import CortesCajaService  # noqa: E402
from services.inventario_service import InventarioService  # noqa: E402
from services.creditos_service import CreditosService  # noqa: E402
from services.reportes_service import ReportesService  # noqa: E402
from services.productos_service import ProductosService  # noqa: E402
from services.bitacora_service import BitacoraService  # noqa: E402
from services import respaldos_service  # noqa: E402
from services.permisos_service import (  # noqa: E402
    ACCIONES,
    PERMISOS_ACCION,
    tiene_permiso,
)
from services.seguridad_service import PermisoDenegado  # noqa: E402
from services import permisos_service as _perm  # noqa: E402
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


def espera_denegado(nombre, fn, extra=""):
    """Ejecuta fn() y comprueba que lanza PermisoDenegado."""
    try:
        fn()
        check(nombre, False, "(no lanzó)")
    except PermisoDenegado:
        check(nombre, True)
    except Exception as e:
        check(nombre, False, f"({type(e).__name__}: {e})")


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
usuarios_service = UsuarioService()
admin = usuarios_service.obtener_por_id(1) or (
    usuarios_service.listar() and usuarios_service.listar()[0]
)
check("admin sembrado", admin is not None and admin.rol == RolUsuarioEnum.ADMIN)

db = next(get_db())
p1 = crear_producto(db, "V001", "Tortilla", Decimal("18"), Decimal("100"))
cliente = Cliente(nombre="Cliente Prueba", limite_credito=Decimal("5000"), activo=True)
db.add(cliente)
db.flush()
p1_id = p1.id
cliente_id = cliente.id
db.commit()
db.close()

# ── 2. A) LOGIN ────────────────────────────────────────────────────────
sesion.cerrar_sesion()
u = usuarios_service.autenticar("admin", "admin123")
check("login CORRECTO (admin/admin123)", u is not None and u.rol == RolUsuarioEnum.ADMIN)
check("login INCORRECTO → None", usuarios_service.autenticar("admin", "mala") is None)
check("login usuario inexistente → None", usuarios_service.autenticar("ghost", "x") is None)

# Crear empleado y desactivarlo para probar bloqueo por usuario inactivo.
set_sesion(RolUsuarioEnum.ADMIN, admin.id)
emp = usuarios_service.crear_usuario("Empleado Uno", "empleado1", "Emp-1!abc", rol=RolUsuarioEnum.VENDEDOR)
check("login empleado ANTES de desactivar", usuarios_service.autenticar("empleado1", "Emp-1!abc") is not None)
usuarios_service.alternar_activo(emp.id)
check("login DESACTIVADO → None", usuarios_service.autenticar("empleado1", "Emp-1!abc") is None)
usuarios_service.alternar_activo(emp.id)  # reactivar para conservarlo

# ── 3. B) BITÁCORA: sesión inicio/cierre ───────────────────────────────
bit = BitacoraService()
bit.registrar_login(usuario_id=admin.id, usuario_nombre=admin.nombre)
bit.registrar_logout(usuario_id=admin.id, usuario_nombre=admin.nombre)
recientes = bit.obtener_recientes(limite=500)
acciones_bit = [r.accion for r in recientes]
check("bitácora registra login", "login" in acciones_bit, str(acciones_bit))
check("bitácora registra logout", "logout" in acciones_bit, str(acciones_bit))

# ── 4. C) ADMINISTRACIÓN DE USUARIOS ───────────────────────────────────
# Sin sesión: todo el CRUD queda bloqueado (enforcement de administrar_usuarios).
sesion.cerrar_sesion()
espera_denegado("crear_usuario SIN sesión BLOQUEADO",
                lambda: usuarios_service.crear_usuario("A", "a1", "Pass-1!ab"))
espera_denegado("actualizar_usuario SIN sesión BLOQUEADO",
                lambda: usuarios_service.actualizar_usuario(emp.id, nombre="B"))
espera_denegado("cambiar_password SIN sesión BLOQUEADO",
                lambda: usuarios_service.cambiar_password(emp.id, "New-1!ab"))
espera_denegado("alternar_activo SIN sesión BLOQUEADO",
                lambda: usuarios_service.alternar_activo(emp.id))

# Con ADMIN sí funciona y asigna rol.
set_sesion(RolUsuarioEnum.ADMIN, admin.id)
cajero = usuarios_service.crear_usuario("Cajero Uno", "cajero1", "Cajero-1!ab", rol=RolUsuarioEnum.CAJERO)
check("crear_usuario asigna rol CAJERO", cajero.rol == RolUsuarioEnum.CAJERO)

edit = usuarios_service.actualizar_usuario(cajero.id, nombre="Cajero Renombrado", rol=RolUsuarioEnum.ALMACEN)
check("editar usuario cambia rol a ALMACEN", edit.rol == RolUsuarioEnum.ALMACEN)

nueva_pass = "Nueva-1!cd"
usuarios_service.cambiar_password(cajero.id, nueva_pass)
check("cambiar_password y re-autenticación con la nueva",
      usuarios_service.autenticar("cajero1", nueva_pass) is not None)
check("password vieja ya NO funciona",
      usuarios_service.autenticar("cajero1", "Cajero-1!ab") is None)

# Proteger al último administrador activo.
administradores_activos = [
    us for us in usuarios_service.listar()
    if us.rol == RolUsuarioEnum.ADMIN and us.activo
]
if len(administradores_activos) == 1:
    try:
        usuarios_service.alternar_activo(admin.id)
        check("último admin activo protegido", False, "(no lanzó)")
    except ValueError:
        check("último admin activo protegido", True)
else:
    check("último admin activo protegido", False, "(hay varios admins activos)")

# ── 5. D) ENFORCEMENT por servicio ─────────────────────────────────────
vs = VentasService()
set_sesion(RolUsuarioEnum.ADMIN, admin.id)

# 5.1 registrar_compras (ComprasService)
set_sesion(RolUsuarioEnum.VENDEDOR, emp.id)
espera_denegado("VENDEDOR: registrar compras BLOQUEADO",
                lambda: ComprasService().crear_compra(items=[], proveedor_id=1, usuario_id=emp.id))
set_sesion(RolUsuarioEnum.CAJERO, cajero.id)
espera_denegado("CAJERO: registrar compras BLOQUEADO",
                lambda: ComprasService().crear_compra(items=[], proveedor_id=1, usuario_id=cajero.id))

# 5.2 administrar_clientes (ClienteService)
set_sesion(RolUsuarioEnum.VENDEDOR, emp.id)
espera_denegado("VENDEDOR: crear cliente BLOQUEADO",
                lambda: ClientesService().crear({"nombre": "X"}))
espera_denegado("VENDEDOR: cambiar estado cliente BLOQUEADO",
                lambda: ClientesService().cambiar_estado(cliente_id, False))
set_sesion(RolUsuarioEnum.ADMIN, admin.id)
nuevo_cliente = ClientesService().crear({"nombre": "Cliente Nuevo", "telefono": "555-0100"})
check("ADMIN: crear cliente permitido", nuevo_cliente is not None and nuevo_cliente.id > 0)

# 5.3 realizar_cortes (CorteCajaService)
set_sesion(RolUsuarioEnum.VENDEDOR, emp.id)
espera_denegado("VENDEDOR: abrir corte BLOQUEADO",
                lambda: CortesCajaService().abrir_corte(monto_inicial=0, usuario_id=emp.id))
set_sesion(RolUsuarioEnum.CAJERO, cajero.id)
corte = CortesCajaService().abrir_corte(monto_inicial=100, usuario_id=cajero.id)
check("CAJERO: abrir corte permitido", corte is not None and corte.id > 0)

# 5.4 ajustar_inventario (InventarioService)
set_sesion(RolUsuarioEnum.VENDEDOR, emp.id)
espera_denegado("VENDEDOR: ajustar stock BLOQUEADO",
                lambda: InventarioService().ajustar_stock(p1_id, Decimal("80"), notas="x", usuario_id=emp.id))
set_sesion(RolUsuarioEnum.ALMACEN, cajero.id)
ajustado = InventarioService().ajustar_stock(p1_id, Decimal("80"), notas="merma", usuario_id=cajero.id)
db = next(get_db())
check("ALMACEN: ajustar stock permitido y aplicado",
      ajustado is not None and cantidad_inventario(db, p1_id) == Decimal("80"),
      str(cantidad_inventario(db, p1_id)))
db.close()

# 5.5 administrar_fiados (CreditosService.registrar_abono)
set_sesion(RolUsuarioEnum.ADMIN, admin.id)
v3 = vs.crear_venta(items=[{"producto_id": p1_id, "cantidad": 2}],
                    metodo_pago="fiado", cliente_id=cliente_id, usuario_id=admin.id)
db = next(get_db())
total_fiado = Decimal(str(v3.total))
credito = db.query(Credito).filter(Credito.cliente_id == cliente_id).first()
db.close()
check("venta fiada crea crédito", credito is not None and total_fiado > 0)
set_sesion(RolUsuarioEnum.VENDEDOR, emp.id)
espera_denegado("VENDEDOR: registrar abono BLOQUEADO",
                lambda: CreditosService().registrar_abono(cliente_id, credito.id, Decimal("10"), usuario_id=emp.id))
set_sesion(RolUsuarioEnum.ADMIN, admin.id)
res_abono = CreditosService().registrar_abono(cliente_id, credito.id, total_fiado, usuario_id=admin.id)
check("ADMIN: abono permitido (saldó fiado)", res_abono is not None)

# 5.6 consultar_reportes (ReportesService, todas las consultas públicas)
fin = datetime.now()
ini = fin - timedelta(days=90)
set_sesion(RolUsuarioEnum.VENDEDOR, emp.id)
espera_denegado("VENDEDOR: consultar reportes BLOQUEADO",
                lambda: ReportesService().ventas_periodo(ini, fin, 500))
set_sesion(None)
espera_denegado("reportes SIN sesión BLOQUEADO",
                lambda: ReportesService().ventas_periodo(ini, fin, 500))
set_sesion(RolUsuarioEnum.ADMIN, admin.id)
try:
    filas = ReportesService().ventas_periodo(ini, fin, 500)
    check("ADMIN: consultar reportes permitido", isinstance(filas, list))
except Exception as e:
    check("ADMIN: consultar reportes permitido", False, f"({type(e).__name__})")

# 5.7 restaurar_respaldos (respaldos_service.crear_flag_restauracion)
set_sesion(RolUsuarioEnum.VENDEDOR, emp.id)
espera_denegado("VENDEDOR: programar restauración BLOQUEADO",
                lambda: respaldos_service.crear_flag_restauracion("fake.db"))
set_sesion(RolUsuarioEnum.ADMIN, admin.id)
try:
    resultado = respaldos_service.crear_flag_restauracion("no_existe.db")
    # Llega a la lógica: valida que exista (no salta por permiso).
    check("ADMIN: resta por LÓGICA (no por permiso)", resultado.get("exito") is False)
except PermisoDenegado:
    check("ADMIN: resta por LÓGICA (no por permiso)", False, "(lanzó permiso)")

# 5.8 realizar_ventas / cancelar_ventas ya cubiertos por _test_fase14.py
#     (se deja constancia y se re-verifica un bloqueo de ALMACEN).
set_sesion(RolUsuarioEnum.ALMACEN, cajero.id)
espera_denegado("ALMACEN: vender BLOQUEADO",
                lambda: vs.crear_venta(items=[{"producto_id": p1_id, "cantidad": 1}],
                                       metodo_pago="efectivo", usuario_id=cajero.id))

# ── 6. E) modificar_precios (permiso fino) ─────────────────────────────
set_sesion(RolUsuarioEnum.ADMIN, admin.id)
# Rol "artificial" con modificar_productos pero SIN modificar_precios:
# demuestra que el chequeo fino funciona (default deny) si mañana se crea
# un rol de ese tipo.
_original = _perm.PERMISOS_ACCION[RolUsuarioEnum.ADMIN]
_perm.PERMISOS_ACCION[RolUsuarioEnum.ADMIN] = {"modificar_productos"}
try:
    espera_denegado(
        "modificar_precios: cambiar precio exige el permiso fino",
        lambda: ProductosService().actualizar(
            p1_id, {"nombre": "Tortilla", "precio_venta": Decimal("20"),
                    "precio_compra": Decimal("0.01"), "stock_minimo": Decimal("0"),
                    "categoria_id": 1}
        ),
    )
finally:
    _perm.PERMISOS_ACCION[RolUsuarioEnum.ADMIN] = _original

# ALMACEN (tiene modificar_precios) sí puede cambiar el precio.
set_sesion(RolUsuarioEnum.ALMACEN, cajero.id)
act = ProductosService().actualizar(
    p1_id, {"nombre": "Tortilla", "precio_venta": Decimal("21"),
            "precio_compra": Decimal("0.01"), "stock_minimo": Decimal("0"),
            "categoria_id": 1}
)
check("ALMACEN: cambiar precio permitido", act is not None and Decimal(str(act.precio_venta)) == Decimal("21"),
      str(act.precio_venta))

# VENDEDOR (sin modificar_productos) no puede editar ni siquiera el nombre.
set_sesion(RolUsuarioEnum.VENDEDOR, emp.id)
espera_denegado("VENDEDOR: editar producto BLOQUEADO",
                lambda: ProductosService().actualizar(
                    p1_id, {"nombre": "Otra", "precio_venta": Decimal("21"),
                            "precio_compra": Decimal("0.01"), "stock_minimo": Decimal("0"),
                            "categoria_id": 1}
                ))

# ── 7. F) configurar_sistema: reservado ────────────────────────────────
check("configurar_sistema: en el catálogo", "configurar_sistema" in ACCIONES)
check("configurar_sistema: ADMIN lo tiene",
      tiene_permiso(RolUsuarioEnum.ADMIN, "configurar_sistema"))
check("configurar_sistema: VENDEDOR NO",
      not tiene_permiso(RolUsuarioEnum.VENDEDOR, "configurar_sistema"))

# ── Resumen ────────────────────────────────────────────────────────────
sesion.cerrar_sesion()
print()
print("=" * 60)
if fallos:
    print(f"FASE 14 VALIDACIÓN: {ok_count} OK, {len(fallos)} FALLOS:")
    for f in fallos:
        print("  -", f)
    sys.exit(1)
else:
    print(f"FASE 14 VALIDACIÓN: TODAS LAS PRUEBAS PASARON ({ok_count} checks OK)")
    print("BD temporal:", settings.DATABASE_PATH)
    sys.exit(0)