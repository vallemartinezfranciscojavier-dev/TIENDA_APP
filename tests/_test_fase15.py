"""
Prueba headless de la FASE 15 (AUDITORÍA Y RESPALDOS).

Cubre lo que pide el documento guía y las decisiones aprobadas:

  A) CONFIGURACIÓN PERSISTENTE (data/configuracion_respaldos.json):
     valores por defecto (programado INACTIVO, retención INACTIVA),
     guardar/leer, valores inválidos sanados, archivo corrupto tolerado.
  B) RESPALDO PROGRAMADO: se distingue con backup_programado_*, no duplica
     dentro de la ventana del intervalo.
  C) POLÍTICA DE RETENCIÓN: INACTIVA no borra nada; ACTIVA conserva los N más
     recientes y elimina los más viejos; NUNCA toca backup_pre_restauracion_*.
  D) AUDITORÍA: quedan en bitácora crear/editar/cambio_precio/act-var/
     desactivar producto, ajuste de inventario, compras, abonos y cortes.
  E) FILTROS DE BITÁCORA: por acción, por usuario y por rango de fechas.

Usa una base de datos TEMPORAL (no toca data/tienda.db).
"""

import os
import sqlite3
import sys
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Consolas Windows (cp1252) no entienden '✔'/'✘': forzar UTF-8 en la salida.
if sys.stdout and getattr(sys.stdout, "buffer", None) is not None:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 0. Redirigir a BD temporal ANTES de importar los servicios ─────────
_tmp = Path(tempfile.mkdtemp(prefix="f15_"))
from config import settings  # noqa: E402

settings.DATABASE_DIR = _tmp
settings.DATABASE_PATH = _tmp / "test.db"
settings.DATABASE_URL = f"sqlite:///{settings.DATABASE_PATH}"
settings.BACKUPS_DIR = _tmp / "backups"
settings.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

from database.connection import get_db  # noqa: E402
from database.models import (  # noqa: E402
    Usuario,
    Categoria,
    Producto,
    Inventario,
    Proveedor,
    Cliente,
    Credito,
    RolUsuarioEnum,
)
from services.db_init_service import inicializar_base_datos  # noqa: E402
from services.usuarios_service import UsuarioService  # noqa: E402
from services.bitacora_service import BitacoraService  # noqa: E402
from services.productos_service import ProductosService  # noqa: E402
from services.inventario_service import InventarioService  # noqa: E402
from services.compras_service import ComprasService  # noqa: E402
from services.creditos_service import CreditosService  # noqa: E402
from services.cortes_caja_service import CortesCajaService  # noqa: E402
from services.ventas_service import VentasService  # noqa: E402
from services import respaldos_service  # noqa: E402
from services import respaldos_config_service  # noqa: E402
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


def este_script():
    return os.path.abspath(__file__)


def crear_producto_directo(db, codigo, nombre, precio, stock):
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


def crear_archivo_respaldo(nombre_base: str, anio: int, con_prefijo_pre=False):
    """Crear un archivo .db de respaldo válido con una fecha de modificación dada."""
    nombre = (
        f"backup_pre_restauracion_{anio}_01_01_00_00.db"
        if con_prefijo_pre
        else f"backup_{nombre_base}_{anio}_01_01_00_00.db"
    )
    ruta = settings.BACKUPS_DIR / nombre
    conn = sqlite3.connect(str(ruta))
    conn.close()
    ts = datetime(anio, 1, 1).timestamp()
    os.utime(ruta, (ts, ts))
    return ruta


def acciones_bitacora():
    return [r.accion for r in BitacoraService().obtener_recientes(limite=1000)]


# ── 1. Inicializar BD temporal ─────────────────────────────────────────
init = inicializar_base_datos()
check("inicializar_base_datos: exito", init["exito"], str(init))
usuarios_service = UsuarioService()
admin = usuarios_service.obtener_por_id(1) or (
    usuarios_service.listar() and usuarios_service.listar()[0]
)
check("admin sembrado", admin is not None and admin.rol == RolUsuarioEnum.ADMIN)

set_sesion(RolUsuarioEnum.ADMIN, admin.id)

# ── 2. A) CONFIGURACIÓN DE RESPALDOS (persistente) ─────────────────────
cfg = respaldos_config_service.leer_config()
check("config por defecto: programado INACTIVO", cfg["programado"]["activo"] is False)
check("config por defecto: intervalo 24h", cfg["programado"]["intervalo_horas"] == 24)
check("config por defecto: retención INACTIVA", cfg["retencion"]["activa"] is False)
check("config por defecto: máximo 30", cfg["retencion"]["maximo_respaldos"] == 30)

res = respaldos_config_service.guardar_programado(True, 6)
check("guardar_programado: exito", res.get("exito"), str(res))
cfg = respaldos_config_service.leer_config()
check("programado guardado y persistido", cfg["programado"]["activo"] is True
      and cfg["programado"]["intervalo_horas"] == 6)

res = respaldos_config_service.guardar_retencion(True, 5)
cfg = respaldos_config_service.leer_config()
check("retención guardada y persistida", cfg["retencion"]["activa"] is True
      and cfg["retencion"]["maximo_respaldos"] == 5)

# Valores inválidos se sanan (no rompen la app).
cfg = respaldos_config_service.guardar_config({
    "programado": {"intervalo_horas": 0},
    "retencion": {"maximo_respaldos": -3},
})["config"]
check("valores inválidos sanados", cfg["programado"]["intervalo_horas"] == 24
      and cfg["retencion"]["maximo_respaldos"] == 30)

# Archivo corrupto: se tolera y devuelve por defecto.
ruta_cfg = settings.DATABASE_DIR / "configuracion_respaldos.json"
ruta_cfg.write_text("{ esto no es json !!!!", encoding="utf-8")
cfg = respaldos_config_service.leer_config()
check("config corrupta tolerada", cfg["programado"]["activo"] is False
      and cfg["retencion"]["activa"] is False, str(cfg))

# Restablecer estado limpio (inactivo) para las siguientes secciones.
respaldos_config_service.guardar_programado(False, 24)
respaldos_config_service.guardar_retencion(False, 30)
cfg = respaldos_config_service.leer_config()
check("reseteo a inactivo", cfg["programado"]["activo"] is False
      and cfg["retencion"]["activa"] is False)

# ── 3. B) RESPALDO PROGRAMADO ──────────────────────────────────────────
# Intervalo de ventana = 1 para no deduplicar entre archivos de años distintos.
p1 = ProductosService().crear({
    "nombre": "Chile Ancho",
    "categoria_id": 1,
    "precio_venta": Decimal("90"),
    "precio_compra": Decimal("60"),
    "stock_inicial": Decimal("10"),
})

r_p1 = respaldos_service.crear_respaldo_programado(intervalo_horas=48)
check("respaldo programado: creado", r_p1.get("exito"), str(r_p1))
prog_files = list(settings.BACKUPS_DIR.glob("backup_programado_*.db"))
check("respaldo programado: nombre backup_programado_*", len(prog_files) == 1,
      str([f.name for f in prog_files]))

r_p2 = respaldos_service.crear_respaldo_programado(intervalo_horas=48)
prog_files = list(settings.BACKUPS_DIR.glob("backup_programado_*.db"))
check("respaldo programado: NO duplica en la ventana",
      r_p2.get("ya_existia") is True and len(prog_files) == 1, str(r_p2))

# Vista de ventana: un programado con marca antigua (vencida la ventana)
# permite crear otro, en vez de deduplicar.
for f in list(settings.BACKUPS_DIR.glob("backup_programado_*.db")):
    f.unlink(missing_ok=True)
antiguo = settings.BACKUPS_DIR / "backup_programado_2020_01_01_00_00.db"
conn = sqlite3.connect(str(antiguo))
conn.close()
os.utime(antiguo, (datetime(2020, 1, 1).timestamp(),) * 2)
r_p3 = respaldos_service.crear_respaldo_programado(intervalo_horas=1)
prog_files = list(settings.BACKUPS_DIR.glob("backup_programado_*.db"))
check("respaldo programado: vencida la ventana crea otro",
      r_p3.get("exito") and len(prog_files) == 2
      and antiguo.name in [f.name for f in prog_files],
      str([f.name for f in prog_files]))

# ── 4. C) POLÍTICA DE RETENCIÓN ────────────────────────────────────────
# Base limpia y controlada para que los conteos sean deterministas.
for f in settings.BACKUPS_DIR.glob("*.db"):
    f.unlink(missing_ok=True)

# Inactiva: no borra nada (aunque haya varios respaldos).
crear_archivo_respaldo("N1", 2021)
crear_archivo_respaldo("N2", 2022)
r = respaldos_service.aplicar_politica_retencion()
restantes = len(list(settings.BACKUPS_DIR.glob("*.db")))
check("retención INACTIVA: no aplica ni borra",
      r.get("aplicada") is False and r.get("eliminados") == [] and restantes == 2,
      str(r))

# Limpiar y sembrar 4 normales + 1 preventivo muy viejo.
for f in settings.BACKUPS_DIR.glob("*.db"):
    f.unlink(missing_ok=True)
for anio in (2024, 2023, 2022, 2021):
    crear_archivo_respaldo("N", anio)
pre = crear_archivo_respaldo("", 1999, con_prefijo_pre=True)

respaldos_config_service.guardar_retencion(True, 3)
r = respaldos_service.aplicar_politica_retencion()
restantes = sorted(f.name for f in settings.BACKUPS_DIR.glob("*.db"))
check("retención ACTIVA: sí aplica", r.get("aplicada") is True)
check("retención: elimina solo excedentes (N_2021)",
      r.get("eliminados") == ["backup_N_2021_01_01_00_00.db"],
      str(r.get("eliminados")))
check("retención: conserva 3 más recientes + preventivo",
      len(restantes) == 4 and pre.name in restantes, str(restantes))

# Retención estricta (límite 1): sigue preservando TODOS los preventivos.
pre_actual = crear_archivo_respaldo("", 1998, con_prefijo_pre=True)
respaldos_config_service.guardar_retencion(True, 1)
r = respaldos_service.aplicar_politica_retencion()
restantes = sorted(f.name for f in settings.BACKUPS_DIR.glob("*.db"))
check("retención estricta: conserva 1 normal",
      len([f for f in restantes if not f.startswith("backup_pre_restauracion_")]) == 1,
      str(restantes))
check("retención estricta: preserva TODOS los preventivos",
      pre.name in restantes and pre_actual.name in restantes, str(restantes))
respaldos_config_service.guardar_retencion(False, 30)

# ── 5. D) AUDITORÍA DE OPERACIONES CRÍTICAS ────────────────────────────
p2 = ProductosService().crear({
    "nombre": "Chile Pasilla",
    "categoria_id": 1,
    "precio_venta": Decimal("85"),
    "precio_compra": Decimal("55"),
    "stock_inicial": Decimal("5"),
})

acciones = acciones_bitacora()
check("auditoría: crear_producto en bitácora", "crear_producto" in acciones,
      str(sorted(set(acciones))))

# Cambio de precio registrado aparte de la edición.
ProductosService().actualizar(
    p2.id,
    {"nombre": "Chile Pasilla", "precio_venta": Decimal("95"),
     "precio_compra": Decimal("55"), "stock_minimo": Decimal("0"),
     "categoria_id": 1},
    nuevo_stock=None,
)
acciones = acciones_bitacora()
check("auditoría: cambio_precio en bitácora", "cambio_precio" in acciones,
      str(sorted(set(acciones))))

# Ajuste manual de inventario.
r_ajuste = InventarioService().ajustar_stock(
    p2.id, Decimal("12"), notas="merma", usuario_id=admin.id
)
acciones = acciones_bitacora()
check("auditoría: ajuste_inventario en bitácora",
      r_ajuste.get("modificado") and "ajuste_inventario" in acciones, str(r_ajuste))

# Compra registrada (audita compra_registrada) y aumenta inventario.
prov = Proveedor(nombre="Proveedor Central")
db = next(get_db())
db.add(prov)
db.flush()
prov_id = prov.id
db.commit()
db.close()

r_compra = ComprasService().crear_compra(
    items=[{"producto_id": p2.id, "cantidad": Decimal("10"), "precio": Decimal("50")}],
    proveedor_id=prov_id,
    usuario_id=admin.id,
)
acciones = acciones_bitacora()
check("auditoría: compra_registrada en bitácora",
      "compra_registrada" in acciones, str(sorted(set(acciones))))

# Abono (fiado) auditado.
cliente = Cliente(nombre="Cliente Fiado", limite_credito=Decimal("5000"), activo=True)
db = next(get_db())
db.add(cliente)
db.flush()
cliente_id = cliente.id
db.commit()
db.close()
v_fiado = VentasService().crear_venta(
    items=[{"producto_id": p2.id, "cantidad": Decimal("2")}],
    metodo_pago="fiado",
    cliente_id=cliente_id,
    usuario_id=admin.id,
)
db = next(get_db())
credito = db.query(Credito).filter(Credito.cliente_id == cliente_id).first()
total_fiado = Decimal(str(v_fiado.total))
db.close()
r_abono = CreditosService().registrar_abono(
    cliente_id, credito.id, total_fiado, usuario_id=admin.id
)
acciones = acciones_bitacora()
check("auditoría: abono en bitácora", "abono" in acciones, str(r_abono))

# Corte de caja auditado (apertura y cierre).
corte = CortesCajaService().abrir_corte(monto_inicial=100, usuario_id=admin.id)
cerrado = CortesCajaService().cerrar_corte(100, observaciones="prueba")
acciones = acciones_bitacora()
check("auditoría: corte_abierto en bitácora", "corte_abierto" in acciones)
check("auditoría: corte_cerrado en bitácora", "corte_cerrado" in acciones)

# Activar / desactivar producto auditado.
ProductosService().desactivar(p2.id)
ProductosService().activar(p2.id)
acciones = acciones_bitacora()
check("auditoría: desactivar_producto en bitácora", "desactivar_producto" in acciones)
check("auditoría: activar_producto en bitácora", "activar_producto" in acciones)

# Respaldos auditados (respaldo manual + programado ya registran su acción).
respaldos_service.crear_respaldo_manual()
acciones = acciones_bitacora()
check("auditoría: respaldo en bitácora", "respaldo" in acciones,
      str(sorted(set(acciones))))

# ── 6. E) FILTROS DE BITÁCORA ──────────────────────────────────────────
bit = BitacoraService()

fil_cambio = bit.obtener_recientes(limite=500, accion="cambio_precio")
check("filtro por acción: cambio_precio",
      len(fil_cambio) >= 1 and all("cambio_precio" in (r.accion or "") for r in fil_cambio),
      str([r.accion for r in fil_cambio][:5]))

fil_usuario = bit.obtener_recientes(limite=500, texto_usuario=admin.nombre[:4])
check("filtro por usuario: devuelve resultados",
      len(fil_usuario) >= 1, str(len(fil_usuario)))

# Rango de fechas: hoy debe incluir lo registrado; mañana no.
hoy = date.today()
manana = hoy + timedelta(days=1)
fil_hoy = bit.obtener_recientes(limite=500, fecha_inicio=hoy, fecha_fin=hoy)
fil_manana = bit.obtener_recientes(limite=500, fecha_inicio=manana, fecha_fin=manana)
check("filtro por fechas: hoy tiene actividad", len(fil_hoy) >= 1, str(len(fil_hoy)))
check("filtro por fechas: mañana no tiene actividad", len(fil_manana) == 0,
      str(len(fil_manana)))

# ── Resumen ────────────────────────────────────────────────────────────
sesion.cerrar_sesion()
print()
print("=" * 60)
if fallos:
    print(f"FASE 15: {ok_count} OK, {len(fallos)} FALLOS:")
    for f in fallos:
        print("  -", f)
    sys.exit(1)
else:
    print(f"FASE 15: TODAS LAS PRUEBAS PASARON ({ok_count} checks OK)")
    print("BD temporal:", settings.DATABASE_PATH)
    sys.exit(0)