# -*- coding: utf-8 -*-
"""Verificación final Fase 12: flujo de respaldos + imports de todas las vistas."""
import sqlite3, tempfile
from pathlib import Path
from decimal import Decimal
from datetime import datetime

TMP = Path(tempfile.mkdtemp(prefix="f12_final_"))
TMPDB, BACKUPS = TMP / "tienda.db", TMP / "backups"

from config import settings
settings.DATABASE_PATH = TMPDB
settings.DATABASE_DIR = TMP
settings.BACKUPS_DIR = BACKUPS

from services import respaldos_service as rs
rs.FLAG_PATH = TMP / "restaurar.flag"

errores = []

try:
    # --- 1) BD temp con modelos REALES ---
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database.connection import Base
    from database.models import (Usuario, Categoria, Producto, Inventario,
                                 Cliente, Venta, RolUsuarioEnum, TipoVentaEnum,
                                 MetodoPagoEnum, EstadoVentaEnum)
    e = create_engine(f"sqlite:///{TMPDB}")
    Base.metadata.create_all(e)
    S = sessionmaker(bind=e)
    db = S()
    u = Usuario(nombre="Admin", usuario="admin", password_hash="x", rol=RolUsuarioEnum.ADMIN, activo=True)
    db.add(u); db.commit()
    c = Categoria(nombre="Chiles", activa=True); db.add(c); db.commit()
    p = Producto(codigo="P1", nombre="Chile Guajillo", categoria_id=c.id,
                 tipo_venta=TipoVentaEnum.KILOGRAMO, precio_venta=Decimal("120"),
                 precio_compra=Decimal("90"), activo=True)
    db.add(p); db.flush()
    db.add(Inventario(producto_id=p.id, cantidad=Decimal("12.750")))
    db.add(Cliente(nombre="Doña Lupe", limite_credito=Decimal("500")))
    db.add(Venta(folio="V-1", usuario_id=u.id, total=Decimal("30"),
                 metodo_pago=MetodoPagoEnum.EFECTIVO, estado=EstadoVentaEnum.COMPLETADA,
                 fecha=datetime(2026, 9, 13, 12, 0)))
    db.commit(); db.close()

    # --- 2) acciones de la Fase 12 ---
    r = rs.crear_respaldo_manual()
    assert r["exito"], r
    assert rs.verificar_integridad(r["ruta"])["exito"]
    d1 = rs.crear_respaldo_diario()
    d2 = rs.crear_respaldo_diario()
    assert d1["exito"] and d2.get("ya_existia")
    assert len(rs.listar_respaldos()) >= 2

    # corromper
    conn = sqlite3.connect(TMPDB)
    conn.execute("INSERT INTO productos (codigo, nombre, categoria_id, tipo_venta, precio_venta, activo) "
                 "VALUES ('B','BASURA',1,'pieza',999,1)")
    conn.commit(); conn.close()

    # flag + aplicar
    assert rs.crear_flag_restauracion(d1["archivo"])["exito"]
    assert rs.hay_restauracion_pendiente()
    res = rs.aplicar_restauracion_pendiente()
    assert res["exito"], res
    assert not rs.hay_restauracion_pendiente()
    conn = sqlite3.connect(TMPDB)
    nombres = [x[0] for x in conn.execute("SELECT nombre FROM productos")]
    n_ventas = conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]
    conn.close()
    assert "BASURA" not in nombres and "Chile Guajillo" in nombres and n_ventas == 1
    print("P1: flujo respaldo/restauración con modelos reales  ✔")

    # --- 3) Import de todas las vistas + main ---
    import main  # noqa: F401
    import views.dashboard, views.productos, views.punto_venta, views.compras   # noqa: F401
    import views.inventario, views.clientes, views.corte_caja                   # noqa: F401
    import views.proveedores, views.reportes, views.configuracion               # noqa: F401
    import views.login                                                          # noqa: F401
    print("P2: imports de todas las vistas y main                           ✔")

except Exception as ex:
    import traceback
    errores.append((ex, traceback.format_exc()))

if errores:
    print("\nERRORES ENCONTRADOS:")
    for ex, tb in errores:
        print(tb)
    print("RESULTADO: FALLÓ ❌")
    raise SystemExit(1)
print("\nVERIFICACION_FINAL: SIN ERRORES ✔✔")