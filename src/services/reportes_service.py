"""
Servicio de reportes.
Consultas de ventas, compras, inventario, crédito y caja por rango de fechas.
"""

from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import func, case
from sqlalchemy.orm import joinedload

from database.connection import get_db
from database.models import (
    Venta,
    DetalleVenta,
    Producto,
    Inventario,
    Cliente,
    Credito,
    Abono,
    Proveedor,
    Compra,
    DetalleCompra,
    MovimientoInventario,
    CorteCaja,
    Usuario,
    EstadoVentaEnum,
    MetodoPagoEnum,
    TipoMovimientoEnum,
)
from services.seguridad_service import requiere_permiso
from utils.calculations import redondear_moneda


# Métodos de pago en el orden de presentación en reportes.
METODOS_LABEL = {
    MetodoPagoEnum.EFECTIVO: "Efectivo",
    MetodoPagoEnum.TARJETA: "Tarjeta",
    MetodoPagoEnum.TRANSFERENCIA: "Transferencia",
    MetodoPagoEnum.FIADO: "Fiado",
}

# Estados de venta que cuentan como "venta válida" para reportes.
ESTADOS_VALIDOS = [EstadoVentaEnum.COMPLETADA, EstadoVentaEnum.FIADO]


def etiqueta_metodo(metodo) -> str:
    """Etiqueta legible de un método de pago."""
    return METODOS_LABEL.get(metodo, str(metodo).replace("_", " ").title())


class ReportesService:
    """Consultas agregadas para el módulo de reportes."""

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _rangos(self, fecha_inicio, fecha_fin):
        """
        Normalizar a rangos datetime inclusivos.

        Límites: hasta el final del día para la fecha_fin. Si falta alguno,
        usa el inicio/el final del día actual según corresponda.
        """
        ahora = datetime.now()
        inicio = fecha_inicio or datetime.combine(ahora.date(), time.min)
        if not isinstance(inicio, datetime):
            inicio = datetime.combine(inicio, time.min)

        fin = fecha_fin or ahora
        if not isinstance(fin, datetime):
            fin = datetime.combine(fin, time.max)
        if fin.time() == time.min:
            fin = datetime.combine(fin.date(), time.max)
        return inicio, fin

    def _query_ventas_validas(self, db, fecha_inicio, fecha_fin):
        """Query base de ventas válidas en el rango."""
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        return db.query(Venta).filter(
            Venta.estado.in_(ESTADOS_VALIDOS),
            Venta.fecha >= inicio,
            Venta.fecha <= fin,
        )

    # ------------------------------------------------------------------
    # Resumen del periodo
    # ------------------------------------------------------------------

    def resumen_periodo(self, fecha_inicio, fecha_fin):
        """
        Resumen de ventas en el periodo:
            total, numero de tickets, venta minima, maxima y promedio.
        Returns:
            dict con Decimales y enteros.
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            fila = (
                db.query(
                    func.coalesce(func.sum(Venta.total), 0),
                    func.count(Venta.id),
                    func.coalesce(func.min(Venta.total), 0),
                    func.coalesce(func.max(Venta.total), 0),
                )
                .filter(
                    Venta.estado.in_(ESTADOS_VALIDOS),
                    Venta.fecha >= inicio,
                    Venta.fecha <= fin,
                )
                .one()
            )
            total, tickets, minima, maxima = fila
            tickets = tickets or 0
            promedio = Decimal("0") if tickets == 0 else Decimal(str(total)) / tickets
            return {
                "total": redondear_moneda(total or 0),
                "tickets": tickets,
                "minima": redondear_moneda(minima or 0),
                "maxima": redondear_moneda(maxima or 0),
                "promedio": redondear_moneda(promedio),
            }
        finally:
            db.close()

    def por_metodo_pago(self, fecha_inicio, fecha_fin):
        """
        Totales de ventas agrupadas por método de pago en el periodo.
        Returns:
            list de dicts {metodo, etiqueta, total}.
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            filas = (
                db.query(
                    Venta.metodo_pago,
                    func.coalesce(func.sum(Venta.total), 0).label("total"),
                )
                .filter(
                    Venta.estado.in_(ESTADOS_VALIDOS),
                    Venta.fecha >= inicio,
                    Venta.fecha <= fin,
                )
                .group_by(Venta.metodo_pago)
                .order_by(func.sum(Venta.total).desc())
                .all()
            )
            resultado = []
            for metodo, total in filas:
                resultado.append({
                    "metodo": metodo,
                    "etiqueta": etiqueta_metodo(metodo),
                    "total": redondear_moneda(total or 0),
                })
            return resultado
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Detalle de ventas
    # ------------------------------------------------------------------

    def ventas_periodo(self, fecha_inicio, fecha_fin, limite: int = 200):
        """
        Ventas válidas del periodo ordenadas por fecha.
        Returns:
            list de dicts {folio, fecha, usuario, cliente, metodo, estado, total}.
        """
        db = next(get_db())
        try:
            ventas = (
                self._query_ventas_validas(db, fecha_inicio, fecha_fin)
                .order_by(Venta.fecha.desc())
                .limit(limite)
                .all()
            )
            resultado = []
            for v in ventas:
                resultado.append({
                    "id": v.id,
                    "folio": v.folio,
                    "fecha": v.fecha,
                    "usuario": v.usuario.nombre if v.usuario else "—",
                    "cliente": v.cliente.nombre if v.cliente else "Mostrador",
                    "metodo": etiqueta_metodo(v.metodo_pago),
                    "estado": v.estado.value if hasattr(v.estado, "value") else str(v.estado),
                    "total": Decimal(str(v.total or 0)),
                })
            return resultado
        finally:
            db.close()

    def productos_mas_vendidos(self, fecha_inicio, fecha_fin, limite: int = 10):
        """
        Productos más vendidos en el periodo por cantidad.
        Returns:
            list de dicts {nombre, cantidad, monto}.
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            filas = (
                db.query(
                    Producto.nombre,
                    func.sum(DetalleVenta.cantidad).label("cantidad"),
                    func.sum(DetalleVenta.subtotal).label("monto"),
                )
                .join(DetalleVenta, DetalleVenta.producto_id == Producto.id)
                .join(Venta, DetalleVenta.venta_id == Venta.id)
                .filter(
                    Venta.estado.in_(ESTADOS_VALIDOS),
                    Venta.fecha >= inicio,
                    Venta.fecha <= fin,
                )
                .group_by(Producto.id, Producto.nombre)
                .order_by(func.sum(DetalleVenta.cantidad).desc())
                .limit(limite)
                .all()
            )
            return [
                {
                    "nombre": nombre,
                    "cantidad": Decimal(str(cant or 0)),
                    "monto": redondear_moneda(monto or 0),
                }
                for nombre, cant, monto in filas
            ]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Ventas por día (para tendencia)
    # ------------------------------------------------------------------

    def ventas_por_dia(self, fecha_inicio, fecha_fin):
        """
        Total vendido por día en el periodo.
        Returns:
            list de dicts {dia, total} en orden cronológico.
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            filas = (
                db.query(
                    func.date(Venta.fecha).label("dia"),
                    func.coalesce(func.sum(Venta.total), 0).label("total"),
                )
                .filter(
                    Venta.estado.in_(ESTADOS_VALIDOS),
                    Venta.fecha >= inicio,
                    Venta.fecha <= fin,
                )
                .group_by(func.date(Venta.fecha))
                .order_by(func.date(Venta.fecha))
                .all()
            )
            return [
                {"dia": dia, "total": redondear_moneda(total or 0)}
                for dia, total in filas
            ]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Productos menos vendidos
    # ------------------------------------------------------------------

    def _detalles_del_periodo(self, db, fecha_inicio, fecha_fin):
        """
        Subquery de los detalles de venta del periodo (ventas válidas).
        Permite contar productos vendidos 0 veces en el periodo con un
        outer join, respetando el estado y el rango de fechas.
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        return (
            db.query(
                DetalleVenta.producto_id,
                DetalleVenta.cantidad,
                DetalleVenta.subtotal,
            )
            .join(Venta, DetalleVenta.venta_id == Venta.id)
            .filter(
                Venta.estado.in_(ESTADOS_VALIDOS),
                Venta.fecha >= inicio,
                Venta.fecha <= fin,
            )
            .subquery()
        )

    def productos_menos_vendidos(self, fecha_inicio, fecha_fin, limite: int = 10):
        """
        Productos con menor cantidad vendida en el periodo.

        Incluye productos activos que no se vendieron en el periodo
        (cantidad 0), ordenados de menor a mayor.

        Returns:
            list de dicts {nombre, cantidad, monto}.
        """
        db = next(get_db())
        try:
            det = self._detalles_del_periodo(db, fecha_inicio, fecha_fin)
            filas = (
                db.query(
                    Producto.nombre,
                    func.coalesce(func.sum(det.c.cantidad), 0).label("cantidad"),
                    func.coalesce(func.sum(det.c.subtotal), 0).label("monto"),
                )
                .outerjoin(det, det.c.producto_id == Producto.id)
                .filter(Producto.activo.is_(True))
                .group_by(Producto.id, Producto.nombre)
                .order_by(func.coalesce(func.sum(det.c.cantidad), 0).asc())
                .limit(limite)
                .all()
            )
            return [
                {
                    "nombre": nombre,
                    "cantidad": Decimal(str(cant or 0)),
                    "monto": redondear_moneda(monto or 0),
                }
                for nombre, cant, monto in filas
            ]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Inventario (valor estimado, sin stock, stock bajo)
    # ------------------------------------------------------------------

    def inventario_estado(self):
        """
        Estado global del inventario:
            - Valor estimado a precio de compra (costo) y a precio de venta.
            - Número total de productos activos.
            - Número de productos sin stock y con stock bajo.

        Returns:
            dict con Decimales e enteros.
        """
        db = next(get_db())
        try:
            valor_costo = (
                db.query(
                    func.coalesce(
                        func.sum(
                            Inventario.cantidad
                            * func.coalesce(Producto.precio_compra, Producto.precio_venta)
                        ),
                        0,
                    )
                )
                .join(Producto)
                .filter(Producto.activo.is_(True))
                .scalar()
                or 0
            )
            valor_venta = (
                db.query(
                    func.coalesce(func.sum(Inventario.cantidad * Producto.precio_venta), 0)
                )
                .join(Producto)
                .filter(Producto.activo.is_(True))
                .scalar()
                or 0
            )
            total_productos = (
                db.query(func.count(Producto.id))
                .filter(Producto.activo.is_(True))
                .scalar()
                or 0
            )
            sin_stock = (
                db.query(func.count(Producto.id))
                .join(Inventario)
                .filter(
                    Producto.activo.is_(True),
                    Inventario.cantidad == 0,
                )
                .scalar()
                or 0
            )
            bajo = (
                db.query(func.count(Producto.id))
                .join(Inventario)
                .filter(
                    Producto.activo.is_(True),
                    Inventario.cantidad > 0,
                    Inventario.cantidad
                    <= func.coalesce(Producto.stock_minimo, 0),
                )
                .scalar()
                or 0
            )
            return {
                "valor_costo": redondear_moneda(valor_costo),
                "valor_venta": redondear_moneda(valor_venta),
                "total_productos": total_productos,
                "sin_stock": sin_stock,
                "bajo": bajo,
            }
        finally:
            db.close()

    def productos_sin_stock(self, limite: int = 50):
        """
        Productos activos sin stock (cantidad == 0).

        Returns:
            list de dicts {nombre, categoria, stock, precio_venta}.
        """
        db = next(get_db())
        try:
            filas = (
                db.query(Producto)
                .join(Inventario)
                .filter(
                    Producto.activo.is_(True),
                    Inventario.cantidad == 0,
                )
                .order_by(Producto.nombre)
                .limit(limite)
                .all()
            )
            return [
                {
                    "nombre": p.nombre,
                    "categoria": p.categoria.nombre if p.categoria else "—",
                    "stock": Decimal(str((p.inventario.cantidad if p.inventario else 0))),
                    "stock_minimo": Decimal(str(p.stock_minimo or 0)),
                    "precio_venta": redondear_moneda(p.precio_venta),
                }
                for p in filas
            ]
        finally:
            db.close()

    def productos_inventario_bajo(self, limite: int = 50):
        """
        Productos activos con stock bajo (cantidad > 0 y <= stock_minimo),
        ordenados por criticidad (menor margen primero).

        Returns:
            list de dicts {nombre, categoria, stock, stock_minimo, precio_venta}.
        """
        db = next(get_db())
        try:
            filas = (
                db.query(Producto)
                .join(Inventario)
                .filter(
                    Producto.activo.is_(True),
                    Inventario.cantidad > 0,
                    Inventario.cantidad
                    <= func.coalesce(Producto.stock_minimo, 0),
                )
                .order_by(
                    (
                        Inventario.cantidad
                        - func.coalesce(Producto.stock_minimo, 0)
                    ).asc(),
                    Producto.nombre,
                )
                .limit(limite)
                .all()
            )
            return [
                {
                    "nombre": p.nombre,
                    "categoria": p.categoria.nombre if p.categoria else "—",
                    "stock": Decimal(str((p.inventario.cantidad if p.inventario else 0))),
                    "stock_minimo": Decimal(str(p.stock_minimo or 0)),
                    "precio_venta": redondear_moneda(p.precio_venta),
                }
                for p in filas
            ]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Productos vendidos detallado (con precio promedio y ordenamiento)
    # ------------------------------------------------------------------

    def productos_vendidos_detalle(self, fecha_inicio, fecha_fin, orden: str = "mas", limite: int = 50):
        """
        Productos vendidos en el periodo con cantidad, importe y precio promedio.

        orden:
            "mas"    -> más vendido por cantidad (default)
            "menos"  -> menos vendido por cantidad
            "ingreso"-> mayor ingreso (importe)

        Returns:
            list de dicts {nombre, cantidad, monto, precio_promedio}.
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            q = (
                db.query(
                    Producto.nombre,
                    func.sum(DetalleVenta.cantidad).label("cantidad"),
                    func.sum(DetalleVenta.subtotal).label("monto"),
                    func.avg(DetalleVenta.precio_unitario).label("precio_promedio"),
                )
                .join(DetalleVenta, DetalleVenta.producto_id == Producto.id)
                .join(Venta, DetalleVenta.venta_id == Venta.id)
                .filter(
                    Venta.estado.in_(ESTADOS_VALIDOS),
                    Venta.fecha >= inicio,
                    Venta.fecha <= fin,
                )
                .group_by(Producto.id, Producto.nombre)
            )
            orden_col = func.sum(DetalleVenta.cantidad)
            if orden == "menos":
                q = q.order_by(orden_col.asc())
            elif orden == "ingreso":
                q = q.order_by(func.sum(DetalleVenta.subtotal).desc())
            else:
                q = q.order_by(orden_col.desc())
            filas = q.limit(limite).all()
            return [
                {
                    "nombre": nombre,
                    "cantidad": Decimal(str(cant or 0)),
                    "monto": redondear_moneda(monto or 0),
                    "precio_promedio": redondear_moneda(precio_prom or 0),
                }
                for nombre, cant, monto, precio_prom in filas
            ]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Ganancias (utilidad bruta por producto)
    # ------------------------------------------------------------------

    def ganancias_periodo(self, fecha_inicio, fecha_fin, limite: int = 50):
        """
        Ganancia bruta = ingreso por ventas - costo de mercancía vendida.

        El costo por producto se calcula con el precio_compra real registrado;
        si un producto no tiene precio de compra, se usa su precio de venta
        (margen 0) como fallback, para no inflar la ganancia.

        Returns:
            list de dicts {nombre, cantidad, ingreso, costo, ganancia, margen}.
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            costo_row = func.coalesce(Producto.precio_compra, Producto.precio_venta) * DetalleVenta.cantidad
            filas = (
                db.query(
                    Producto.nombre,
                    func.sum(DetalleVenta.cantidad).label("cantidad"),
                    func.sum(DetalleVenta.subtotal).label("ingreso"),
                    func.sum(costo_row).label("costo"),
                    func.sum(DetalleVenta.subtotal - costo_row).label("ganancia"),
                )
                .join(DetalleVenta, DetalleVenta.producto_id == Producto.id)
                .join(Venta, DetalleVenta.venta_id == Venta.id)
                .filter(
                    Venta.estado.in_(ESTADOS_VALIDOS),
                    Venta.fecha >= inicio,
                    Venta.fecha <= fin,
                )
                .group_by(Producto.id, Producto.nombre)
                .order_by(func.sum(DetalleVenta.subtotal - costo_row).desc())
                .limit(limite)
                .all()
            )
            resultado = []
            for nombre, cant, ingreso, costo, ganancia in filas:
                ingreso = Decimal(str(ingreso or 0))
                ganancia = Decimal(str(ganancia or 0))
                margen = (
                    Decimal("0")
                    if ingreso == 0
                    else (ganancia / ingreso * 100).quantize(Decimal("0.1"))
                )
                resultado.append({
                    "nombre": nombre,
                    "cantidad": Decimal(str(cant or 0)),
                    "ingreso": redondear_moneda(ingreso),
                    "costo": redondear_moneda(costo or 0),
                    "ganancia": redondear_moneda(ganancia),
                    "margen": margen,
                })
            return resultado
        finally:
            db.close()

    def ganancias_resumen(self, fecha_inicio, fecha_fin):
        """
        Totales globales de ganancias del periodo:
            ventas, costo mercancía, ganancia bruta y margen %.
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            costo_row = func.coalesce(Producto.precio_compra, Producto.precio_venta) * DetalleVenta.cantidad
            fila = (
                db.query(
                    func.coalesce(func.sum(DetalleVenta.subtotal), 0),
                    func.coalesce(func.sum(costo_row), 0),
                )
                .select_from(Producto)
                .join(DetalleVenta, DetalleVenta.producto_id == Producto.id)
                .join(Venta, DetalleVenta.venta_id == Venta.id)
                .filter(
                    Venta.estado.in_(ESTADOS_VALIDOS),
                    Venta.fecha >= inicio,
                    Venta.fecha <= fin,
                )
                .one()
            )
            ventas, costo = fila
            ventas = Decimal(str(ventas or 0))
            costo = Decimal(str(costo or 0))
            ganancia = ventas - costo
            margen = Decimal("0") if ventas == 0 else (ganancia / ventas * 100).quantize(Decimal("0.1"))
            return {
                "ventas": redondear_moneda(ventas),
                "costo": redondear_moneda(costo),
                "ganancia": redondear_moneda(ganancia),
                "margen": margen,
            }
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Compras por periodo
    # ------------------------------------------------------------------

    def compras_periodo(self, fecha_inicio, fecha_fin, proveedor_id: int = None, limite: int = 200):
        """
        Compras del periodo, con proveedor y número de productos comprados.

        Args:
            proveedor_id: filtra por proveedor (None = todos).
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            q = db.query(Compra).filter(
                Compra.fecha >= inicio,
                Compra.fecha <= fin,
            )
            if proveedor_id:
                q = q.filter(Compra.proveedor_id == proveedor_id)
            compras = q.order_by(Compra.fecha.desc()).limit(limite).all()
            resultado = []
            for c in compras:
                num_productos = (
                    db.query(func.coalesce(func.sum(DetalleCompra.cantidad), 0))
                    .filter(DetalleCompra.compra_id == c.id)
                    .scalar() or 0
                )
                resultado.append({
                    "id": c.id,
                    "folio": c.folio,
                    "fecha": c.fecha,
                    "proveedor": c.proveedor.nombre if c.proveedor else "—",
                    "total": redondear_moneda(c.total or 0),
                    "productos": Decimal(str(num_productos)),
                })
            return resultado
        finally:
            db.close()

    def compras_resumen(self, fecha_inicio, fecha_fin):
        """Resumen de compras del periodo: total, órdenes y proveedor principal."""
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            fila = (
                db.query(
                    func.coalesce(func.sum(Compra.total), 0),
                    func.count(Compra.id),
                )
                .filter(Compra.fecha >= inicio, Compra.fecha <= fin)
                .one()
            )
            total, ordenes = fila
            proveedor_top = (
                db.query(Proveedor.nombre, func.sum(Compra.total).label("total"))
                .join(Compra, Compra.proveedor_id == Proveedor.id)
                .filter(Compra.fecha >= inicio, Compra.fecha <= fin)
                .group_by(Proveedor.id)
                .order_by(func.sum(Compra.total).desc())
                .first()
            )
            return {
                "total": redondear_moneda(total or 0),
                "ordenes": ordenes or 0,
                "proveedor_top": proveedor_top[0] if proveedor_top else "—",
            }
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Clientes y fiado
    # ------------------------------------------------------------------

    def clientes_fiados(self):
        """
        Clientes activos con saldo pendiente de fiado.

        Muestra el estado global de cada cliente: total fiado histórico,
        total abonado y saldo pendiente actual.

        Returns:
            list de dicts {cliente, telefono, total_fiado, total_abonado, pendiente}.
        """
        db = next(get_db())
        try:
            clientes = (
                db.query(Cliente)
                .filter(Cliente.activo.is_(True))
                .order_by(Cliente.saldo_actual.desc())
                .all()
            )
            resultado = []
            for cl in clientes:
                saldo = Decimal(str(cl.saldo_actual or 0))
                if saldo <= 0:
                    continue
                total_fiado = (
                    db.query(func.coalesce(func.sum(Credito.monto_original), 0))
                    .filter(Credito.cliente_id == cl.id)
                    .scalar() or 0
                )
                total_abonado = (
                    db.query(func.coalesce(func.sum(Abono.monto), 0))
                    .join(Credito, Abono.credito_id == Credito.id)
                    .filter(Credito.cliente_id == cl.id)
                    .scalar() or 0
                )
                resultado.append({
                    "cliente": cl.nombre,
                    "telefono": cl.telefono or "—",
                    "total_fiado": redondear_moneda(total_fiado),
                    "total_abonado": redondear_moneda(total_abonado),
                    "pendiente": redondear_moneda(saldo),
                })
            return resultado
        finally:
            db.close()

    def clientes_resumen(self):
        """Resumen global del fiado: fiado histórico, abonado, pendiente y deudores."""
        db = next(get_db())
        try:
            total_fiado = (
                db.query(func.coalesce(func.sum(Credito.monto_original), 0)).scalar() or 0
            )
            total_pendiente = (
                db.query(func.coalesce(func.sum(Cliente.saldo_actual), 0))
                .filter(Cliente.activo.is_(True))
                .scalar() or 0
            )
            total_abonado = (
                db.query(func.coalesce(func.sum(Abono.monto), 0)).scalar() or 0
            )
            deudores = (
                db.query(func.count(Cliente.id))
                .filter(Cliente.activo.is_(True), Cliente.saldo_actual > 0)
                .scalar() or 0
            )
            return {
                "total_fiado": redondear_moneda(total_fiado),
                "total_abonado": redondear_moneda(total_abonado),
                "total_pendiente": redondear_moneda(total_pendiente),
                "deudores": deudores,
            }
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Cortes de caja
    # ------------------------------------------------------------------

    def cortes_caja_periodo(self, fecha_inicio, fecha_fin, limite: int = 100):
        """
        Cortes de caja del periodo, con el total de ventas asociadas a cada uno.

        Returns:
            list de dicts {id, fecha_apertura, fecha_cierre, monto_inicial,
            esperado, contado, diferencia, total_ventas, cerrado}.
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            cortes = (
                db.query(CorteCaja)
                .filter(
                    CorteCaja.fecha_apertura >= inicio,
                    CorteCaja.fecha_apertura <= fin,
                )
                .order_by(CorteCaja.fecha_apertura.desc())
                .limit(limite)
                .all()
            )
            resultado = []
            for c in cortes:
                total_ventas = (
                    db.query(func.coalesce(func.sum(Venta.total), 0))
                    .filter(
                        Venta.corte_caja_id == c.id,
                        Venta.estado.in_(ESTADOS_VALIDOS),
                    )
                    .scalar() or 0
                )
                resultado.append({
                    "id": c.id,
                    "fecha_apertura": c.fecha_apertura,
                    "fecha_cierre": c.fecha_cierre,
                    "monto_inicial": redondear_moneda(c.monto_inicial or 0),
                    "esperado": redondear_moneda(c.monto_final_sistema or 0),
                    "contado": redondear_moneda(c.monto_final_real or 0),
                    "diferencia": redondear_moneda(c.diferencia or 0),
                    "total_ventas": redondear_moneda(total_ventas),
                    "cerrado": bool(c.cerrado),
                })
            return resultado
        finally:
            db.close()

    def cortes_resumen(self, fecha_inicio, fecha_fin):
        """Resumen de cortes del periodo: cantidad, efectivo contado, diferencias y ventas."""
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            fila = (
                db.query(
                    func.count(CorteCaja.id),
                    func.coalesce(func.sum(CorteCaja.monto_final_real), 0),
                    func.coalesce(func.sum(CorteCaja.diferencia), 0),
                )
                .filter(CorteCaja.fecha_apertura >= inicio, CorteCaja.fecha_apertura <= fin)
                .one()
            )
            cortes, efectivo_contado, diferencia_total = fila
            # Total de ventas asociadas a cortes del periodo
            total_ventas_cortes = (
                db.query(func.coalesce(func.sum(Venta.total), 0))
                .join(CorteCaja, Venta.corte_caja_id == CorteCaja.id)
                .filter(
                    CorteCaja.fecha_apertura >= inicio,
                    CorteCaja.fecha_apertura <= fin,
                    Venta.estado.in_(ESTADOS_VALIDOS),
                )
                .scalar() or 0
            )
            return {
                "cortes": cortes or 0,
                "efectivo_contado": redondear_moneda(efectivo_contado),
                "diferencia_total": redondear_moneda(diferencia_total),
                "ventas": redondear_moneda(total_ventas_cortes),
            }
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Movimientos de inventario
    # ------------------------------------------------------------------

    def movimientos_periodo(self, fecha_inicio, fecha_fin, tipo: str = None, limite: int = 300):
        """
        Movimientos de inventario del periodo.

        Args:
            tipo: None (todos) o uno de "entrada", "salida", "ajuste", "devolucion".
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            q = db.query(MovimientoInventario).filter(
                MovimientoInventario.fecha >= inicio,
                MovimientoInventario.fecha <= fin,
            )
            if tipo:
                try:
                    q = q.filter(MovimientoInventario.tipo == TipoMovimientoEnum(tipo))
                except ValueError:
                    pass  # tipo inválido: mostrar todos
            movimientos = q.order_by(MovimientoInventario.fecha.desc()).limit(limite).all()
            resultado = []
            for m in movimientos:
                resultado.append({
                    "id": m.id,
                    "fecha": m.fecha,
                    "producto": m.producto.nombre if m.producto else "—",
                    "tipo": m.tipo.value if hasattr(m.tipo, "value") else str(m.tipo),
                    "cantidad": Decimal(str(m.cantidad or 0)),
                    "usuario": m.usuario.nombre if m.usuario else "—",
                    "referencia": m.notas or m.referencia_tipo or "—",
                })
            return resultado
        finally:
            db.close()

    def movimientos_resumen(self, fecha_inicio, fecha_fin):
        """Conteo de movimientos por tipo en el periodo."""
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            filas = (
                db.query(
                    MovimientoInventario.tipo,
                    func.count(MovimientoInventario.id),
                )
                .filter(MovimientoInventario.fecha >= inicio, MovimientoInventario.fecha <= fin)
                .group_by(MovimientoInventario.tipo)
                .all()
            )
            total = 0
            por_tipo = {}
            for tipo, count in filas:
                clave = tipo.value if hasattr(tipo, "value") else str(tipo)
                por_tipo[clave] = count
                total += count
            return {
                "entradas": por_tipo.get("entrada", 0),
                "salidas": por_tipo.get("salida", 0),
                "ajustes": por_tipo.get("ajuste", 0),
                "devoluciones": por_tipo.get("devolucion", 0),
                "total": total,
            }
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Descuentos del periodo
    # ------------------------------------------------------------------

    def descuentos_periodo(self, fecha_inicio, fecha_fin):
        """
        Total de descuentos aplicados en ventas del periodo.

        Returns:
            dict con 'total' (Decimal) y 'descuento_medio' (Decimal).
        """
        inicio, fin = self._rangos(fecha_inicio, fecha_fin)
        db = next(get_db())
        try:
            fila = (
                db.query(
                    func.coalesce(func.sum(Venta.descuento), 0),
                    func.count(Venta.id),
                )
                .filter(
                    Venta.estado.in_(ESTADOS_VALIDOS),
                    Venta.fecha >= inicio,
                    Venta.fecha <= fin,
                )
                .one()
            )
            total, tickets = fila
            tickets = tickets or 0
            descuento_medio = (
                Decimal("0") if tickets == 0
                else Decimal(str(total)) / tickets
            )
            return {
                "total": redondear_moneda(total or 0),
                "medio": redondear_moneda(descuento_medio),
            }
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Inventario detallado (todos los productos activos con estado)
    # ------------------------------------------------------------------

    def inventario_detallado(self, limite: int = 500):
        """
        Listado completo de productos activos con su estado visual.

        Estado: "●" verde (> stock_minimo), "●" amarillo (>0 y <= stock_minimo),
                "●" rojo (sin stock / 0).

        Returns:
            list de dicts {nombre, categoria, existencia, unidad, costo,
            precio_venta, valor_inv, stock_minimo, estado}.
        """
        db = next(get_db())
        try:
            filas = (
                db.query(Producto)
                .options(joinedload(Producto.inventario))
                .outerjoin(Producto.categoria)
                .filter(Producto.activo.is_(True))
                .order_by(Producto.nombre)
                .limit(limite)
                .all()
            )
            resultado = []
            for p in filas:
                stock = Decimal(str((p.inventario.cantidad if p.inventario else 0)))
                costo_unit = Decimal(str(p.precio_compra or 0))
                precio = Decimal(str(p.precio_venta or 0))
                minimo = Decimal(str(p.stock_minimo or 0))
                valor_inv = redondear_moneda(stock * costo_unit)
                # Estado visual
                if stock == 0:
                    estado = "● Sin stock"
                elif stock <= minimo:
                    estado = "● Bajo"
                else:
                    estado = "● OK"
                resultado.append({
                    "nombre": p.nombre,
                    "categoria": p.categoria.nombre if p.categoria else "—",
                    "existencia": stock,
                    "unidad": p.unidad_medida or "pza",
                    "costo": redondear_moneda(costo_unit),
                    "precio_venta": redondear_moneda(precio),
                    "valor_inv": valor_inv,
                    "stock_minimo": minimo,
                    "estado": estado,
                })
            return resultado
        finally:
            db.close()


# ----------------------------------------------------------------------
# Permiso "consultar_reportes" aplicado a TODAS las consultas públicas del
# servicio (Fase 14). Las internas (con guion bajo) no se tocan.
#
# Esto garantiza que el permiso se aplica en la lógica de negocio y no
# solo ocultando el botón/módulo en la interfaz.
# ----------------------------------------------------------------------
for _nombre, _metodo in list(vars(ReportesService).items()):
    if _nombre.startswith("_") or not callable(_metodo):
        continue
    setattr(ReportesService, _nombre, requiere_permiso("consultar_reportes")(_metodo))