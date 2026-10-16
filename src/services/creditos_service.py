"""
Servicio de créditos/fiados.
Gestiona las deudas de los clientes (créditos), los abonos (pagos parciales)
y el saldo pendiente, manteniendo la integridad financiera del sistema.

Regla de integridad:
- El saldo pendiente de un cliente es la suma de los montos pendientes de
  sus créditos activos.
- Nunca se modifica un saldo directamente: cualquier cambio se registra
  como un abono (movimiento).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import joinedload

from database.connection import get_db
from database.models import (
    Cliente,
    Credito,
    Abono,
    Usuario,
    Venta,
    EstadoVentaEnum,
)
from services.bitacora_service import BitacoraService
from services.seguridad_service import requiere_permiso
from utils.calculations import redondear_moneda


class CreditosService:
    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def _obtener_usuario_id(self, db) -> int:
        """Id del usuario con sesión activa (Fase 14: bloquear sin sesión)."""
        from services.sesion_service import obtener_usuario_id

        usuario_id = obtener_usuario_id()
        if not usuario_id:
            raise ValueError("Debe iniciar sesión para registrar el abono.")
        return usuario_id

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def obtener_creditos_por_cliente(self, cliente_id: int):
        """Créditos de un cliente (pendientes y pagados), más recientes primero."""
        db = next(get_db())
        try:
            return (
                db.query(Credito)
                .options(joinedload(Credito.venta))
                .filter(Credito.cliente_id == cliente_id)
                .order_by(Credito.fecha_creacion.desc())
                .all()
            )
        finally:
            db.close()

    def obtener_abonos(self, credito_id: int):
        """Abonos aplicados a un crédito, más recientes primero."""
        db = next(get_db())
        try:
            return (
                db.query(Abono)
                .options(joinedload(Abono.usuario))
                .filter(Abono.credito_id == credito_id)
                .order_by(Abono.fecha.desc())
                .all()
            )
        finally:
            db.close()

    def obtener_abonos_por_cliente(self, cliente_id: int):
        """Todos los abonos realizados por un cliente."""
        db = next(get_db())
        try:
            return (
                db.query(Abono)
                .options(joinedload(Abono.usuario))
                .join(Credito, Credito.id == Abono.credito_id)
                .filter(Credito.cliente_id == cliente_id)
                .order_by(Abono.fecha.desc())
                .all()
            )
        finally:
            db.close()

    def obtener_historial_completo(self, cliente_id: int) -> dict:
        """Resumen completo del historial de crédito de un cliente.

        Returns:
            dict con ``saldo_pendiente`` (Decimal) y ``creditos`` (lista
            de dicts con cada crédito y sus abonos).
        """
        creditos = self.obtener_creditos_por_cliente(cliente_id)
        saldo = Decimal("0")

        resultado = []
        for credito in creditos:
            pendiente = Decimal(str(credito.monto_pendiente))
            abonos = [
                {
                    "id": a.id,
                    "monto": Decimal(str(a.monto)),
                    "fecha": a.fecha,
                    "usuario": a.usuario.nombre if a.usuario else "Sistema",
                    "notas": a.notas,
                }
                for a in self.obtener_abonos(credito.id)
            ]
            resultado.append({
                "id": credito.id,
                "monto_original": Decimal(str(credito.monto_original)),
                "monto_pendiente": pendiente,
                "fecha_creacion": credito.fecha_creacion,
                "fecha_vencimiento": credito.fecha_vencimiento,
                "pagado": credito.pagado,
                "folio": credito.venta.folio if credito.venta else None,
                "abonos": abonos,
            })
            saldo += pendiente

        return {
            "saldo_pendiente": redondear_moneda(saldo),
            "creditos": resultado,
        }

    def obtener_saldo_cliente(self, cliente_id: int) -> Decimal:
        """Suma de los montos pendientes de los créditos activos del cliente."""
        db = next(get_db())
        try:
            pendientes = (
                db.query(Credito)
                .filter(Credito.cliente_id == cliente_id, Credito.pagado == False)
                .all()
            )
            return redondear_moneda(
                sum((Decimal(str(c.monto_pendiente)) for c in pendientes), Decimal("0"))
            )
        finally:
            db.close()

    def obtener_clientes_con_saldo(self):
        """Clientes con crédito pendiente, con su saldo total y último movimiento."""
        db = next(get_db())
        try:
            clientes = db.query(Cliente).filter(Cliente.activo == True).all()
            resultado = []
            for c in clientes:
                saldo = self._saldo_en_sesion(db, c.id)
                if saldo > 0:
                    resultado.append({
                        "cliente": c,
                        "saldo": saldo,
                    })
            # Ordenar por saldo descendente
            resultado.sort(key=lambda r: r["saldo"], reverse=True)
            return resultado
        finally:
            db.close()

    def _saldo_en_sesion(self, db, cliente_id: int) -> Decimal:
        pendientes = (
            db.query(Credito)
            .filter(Credito.cliente_id == cliente_id, Credito.pagado == False)
            .all()
        )
        return redondear_moneda(
            sum((Decimal(str(c.monto_pendiente)) for c in pendientes), Decimal("0"))
        )

    # ------------------------------------------------------------------
    # Creación de crédito (dentro de una transacción de venta)
    # ------------------------------------------------------------------

    def crear_credito(self, db, cliente_id: int, venta_id: int, monto) -> Credito:
        """Crear un crédito y actualizar el saldo del cliente.

        Se ejecuta dentro de la transacción de la venta (recibe la sesión ya
        abierta). Llama al final a ``db.commit()``.

        Raises:
            ValueError: Si el monto no es válido o el cliente no está activo.
        """
        monto_dec = redondear_moneda(Decimal(str(monto)))
        if monto_dec <= 0:
            raise ValueError("El monto del crédito debe ser mayor a cero.")

        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise ValueError("El cliente seleccionado no existe.")
        if not cliente.activo:
            raise ValueError("El cliente está inactivo.")

        # Verificar límite de crédito disponible (0 = sin límite)
        limite = Decimal(str(cliente.limite_credito or 0))
        saldo_actual = self._saldo_en_sesion(db, cliente_id)
        if limite > 0:
            disponible = redondear_moneda(limite - saldo_actual)
            if disponible < monto_dec:
                raise ValueError(
                    f"El cliente supera su límite de crédito.\n"
                    f"Disponible: {disponible} - Necesario: {monto_dec}"
                )

        credito = Credito(
            cliente_id=cliente_id,
            venta_id=venta_id,
            monto_original=monto_dec,
            monto_pendiente=monto_dec,
            pagado=False,
        )
        db.add(credito)
        db.flush()

        cliente.saldo_actual = redondear_moneda(saldo_actual + monto_dec)

        return credito

    # ------------------------------------------------------------------
    # Abonos (pagos parciales)
    # ------------------------------------------------------------------

    @requiere_permiso("administrar_fiados")
    def registrar_abono(
        self,
        cliente_id: int,
        credito_id: int,
        monto,
        usuario_id: int = None,
        notas: str = None,
    ) -> dict:
        """Registrar un abono a un crédito dentro de una transacción.

        Actualiza el monto pendiente del crédito, marca como pagado si queda
        en cero, ajusta el saldo del cliente y guarda el movimiento (abono).

        Raises:
            ValueError: Si el monto es inválido o el crédito no corresponde.
        """
        db = next(get_db())
        try:
            monto_dec = redondear_moneda(Decimal(str(monto)))
            if monto_dec <= 0:
                raise ValueError("El abono debe ser mayor a cero.")

            credito = (
                db.query(Credito)
                .filter(Credito.id == credito_id, Credito.cliente_id == cliente_id)
                .first()
            )
            if not credito:
                raise ValueError("El crédito seleccionado no existe para este cliente.")
            if credito.pagado:
                raise ValueError("Este crédito ya está completamente pagado.")

            pendiente = Decimal(str(credito.monto_pendiente))
            if monto_dec > pendiente:
                raise ValueError(
                    f"El abono no puede ser mayor al pendiente.\n"
                    f"Pendiente: {pendiente} - Abono: {monto_dec}"
                )

            if not usuario_id:
                usuario_id = self._obtener_usuario_id(db)

            # Registrar el movimiento (abono)
            db.add(Abono(
                credito_id=credito.id,
                usuario_id=usuario_id,
                monto=monto_dec,
                notas=notas,
            ))

            # Actualizar crédito
            nuevo_pendiente = redondear_moneda(pendiente - monto_dec)
            credito.monto_pendiente = nuevo_pendiente
            if nuevo_pendiente <= 0:
                credito.pagado = True
                credito.fecha_pago = datetime.now()
                # Al liquidar la deuda, la venta fiada pasa a completada
                if credito.venta_id:
                    venta = (
                        db.query(Venta)
                        .filter(Venta.id == credito.venta_id)
                        .first()
                    )
                    if venta and venta.estado == EstadoVentaEnum.FIADO:
                        venta.estado = EstadoVentaEnum.COMPLETADA

            # Ajustar saldo del cliente
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if cliente:
                cliente.saldo_actual = self._saldo_en_sesion(db, cliente_id)

            db.commit()

            # Auditoría (Fase 15)
            BitacoraService().registrar(
                usuario_id=usuario_id,
                accion="abono",
                detalle=f"Abono de {monto_dec} registrado al crédito {credito.id}",
            )

            return {
                "exito": True,
                "mensaje": (
                    f"Abono de {monto_dec} registrado.\n"
                    f"Pendiente del crédito: {nuevo_pendiente}"
                ),
            }
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo registrar el abono: {e}")
        finally:
            db.close()
