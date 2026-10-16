"""
Servicio de proveedores.
Gestiona el CRUD de proveedores para el módulo de compras.
"""

from sqlalchemy import func

from database.connection import get_db
from database.models import Proveedor


class ProveedoresService:
    def __init__(self):
        pass

    def _validar_nombre(self, db, nombre: str, exclude_id: int = None):
        """Validar que el nombre no esté vacío ni duplicado."""
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre del proveedor es obligatorio.")
        duplicado = db.query(Proveedor).filter(
            func.lower(Proveedor.nombre) == nombre.lower()
        ).first()
        if duplicado and duplicado.id != exclude_id:
            raise ValueError("Ya existe un proveedor con ese nombre.")

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def obtener_activos(self):
        """Obtener proveedores activos (para seleccionar en compras)."""
        db = next(get_db())
        try:
            return db.query(Proveedor).filter(
                Proveedor.activo == True
            ).order_by(Proveedor.nombre).all()
        finally:
            db.close()

    def obtener_todos(self, incluir_inactivos: bool = True):
        """Obtener todos los proveedores."""
        db = next(get_db())
        try:
            q = db.query(Proveedor)
            if not incluir_inactivos:
                q = q.filter(Proveedor.activo == True)
            return q.order_by(Proveedor.nombre).all()
        finally:
            db.close()

    def obtener_por_id(self, proveedor_id: int):
        db = next(get_db())
        try:
            return db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Crear / Actualizar / Estado
    # ------------------------------------------------------------------

    def crear(self, datos: dict) -> Proveedor:
        """Crear un proveedor nuevo."""
        nombre = (datos.get("nombre") or "").strip()
        if not nombre:
            raise ValueError("El nombre del proveedor es obligatorio.")

        db = next(get_db())
        try:
            self._validar_nombre(db, nombre)
            proveedor = Proveedor(
                nombre=nombre,
                contacto=(datos.get("contacto") or "").strip() or None,
                telefono=(datos.get("telefono") or "").strip() or None,
                email=(datos.get("email") or "").strip() or None,
                direccion=(datos.get("direccion") or "").strip() or None,
                rfc=(datos.get("rfc") or "").strip() or None,
                activo=True,
            )
            db.add(proveedor)
            db.commit()
            db.refresh(proveedor)
            return proveedor
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo crear el proveedor: {e}")
        finally:
            db.close()

    def actualizar(self, proveedor_id: int, datos: dict) -> Proveedor:
        """Actualizar un proveedor existente."""
        db = next(get_db())
        try:
            proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
            if not proveedor:
                raise ValueError("El proveedor no existe.")

            nombre = (datos.get("nombre") or "").strip()
            self._validar_nombre(db, nombre, exclude_id=proveedor_id)

            proveedor.nombre = nombre
            proveedor.contacto = (datos.get("contacto") or "").strip() or None
            proveedor.telefono = (datos.get("telefono") or "").strip() or None
            proveedor.email = (datos.get("email") or "").strip() or None
            proveedor.direccion = (datos.get("direccion") or "").strip() or None
            proveedor.rfc = (datos.get("rfc") or "").strip() or None
            if "activo" in datos:
                proveedor.activo = bool(datos.get("activo"))
            db.commit()
            db.refresh(proveedor)
            return proveedor
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo actualizar el proveedor: {e}")
        finally:
            db.close()

    def desactivar(self, proveedor_id: int):
        """Desactivar un proveedor (no se elimina de la BD)."""
        db = next(get_db())
        try:
            proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
            if not proveedor:
                raise ValueError("El proveedor no existe.")
            proveedor.activo = False
            db.commit()
            db.refresh(proveedor)
            return proveedor
        finally:
            db.close()

    def activar(self, proveedor_id: int):
        """Activar un proveedor."""
        db = next(get_db())
        try:
            proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
            if not proveedor:
                raise ValueError("El proveedor no existe.")
            proveedor.activo = True
            db.commit()
            db.refresh(proveedor)
            return proveedor
        finally:
            db.close()