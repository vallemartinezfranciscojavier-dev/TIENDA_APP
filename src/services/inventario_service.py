"""
Servicio de inventario.
Gestiona el stock de productos, consultas con filtros, historial de
movimientos y ajustes manuales.
"""

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import joinedload
from services.bitacora_service import BitacoraService
from services.seguridad_service import requiere_permiso
from services.sesion_service import obtener_usuario_id

from database.connection import get_db
from database.models import (
    Inventario,
    MovimientoInventario,
    Producto,
    Usuario,
    TipoMovimientoEnum,
)


class InventarioService:
    def __init__(self):
        pass

    def obtener_usuario_admin(self):
        """Id del usuario admin por defecto (para registrar movimientos)."""
        db = next(get_db())
        try:
            u = db.query(Usuario).filter(Usuario.usuario == "admin").first()
            return u.id if u else None
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Consultas de catálogo
    # ------------------------------------------------------------------

    def obtener_catalogo(self, estado: str = "todos", categoria_id=None, termino: str = ""):
        """
        Obtener el catálogo de productos con su inventario para la vista.

        Args:
            estado: "todos", "bajo" (cantidad > 0 y <= stock_minimo),
                    o "sin_stock" (cantidad == 0).
            categoria_id: Filtro por categoría (None = todas).
            termino: Texto de búsqueda por nombre o código.
        """
        db = next(get_db())
        try:
            q = db.query(Producto).join(Inventario).options(
                joinedload(Producto.categoria),
                joinedload(Producto.inventario),
            )

            if categoria_id:
                q = q.filter(Producto.categoria_id == categoria_id)

            if estado == "bajo":
                q = q.filter(
                    Inventario.cantidad > 0,
                    Inventario.cantidad <= func.coalesce(Producto.stock_minimo, 0),
                )
            elif estado == "sin_stock":
                q = q.filter(Inventario.cantidad == 0)

            termino = (termino or "").strip()
            if termino:
                patron = f"%{termino}%"
                q = q.filter(
                    func.lower(Producto.nombre).like(patron.lower())
                    | func.lower(Producto.codigo).like(patron.lower())
                )

            return q.order_by(Producto.nombre).all()
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Historial de movimientos
    # ------------------------------------------------------------------

    def obtener_movimientos(self, termino: str = "", limite: int = 200):
        """
        Obtener el historial de movimientos de inventario (los más recientes primero).

        Args:
            termino: Filtro opcional por nombre de producto.
            limite: Máximo de registros a traer para no cargar datos innecesarios.
        """
        db = next(get_db())
        try:
            q = db.query(MovimientoInventario).options(
                joinedload(MovimientoInventario.producto),
                joinedload(MovimientoInventario.usuario),
            )
            termino = (termino or "").strip()
            if termino:
                patron = f"%{termino}%"
                q = q.filter(
                    MovimientoInventario.producto.has(
                        Producto.nombre.ilike(patron)
                    )
                )
            return q.order_by(MovimientoInventario.fecha.desc()).limit(limite).all()
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Stock por producto
    # ------------------------------------------------------------------

    def obtener_todo(self):
        """Obtener todos los registros de inventario."""
        db = next(get_db())
        try:
            return db.query(Inventario).all()
        finally:
            db.close()

    def obtener_por_producto(self, producto_id: int):
        """Obtener el inventario de un producto específico."""
        db = next(get_db())
        try:
            return db.query(Inventario).filter(Inventario.producto_id == producto_id).first()
        finally:
            db.close()

    def crear_inventario(self, producto_id: int, cantidad=0):
        """Crear el registro de inventario inicial de un producto."""
        db = next(get_db())
        try:
            existe = db.query(Inventario).filter(Inventario.producto_id == producto_id).first()
            if existe:
                return existe
            inventario = Inventario(producto_id=producto_id, cantidad=Decimal(str(cantidad)))
            db.add(inventario)
            db.commit()
            db.refresh(inventario)
            return inventario
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Registro de movimientos
    # ------------------------------------------------------------------

    def registrar_movimiento(
        self,
        producto_id: int,
        tipo: TipoMovimientoEnum,
        cantidad: Decimal,
        cantidad_anterior: Decimal,
        cantidad_nueva: Decimal,
        notas: str = None,
        referencia_id: int = None,
        referencia_tipo: str = None,
        usuario_id: int = None,
    ):
        """Registrar un movimiento de inventario."""
        db = next(get_db())
        try:
            movimiento = MovimientoInventario(
                producto_id=producto_id,
                tipo=tipo,
                cantidad=Decimal(str(cantidad)),
                cantidad_anterior=Decimal(str(cantidad_anterior)),
                cantidad_nueva=Decimal(str(cantidad_nueva)),
                notas=notas,
                referencia_id=referencia_id,
                referencia_tipo=referencia_tipo,
                usuario_id=usuario_id,
            )
            db.add(movimiento)
            db.commit()
            db.refresh(movimiento)
            return movimiento
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Ajuste manual de stock
    # ------------------------------------------------------------------

    @requiere_permiso("ajustar_inventario")
    def ajustar_stock(
        self,
        producto_id: int,
        nueva_cantidad: Decimal,
        notas: str = None,
        usuario_id: int = None,
    ):
        """
        Ajustar manualmente el stock de un producto.

        Actualiza el inventario y registra un movimiento de tipo AJUSTE
        con el motivo indicado en ``notas``.

        Returns:
            dict con resultado de la operación y el movimiento generado.
        """
        resultado = {"modificado": False, "movimiento": None, "mensaje": ""}

        db = next(get_db())
        try:
            producto = db.query(Producto).filter(Producto.id == producto_id).first()
            if not producto:
                raise ValueError("El producto no existe.")

            inventario = db.query(Inventario).filter(Inventario.producto_id == producto_id).first()
            if not inventario:
                raise ValueError("El producto no tiene registro de inventario.")

            nueva = Decimal(str(nueva_cantidad))
            anterior = Decimal(str(inventario.cantidad))

            if nueva < 0:
                raise ValueError("El stock no puede ser negativo.")

            notas = (notas or "").strip()
            if not notas:
                raise ValueError("Se requiere un motivo para el ajuste.")

            if nueva == anterior:
                resultado["mensaje"] = "El stock es el mismo, no se registró ajuste."
                return resultado

            # Actualizar stock
            inventario.cantidad = nueva
            db.flush()

            # Registrar movimiento de ajuste
            movimiento = MovimientoInventario(
                producto_id=producto_id,
                tipo=TipoMovimientoEnum.AJUSTE,
                cantidad=nueva - anterior,
                cantidad_anterior=anterior,
                cantidad_nueva=nueva,
                usuario_id=usuario_id,
                notas=notas,
                referencia_tipo="ajuste",
            )
            db.add(movimiento)
            db.commit()
            db.refresh(movimiento)

            resultado["modificado"] = True
            resultado["movimiento"] = movimiento
            resultado["mensaje"] = (
                f"Stock de '{producto.nombre}' ajustado de {anterior} a {nueva}."
            )
            # Auditoría (Fase 15)
            BitacoraService().registrar(
                usuario_id=usuario_id or obtener_usuario_id(),
                accion="ajuste_inventario",
                detalle=resultado["mensaje"],
            )
            return resultado
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo ajustar el stock: {e}")
        finally:
            db.close()