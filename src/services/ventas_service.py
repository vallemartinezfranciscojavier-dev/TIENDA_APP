"""
Servicio de ventas.
Registra ventas completas con sus detalles, descuenta inventario y
registra los movimientos de inventario, todo dentro de una transacción.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func

from database.connection import get_db
from database.models import (
    Venta,
    DetalleVenta,
    Producto,
    Inventario,
    MovimientoInventario,
    Cliente,
    Credito,
    MetodoPagoEnum,
    EstadoVentaEnum,
    TipoMovimientoEnum,
)
from services.creditos_service import CreditosService
from services.cortes_caja_service import CortesCajaService
from services.bitacora_service import BitacoraService
from services.seguridad_service import requiere_permiso
from utils.calculations import redondear_moneda
from utils.formatters import formatear_folio


class VentasService:
    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def obtener_todas(self):
        db = next(get_db())
        try:
            return db.query(Venta).order_by(Venta.fecha.desc()).all()
        finally:
            db.close()

    def obtener_por_id(self, venta_id: int):
        db = next(get_db())
        try:
            return db.query(Venta).filter(Venta.id == venta_id).first()
        finally:
            db.close()

    def buscar_por_folio(self, folio: str):
        """Buscar una venta por su folio (lectura). None si no existe."""
        folio = (folio or "").strip()
        if not folio:
            return None
        db = next(get_db())
        try:
            return db.query(Venta).filter(Venta.folio == folio.upper()).first()
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def _generar_folio(self, db) -> str:
        """Generar un folio único de venta del tipo VTA-000001."""
        total = db.query(func.count(Venta.id)).scalar() or 0
        for i in range(total + 1, total + 10000):
            folio = formatear_folio("VTA", i)
            existe = db.query(Venta).filter(Venta.folio == folio).first()
            if not existe:
                return folio
        raise ValueError("No se pudo generar un folio disponible.")

    def _obtener_usuario_id(self, db) -> int:
        """Id del usuario con sesión activa (Fase 14: bloquear sin sesión)."""
        from services.sesion_service import obtener_usuario_id

        usuario_id = obtener_usuario_id()
        if not usuario_id:
            raise ValueError(
                "Debe iniciar sesión para registrar una venta."
            )
        return usuario_id

    # ------------------------------------------------------------------
    # Crear venta (transacción completa)
    # ------------------------------------------------------------------

    @requiere_permiso("realizar_ventas")
    def crear_venta(
        self,
        items: list,
        metodo_pago=None,
        recibido=None,
        descuento=None,
        usuario_id: int = None,
        notas: str = None,
        cliente_id: int = None,
    ):
        """
        Registrar una venta completa dentro de una transacción.

        1. Crea la venta (con folio único).
        2. Crea los detalles de venta.
        3. Valida el stock disponible de cada producto.
        4. Descuenta el inventario.
        5. Registra los movimientos de inventario (tipo SALIDA).
        6. Si el pago es a crédito (FIADO), crea el crédito del cliente y
           actualiza su saldo pendiente.

        Si ocurre cualquier error, se revierte TODO (rollback) y no queda
        ninguna venta incompleta en la base de datos.

        Args:
            items: Lista de dicts con ``producto_id`` y ``cantidad``.
            metodo_pago: Método de pago (MetodoPagoEnum o string).
            recibido: Monto recibido en efectivo (opcional, solo informativo).
            descuento: Descuento total en pesos (opcional).
            usuario_id: Id del usuario. Si es None, usa el admin por defecto.
            notas: Notas opcionales sobre la venta.
            cliente_id: Id del cliente (obligatorio si el pago es a crédito).

        Returns:
            Venta creada y confirmada.

        Raises:
            ValueError: Si el carrito está vacío, hay datos inválidos o
                        inventario insuficiente.
        """
        db = next(get_db())
        try:
            # Validaciones generales
            if not items:
                raise ValueError("El carrito está vacío.")

            if not usuario_id:
                usuario_id = self._obtener_usuario_id(db)

            # Vínculo con el corte de caja abierto (si existe)
            corte_abierto = CortesCajaService().obtener_corte_abierto()
            corte_caja_id = corte_abierto.id if corte_abierto else None

            # Método de pago
            if metodo_pago is None:
                metodo_pago = MetodoPagoEnum.EFECTIVO
            if isinstance(metodo_pago, str):
                metodo_pago = MetodoPagoEnum(metodo_pago)

            es_credito = metodo_pago == MetodoPagoEnum.FIADO

            # Para ventas a crédito se requiere un cliente
            if es_credito and not cliente_id:
                raise ValueError(
                    "Para registrar una venta a crédito debes seleccionar un cliente."
                )

            # Descuento
            desc = Decimal(str(descuento or 0))
            if desc < 0:
                raise ValueError("El descuento no puede ser negativo.")

            # Folio único
            folio = self._generar_folio(db)

            # Crear venta (los totales se calculan después de los detalles)
            venta = Venta(
                folio=folio,
                usuario_id=usuario_id,
                cliente_id=cliente_id if es_credito else None,
                corte_caja_id=corte_caja_id,
                metodo_pago=metodo_pago,
                estado=EstadoVentaEnum.FIADO if es_credito else EstadoVentaEnum.COMPLETADA,
                descuento=desc,
                impuestos=Decimal("0"),
                notas=notas,
            )
            db.add(venta)
            db.flush()  # Asigna venta.id

            subtotal = Decimal("0")

            for item in items:
                producto_id = item["producto_id"]
                try:
                    cantidad = Decimal(str(item["cantidad"]))
                except Exception:
                    raise ValueError("La cantidad de un producto no es válida.")

                if cantidad <= 0:
                    raise ValueError("Las cantidades deben ser mayores a cero.")

                producto = db.query(Producto).filter(Producto.id == producto_id).first()
                if not producto or not producto.activo:
                    raise ValueError("Un producto del carrito no existe o está inactivo.")

                inventario = (
                    db.query(Inventario)
                    .filter(Inventario.producto_id == producto_id)
                    .first()
                )
                if not inventario:
                    raise ValueError(
                        f"No hay inventario registrado para '{producto.nombre}'."
                    )

                stock_actual = Decimal(str(inventario.cantidad))
                if cantidad > stock_actual:
                    raise ValueError(
                        f"Stock insuficiente para '{producto.nombre}'.\n"
                        f"Disponible: {stock_actual} - Solicitado: {cantidad}"
                    )

                precio_unitario = Decimal(str(producto.precio_venta))
                linea_subtotal = redondear_moneda(precio_unitario * cantidad)
                cantidad_nueva = stock_actual - cantidad

                # Detalle de venta
                db.add(DetalleVenta(
                    venta_id=venta.id,
                    producto_id=producto_id,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    descuento=Decimal("0"),
                    subtotal=linea_subtotal,
                ))

                # Descontar inventario
                inventario.cantidad = cantidad_nueva

                # Movimiento de inventario (salida por venta)
                db.add(MovimientoInventario(
                    producto_id=producto_id,
                    tipo=TipoMovimientoEnum.SALIDA,
                    cantidad=-cantidad,
                    cantidad_anterior=stock_actual,
                    cantidad_nueva=cantidad_nueva,
                    usuario_id=usuario_id,
                    referencia_id=venta.id,
                    referencia_tipo="venta",
                    notas=f"Venta folio {folio}",
                ))

                subtotal += linea_subtotal

            # Totales de la venta
            subtotal = redondear_moneda(subtotal)
            total = redondear_moneda(subtotal - desc)
            # El total no puede ser negativo (el descuento máximo es el subtotal)
            if total < 0:
                total = Decimal("0")

            venta.subtotal = subtotal
            venta.total = total

            # Si es venta a crédito, registrar la deuda del cliente
            if es_credito:
                CreditosService().crear_credito(
                    db,
                    cliente_id=cliente_id,
                    venta_id=venta.id,
                    monto=total,
                )

            db.commit()
            db.refresh(venta)
            # Bitácora básica de acciones importantes (Fase 11).
            BitacoraService().registrar(
                usuario_id=usuario_id,
                accion="venta",
                detalle=f"Venta {venta.folio} por {metodo_pago.value if hasattr(metodo_pago, 'value') else metodo_pago} / {total}",
            )
            return venta
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo registrar la venta: {e}")
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Cancelar venta (Fase 14)
    # ------------------------------------------------------------------

    @requiere_permiso("cancelar_ventas")
    def cancelar_venta(self, venta_id: int, motivo: str = None):
        """
        Cancelar una venta dentro de una transacción.

        1. Valida que la venta exista y no esté ya cancelada.
        2. Repone el inventario de cada detalle (cantidad de vuelta).
        3. Registra un movimiento de inventario tipo DEVOLUCION por detalle
           (referencia_tipo="cancelacion").
        4. Marca la venta como CANCELADA (queda excluida de reportes y
           cortes porque estos solo contemplan COMPLETADA/FIADO).
        5. Si la venta era a crédito, perdona el pendiente del crédito
           asociado y recalcula el saldo del cliente (integridad financiera).

        Args:
            venta_id: Id de la venta a cancelar.
            motivo: Motivo opcional de la cancelación (se guarda en el
                    movimiento de inventario y en la bitácora).

        Raises:
            ValueError: Si la venta no existe o ya está cancelada.
            PermisoDenegado: Si no hay sesión o el rol no puede cancelar.
        """
        db = next(get_db())
        try:
            venta = db.query(Venta).filter(Venta.id == venta_id).first()
            if not venta:
                raise ValueError("La venta no existe.")
            if venta.estado == EstadoVentaEnum.CANCELADA:
                raise ValueError("Esta venta ya está cancelada.")

            usuario_id = self._obtener_usuario_id(db)
            motivo = (motivo or "").strip()

            # 1 y 2. Reponer inventario y registrar devolución por detalle
            detalles = (
                db.query(DetalleVenta)
                .filter(DetalleVenta.venta_id == venta.id)
                .all()
            )
            for det in detalles:
                cantidad = Decimal(str(det.cantidad))
                inventario = (
                    db.query(Inventario)
                    .filter(Inventario.producto_id == det.producto_id)
                    .first()
                )
                stock_anterior = (
                    Decimal(str(inventario.cantidad)) if inventario else Decimal("0")
                )
                stock_nuevo = stock_anterior + cantidad
                if inventario:
                    inventario.cantidad = stock_nuevo

                notas = f"Cancelación venta {venta.folio}"
                if motivo:
                    notas += f" — {motivo}"
                db.add(MovimientoInventario(
                    producto_id=det.producto_id,
                    tipo=TipoMovimientoEnum.DEVOLUCION,
                    cantidad=cantidad,
                    cantidad_anterior=stock_anterior,
                    cantidad_nueva=stock_nuevo,
                    usuario_id=usuario_id,
                    referencia_id=venta.id,
                    referencia_tipo="cancelacion",
                    notas=notas,
                ))

            # 3. Marcar como cancelada
            venta.estado = EstadoVentaEnum.CANCELADA

            # 4. Venta a crédito: perdonar el pendiente (si existe)
            if venta.cliente_id:
                credito = (
                    db.query(Credito)
                    .filter(Credito.venta_id == venta.id)
                    .first()
                )
                if credito is not None:
                    pendiente = Decimal(str(credito.monto_pendiente or 0))
                    if pendiente > 0:
                        credito.monto_pendiente = Decimal("0")
                        credito.pagado = True
                        credito.fecha_pago = datetime.now()
                    cliente = (
                        db.query(Cliente)
                        .filter(Cliente.id == venta.cliente_id)
                        .first()
                    )
                    if cliente:
                        # Recalcular el saldo desde los créditos pendientes,
                        # no restar a mano (integridad financiera).
                        cliente.saldo_actual = CreditosService()._saldo_en_sesion(
                            db, cliente.id
                        )

            db.commit()
            db.refresh(venta)
            detalle = f"Venta {venta.folio} cancelada"
            if motivo:
                detalle += f" — {motivo}"
            BitacoraService().registrar(
                usuario_id=usuario_id,
                accion="cancelacion_venta",
                detalle=detalle,
            )
            return venta
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo cancelar la venta: {e}")
        finally:
            db.close()