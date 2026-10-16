"""
Servicio de consultas para el Dashboard.
Agrupa las consultas de estadísticas e indicadores del panel principal.
"""

from datetime import datetime, date, time, timedelta
from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from database.connection import get_db
from database.models import (
    Venta,
    DetalleVenta,
    Producto,
    Inventario,
    EstadoVentaEnum,
)


class DashboardService:
    """Consultas agregadas para el panel principal."""

    def __init__(self):
        pass

    def _inicio_dia(self) -> datetime:
        """Fecha-hora de inicio del día actual (00:00:00)."""
        return datetime.combine(date.today(), time.min)

    # ------------------------------------------------------------------
    # Ventas del día
    # ------------------------------------------------------------------

    def resumen_ventas_hoy(self) -> dict:
        """Total vendido y número de tickets del día actual."""
        inicio = self._inicio_dia()
        db = next(get_db())
        try:
            estados_validos = [EstadoVentaEnum.COMPLETADA, EstadoVentaEnum.FIADO]
            base = db.query(Venta).filter(
                Venta.estado.in_(estados_validos),
                Venta.fecha >= inicio,
            )
            total = db.query(
                func.coalesce(func.sum(Venta.total), 0)
            ).filter(
                Venta.estado.in_(estados_validos),
                Venta.fecha >= inicio,
            ).scalar()
            tickets = base.count()
            return {
                "total_hoy": Decimal(str(total)),
                "tickets_hoy": tickets,
            }
        finally:
            db.close()

    def productos_activos(self) -> int:
        """Cantidad de productos activos registrados."""
        db = next(get_db())
        try:
            return db.query(func.count(Producto.id)).filter(
                Producto.activo == True
            ).scalar() or 0
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Inventario bajo
    # ------------------------------------------------------------------

    def productos_stock_bajo(self) -> list:
        """
        Productos activos cuyo stock actual es menor o igual al stock mínimo.
        Ordenados por diferencia (los más críticos primero).
        """
        db = next(get_db())
        try:
            return (
                db.query(Producto)
                .join(Inventario)
                .options(joinedload(Producto.inventario))
                .filter(
                    Producto.activo == True,
                    Inventario.cantidad <= func.coalesce(Producto.stock_minimo, 0),
                )
                .order_by((Inventario.cantidad - func.coalesce(Producto.stock_minimo, 0)).asc())
                .limit(10)
                .all()
            )
        finally:
            db.close()

    def productos_stock_bajo_count(self) -> int:
        """Cantidad de productos con stock bajo."""
        db = next(get_db())
        try:
            return db.query(func.count(Producto.id)).join(Inventario).filter(
                Producto.activo == True,
                Inventario.cantidad <= func.coalesce(Producto.stock_minimo, 0),
            ).scalar() or 0
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Productos más vendidos
    # ------------------------------------------------------------------

    def productos_mas_vendidos(self, limite: int = 5) -> list:
        """
        Productos más vendidos por cantidad total.
        Returns: lista de dicts {nombre, cantidad}.
        """
        db = next(get_db())
        try:
            filas = (
                db.query(
                    Producto.nombre,
                    func.sum(DetalleVenta.cantidad).label("cantidad_total"),
                )
                .join(DetalleVenta, DetalleVenta.producto_id == Producto.id)
                .group_by(Producto.id, Producto.nombre)
                .order_by(func.sum(DetalleVenta.cantidad).desc())
                .limit(limite)
                .all()
            )
            return [
                {"nombre": nombre, "cantidad": Decimal(str(cant))}
                for nombre, cant in filas
            ]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Últimas ventas
    # ------------------------------------------------------------------

    def ultimas_ventas(self, limite: int = 10) -> list:
        """Ventas más recientes con fecha, total y método de pago."""
        db = next(get_db())
        try:
            return (
                db.query(Venta)
                .filter(Venta.estado.in_(
                    [EstadoVentaEnum.COMPLETADA, EstadoVentaEnum.FIADO]
                ))
                .order_by(Venta.fecha.desc())
                .limit(limite)
                .all()
            )
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Ventas últimos 7 días
    # ------------------------------------------------------------------

    def ventas_ultimos_7_dias(self) -> list:
        """
        Total vendido por día para los últimos 7 días (incluido hoy).
        Returns: lista de dicts {fecha, total} en orden cronológico,
                 rellenando con ceros los días sin ventas.
        """
        hoy = date.today()
        inicio = datetime.combine(hoy - timedelta(days=6), time.min)

        db = next(get_db())
        try:
            filas = (
                db.query(
                    func.date(Venta.fecha).label("dia"),
                    func.sum(Venta.total).label("total_dia"),
                )
                .filter(
                    Venta.estado.in_(
                        [EstadoVentaEnum.COMPLETADA, EstadoVentaEnum.FIADO]
                    ),
                    Venta.fecha >= inicio,
                )
                .group_by(func.date(Venta.fecha))
                .all()
            )
        finally:
            db.close()

        por_dia = {dia: Decimal(str(total)) for dia, total in filas}

        resultado = []
        for i in range(7):
            fecha = hoy - timedelta(days=6 - i)
            clave = fecha.isoformat()
            resultado.append({
                "fecha": fecha,
                "total": por_dia.get(clave, Decimal("0")),
            })
        return resultado