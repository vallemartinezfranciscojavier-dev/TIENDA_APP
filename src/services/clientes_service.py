"""
Servicio de clientes.
Administración completa de clientes: crear, editar, buscar, desactivar
y consultar su saldo. El saldo pendiente se mantiene a través de los
créditos (ver CreditosService); aquí solo se lee.
"""

from decimal import Decimal

from sqlalchemy import or_

from database.connection import get_db
from database.models import Cliente
from utils.calculations import redondear_moneda
from services.seguridad_service import requiere_permiso
from utils.validators import validar_telefono, validar_email


class ClientesService:
    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def obtener_todos(self, incluir_inactivos: bool = False):
        db = next(get_db())
        try:
            q = db.query(Cliente)
            if not incluir_inactivos:
                q = q.filter(Cliente.activo == True)
            return q.order_by(Cliente.nombre.asc()).all()
        finally:
            db.close()

    def obtener_por_id(self, cliente_id: int):
        db = next(get_db())
        try:
            return db.query(Cliente).filter(Cliente.id == cliente_id).first()
        finally:
            db.close()

    def buscar(self, termino: str = "", incluir_inactivos: bool = False):
        """Buscar clientes por nombre, teléfono o email."""
        db = next(get_db())
        try:
            q = db.query(Cliente)
            if not incluir_inactivos:
                q = q.filter(Cliente.activo == True)
            termino = (termino or "").strip()
            if termino:
                patron = f"%{termino}%"
                q = q.filter(or_(
                    Cliente.nombre.ilike(patron),
                    Cliente.telefono.ilike(patron),
                    Cliente.email.ilike(patron),
                ))
            return q.order_by(Cliente.nombre.asc()).all()
        finally:
            db.close()

    def obtener_activos_para_selector(self):
        """Clientes activos para combos/selectores (venta, fiado)."""
        return self.obtener_todos()

    # ------------------------------------------------------------------
    # Crear / editar
    # ------------------------------------------------------------------

    def _validar(self, datos: dict):
        nombre = (datos.get("nombre") or "").strip()
        if not nombre:
            raise ValueError("El nombre del cliente es obligatorio.")

        telefono = (datos.get("telefono") or "").strip()
        if not validar_telefono(telefono):
            raise ValueError("El teléfono no tiene un formato válido.")

        email = (datos.get("email") or "").strip()
        if not validar_email(email):
            raise ValueError("El email no tiene un formato válido.")

        try:
            limite = Decimal(str(datos.get("limite_credito") or 0))
        except Exception:
            raise ValueError("El límite de crédito no es válido.")
        if limite < 0:
            raise ValueError("El límite de crédito no puede ser negativo.")

        return {
            "nombre": nombre,
            "telefono": telefono or None,
            "email": email or None,
            "direccion": (datos.get("direccion") or "").strip() or None,
            "limite_credito": redondear_moneda(limite),
        }

    @requiere_permiso("administrar_clientes")
    def crear(self, datos: dict) -> Cliente:
        db = next(get_db())
        try:
            limpios = self._validar(datos)
            cliente = Cliente(
                **limpios,
                saldo_actual=Decimal("0"),
                activo=True,
            )
            db.add(cliente)
            db.commit()
            db.refresh(cliente)
            return cliente
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo crear el cliente: {e}")
        finally:
            db.close()

    @requiere_permiso("administrar_clientes")
    def editar(self, cliente_id: int, datos: dict) -> Cliente:
        db = next(get_db())
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if not cliente:
                raise ValueError("El cliente no existe.")

            limpios = self._validar(datos)
            for campo, valor in limpios.items():
                setattr(cliente, campo, valor)

            db.commit()
            db.refresh(cliente)
            return cliente
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo actualizar el cliente: {e}")
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Estado (activo/inactivo)
    # ------------------------------------------------------------------

    @requiere_permiso("administrar_clientes")
    def cambiar_estado(self, cliente_id: int, activo: bool) -> Cliente:
        """Activar o desactivar un cliente (no se borra físicamente)."""
        db = next(get_db())
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if not cliente:
                raise ValueError("El cliente no existe.")
            cliente.activo = bool(activo)
            db.commit()
            db.refresh(cliente)
            return cliente
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo cambiar el estado del cliente: {e}")
        finally:
            db.close()
