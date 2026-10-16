"""
Servicio de inicialización de base de datos con datos semilla.
"""

from database.connection import engine, Base, SessionLocal
from database.models import (
    Usuario,
    Categoria,
    Producto,
    Inventario,
    Proveedor,
    RolUsuarioEnum,
)
from utils.security import hash_password, generar_password_aleatorio
from config.settings import DATABASE_PATH
from sqlalchemy import inspect, text


CATEGORIAS_INICIALES = [
    {"nombre": "Chiles secos", "descripcion": "Chiles secos variados (guajillo, ancho, pasilla, chipotle, etc.)"},
    {"nombre": "Abarrotes", "descripcion": "Productos de abarrotes básicos (arroz, frijol, azúcar, sal, aceite, etc.)"},
    {"nombre": "Bebidas", "descripcion": "Refrescos, jugos, agua, bebidas alcohólicas"},
    {"nombre": "Dulces", "descripcion": "Dulces tradicionales, chocolates, golosinas"},
    {"nombre": "Semillas", "descripcion": "Semillas, nueces, frutos secos"},
    {"nombre": "Otros", "descripcion": "Productos varios no categorizados"},
]

PROVEEDORES_INICIALES = [
    {"nombre": "Distribuidora La Viga", "contacto": "Atención a clientes", "telefono": "5555550101"},
    {"nombre": "Abarrotes El Buen Precio", "contacto": "Gerencia", "telefono": "5555550102"},
    {"nombre": "Chiles San Juan", "contacto": "Ventas", "telefono": "5555550103"},
]


def tablas_existen() -> bool:
    """Verificar si las tablas ya existen en la BD."""
    inspector = inspect(engine)
    tablas_requeridas = [
        'usuarios', 'categorias', 'productos', 'inventario',
        'ventas', 'detalle_ventas', 'clientes', 'creditos', 'abonos',
        'proveedores', 'compras', 'detalle_compras',
        'movimientos_inventario', 'cortes_caja'
    ]
    tablas_existentes = inspector.get_table_names()
    return all(tabla in tablas_existentes for tabla in tablas_requeridas)


def _aplicar_migraciones() -> list:
    """Aplicar migraciones ligeras a bases de datos existentes (ALTER TABLE)."""
    mensajes = []
    inspector = inspect(engine)
    try:
        columnas = [c['name'] for c in inspector.get_columns('movimientos_inventario')]
        if 'usuario_id' not in columnas:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE movimientos_inventario "
                         "ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id)")
                )
            mensajes.append("Columna 'usuario_id' agregada a movimientos_inventario")
    except Exception as e:
        mensajes.append(f"Migraciones: {e}")
    return mensajes


def inicializar_base_datos() -> dict:
    """
    Inicializar la base de datos completa:
    1. Crear tablas si no existen
    2. Poblar datos semilla (categorías, usuario admin)

    Returns:
        dict con resultado de la operación
    """
    resultado = {
        "exito": True,
        "tablas_creadas": False,
        "categorias_creadas": 0,
        "usuario_admin_creado": False,
        "mensajes": []
    }

    try:
        # 1. Crear tablas si no existen
        if not tablas_existen():
            Base.metadata.create_all(bind=engine)
            resultado["tablas_creadas"] = True
            resultado["mensajes"].append("Tablas creadas correctamente")
        else:
            resultado["mensajes"].append("Tablas ya existían, omitiendo creación")

        # 1a. Crear tablas que falten en BD existentes (módulos nuevos).
        # create_all solo crea las tablas inexistentes, así que es seguro
        # ejecutarlo aunque la base ya tenga datos.
        Base.metadata.create_all(bind=engine)

        # 1b. Migraciones para BD existentes (agregar columnas nuevas, etc.)
        resultado["mensajes"].extend(_aplicar_migraciones())

        # 2. Poblar datos semilla
        db = SessionLocal()
        try:
            # Categorías iniciales
            for cat_data in CATEGORIAS_INICIALES:
                existe = db.query(Categoria).filter(Categoria.nombre == cat_data["nombre"]).first()
                if not existe:
                    categoria = Categoria(**cat_data, activa=True)
                    db.add(categoria)
                    resultado["categorias_creadas"] += 1

            # Proveedores iniciales
            for prov_data in PROVEEDORES_INICIALES:
                existe = db.query(Proveedor).filter(Proveedor.nombre == prov_data["nombre"]).first()
                if not existe:
                    db.add(Proveedor(**prov_data, activo=True))

            # Usuario administrador por defecto
            admin_existe = db.query(Usuario).filter(Usuario.usuario == "admin").first()
            if not admin_existe:
                password_default = "admin123"  # En producción esto debería cambiarse
                admin = Usuario(
                    nombre="Administrador del Sistema",
                    usuario="admin",
                    password_hash=hash_password(password_default),
                    rol=RolUsuarioEnum.ADMIN,
                    activo=True
                )
                db.add(admin)
                resultado["usuario_admin_creado"] = True
                resultado["mensajes"].append(
                    f"Usuario 'admin' creado con contraseña: {password_default} "
                    "(CAMBIAR EN PRODUCCIÓN)"
                )

            db.commit()
            resultado["mensajes"].append("Datos semilla insertados correctamente")

        except Exception as e:
            db.rollback()
            resultado["exito"] = False
            resultado["mensajes"].append(f"Error insertando datos semilla: {str(e)}")
            raise
        finally:
            db.close()

    except Exception as e:
        resultado["exito"] = False
        resultado["mensajes"].append(f"Error inicializando BD: {str(e)}")

    return resultado


def resetear_base_datos() -> dict:
    """
    Eliminar y recrear toda la base de datos (solo para desarrollo/testing).
    ¡CUIDADO! Esto borra TODOS los datos.
    """
    resultado = {
        "exito": True,
        "mensajes": []
    }

    try:
        # Eliminar todas las tablas
        Base.metadata.drop_all(bind=engine)
        resultado["mensajes"].append("Todas las tablas eliminadas")

        # Recrear
        Base.metadata.create_all(bind=engine)
        resultado["mensajes"].append("Tablas recreadas")

        # Poblar datos semilla
        init_result = inicializar_base_datos()
        resultado["mensajes"].extend(init_result["mensajes"])

    except Exception as e:
        resultado["exito"] = False
        resultado["mensajes"].append(f"Error reseteando BD: {str(e)}")

    return resultado


def verificar_integridad_bd() -> dict:
    """
    Verificar integridad básica de la base de datos.
    """
    resultado = {
        "exito": True,
        "tablas_ok": True,
        "categorias_count": 0,
        "usuarios_count": 0,
        "productos_count": 0,
        "mensajes": []
    }

    try:
        db = SessionLocal()
        try:
            resultado["categorias_count"] = db.query(Categoria).count()
            resultado["usuarios_count"] = db.query(Usuario).count()
            resultado["productos_count"] = db.query(Producto).count()

            if resultado["categorias_count"] == 0:
                resultado["mensajes"].append("ADVERTENCIA: No hay categorías registradas")
            if resultado["usuarios_count"] == 0:
                resultado["mensajes"].append("ADVERTENCIA: No hay usuarios registrados")

            resultado["mensajes"].append("Verificación de integridad completada")

        finally:
            db.close()

    except Exception as e:
        resultado["exito"] = False
        resultado["mensajes"].append(f"Error verificando integridad: {str(e)}")

    return resultado