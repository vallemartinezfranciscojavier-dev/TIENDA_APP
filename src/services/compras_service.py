"""
Servicio de compras.
Registra compras con sus detalles, aumenta el inventario y registra los
movimientos de inventario (entrada por compra), todo en una transacción.
"""

from decimal import Decimal

from sqlalchemy import func

from database.connection import get_db
from database.models import (
    Compra,
    DetalleCompra,
    Producto,
    Inventario,
    MovimientoInventario,
    Usuario,
    TipoMovimientoEnum,
)
from utils.calculations import redondear_moneda
from services.bitacora_service import BitacoraService
from services.seguridad_service import requiere_permiso
from utils.formatters import formatear_folio


class ComprasService:
    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def obtener_todas(self):
        db = next(get_db())
        try:
            return db.query(Compra).order_by(Compra.fecha.desc()).all()
        finally:
            db.close()

    def obtener_por_id(self, compra_id: int):
        db = next(get_db())
        try:
            return db.query(Compra).filter(Compra.id == compra_id).first()
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def _generar_folio(self, db) -> str:
        """Generar un folio único de compra del tipo CMP-000001."""
        total = db.query(func.count(Compra.id)).scalar() or 0
        for i in range(total + 1, total + 10000):
            folio = formatear_folio("CMP", i)
            existe = db.query(Compra).filter(Compra.folio == folio).first()
            if not existe:
                return folio
        raise ValueError("No se pudo generar un folio disponible.")

    def _obtener_usuario_id(self, db):
        """Id del usuario con sesión activa (Fase 14: bloquear sin sesión)."""
        from services.sesion_service import obtener_usuario_id

        usuario_id = obtener_usuario_id()
        if not usuario_id:
            raise ValueError("Debe iniciar sesión para registrar una compra.")
        return usuario_id

    # ------------------------------------------------------------------
    # Crear compra (transacción completa)
    # ------------------------------------------------------------------

    @requiere_permiso("registrar_compras")
    def crear_compra(
        self,
        items: list,
        proveedor_id: int,
        usuario_id: int = None,
        notas: str = None,
    ):
        """
        Registrar una compra completa dentro de una transacción.

        1. Crea la compra (con folio único).
        2. Crea los detalles de compra.
        3. Aumenta el inventario de cada producto.
        4. Registra los movimientos de inventario (tipo ENTRADA).
        5. Actualiza el precio de compra más reciente del producto.

        Si ocurre cualquier error, se revierte TODO (rollback).

        Args:
            items: Lista de dicts con ``producto_id``, ``cantidad`` y ``precio``.
            proveedor_id: Id del proveedor de la compra.
            usuario_id: Id del usuario (None = admin por defecto).
            notas: Notas opcionales sobre la compra.

        Returns:
            Compra creada y confirmada.

        Raises:
            ValueError: Si no hay productos, no hay proveedor, o algún dato es inválido.
        """
        db = next(get_db())
        try:
            if not items:
                raise ValueError("La compra no tiene productos.")

            if not proveedor_id:
                raise ValueError("Selecciona un proveedor.")

            if not usuario_id:
                usuario_id = self._obtener_usuario_id(db)

            folio = self._generar_folio(db)

            compra = Compra(
                folio=folio,
                proveedor_id=int(proveedor_id),
                subtotal=Decimal("0"),
                impuestos=Decimal("0"),
                total=Decimal("0"),
                pagado=True,
                notas=notas,
            )
            db.add(compra)
            db.flush()  # Asigna compra.id

            subtotal = Decimal("0")

            for item in items:
                producto_id = item["producto_id"]
                try:
                    cantidad = Decimal(str(item.get("cantidad", 0)))
                    precio = Decimal(str(item.get("precio", 0)))
                except Exception:
                    raise ValueError("Los valores de cantidad y precio no son válidos.")

                if cantidad <= 0:
                    raise ValueError(
                        "Las cantidades de la compra deben ser mayores a cero."
                    )
                if precio < 0:
                    raise ValueError("El precio de compra no puede ser negativo.")

                producto = db.query(Producto).filter(Producto.id == producto_id).first()
                if not producto:
                    raise ValueError("Un producto del detalle no existe.")

                inventario = (
                    db.query(Inventario)
                    .filter(Inventario.producto_id == producto_id)
                    .first()
                )
                if not inventario:
                    inventario = Inventario(producto_id=producto_id, cantidad=Decimal("0"))
                    db.add(inventario)
                    db.flush()

                stock_anterior = Decimal(str(inventario.cantidad))
                stock_nuevo = stock_anterior + cantidad
                linea_subtotal = redondear_moneda(cantidad * precio)

                # Detalle de compra
                db.add(DetalleCompra(
                    compra_id=compra.id,
                    producto_id=producto_id,
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=linea_subtotal,
                ))

                # Aumentar inventario
                inventario.cantidad = stock_nuevo

                # Actualizar el último precio de compra conocido
                if precio > 0:
                    producto.precio_compra = precio

                # Movimiento de inventario (entrada por compra)
                db.add(MovimientoInventario(
                    producto_id=producto_id,
                    tipo=TipoMovimientoEnum.ENTRADA,
                    cantidad=cantidad,
                    cantidad_anterior=stock_anterior,
                    cantidad_nueva=stock_nuevo,
                    usuario_id=usuario_id,
                    referencia_id=compra.id,
                    referencia_tipo="compra",
                    notas=f"Compra folio {folio}",
                ))

                subtotal += linea_subtotal

            subtotal = redondear_moneda(subtotal)
            compra.subtotal = subtotal
            compra.total = subtotal

            db.commit()
            db.refresh(compra)
            # Auditoría (Fase 15)
            BitacoraService().registrar(
                usuario_id=usuario_id,
                accion="compra_registrada",
                detalle=f"Compra {folio} registrada (total {subtotal})",
            )
            return compra
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo registrar la compra: {e}")
        finally:
            db.close()