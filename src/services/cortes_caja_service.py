"""
Servicio de corte de caja.
Controla la apertura de caja, el resumen de ventas esperadas por método de
pago, el cierre con diferencia y la validación de cortes duplicados.
"""

from decimal import Decimal
from datetime import datetime, date, time

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from database.connection import get_db
from database.models import (
    CorteCaja,
    Venta,
    MetodoPagoEnum,
    EstadoVentaEnum,
)
from services.bitacora_service import BitacoraService
from services.sesion_service import obtener_usuario_id
from services.seguridad_service import requiere_permiso
from utils.calculations import redondear_moneda


class CortesCajaService:
    """Lógica de negocio para el control diario de caja."""

    # Métodos que participan en el corte (el fiado queda pendiente)
    METODOS_CORTE = [
        (MetodoPagoEnum.EFECTIVO, "Efectivo"),
        (MetodoPagoEnum.TARJETA, "Tarjeta"),
        (MetodoPagoEnum.TRANSFERENCIA, "Transferencia"),
    ]

    def _obtener_usuario_id(self, db) -> int:
        """Id del usuario de la sesión activa (Fase 11)."""
        usuario_id = obtener_usuario_id()
        if usuario_id is None:
            raise ValueError("No hay una sesión de usuario activa.")
        return usuario_id

    def _condicion_ventas_corte(self, corte):
        """
        Condición SQL de las ventas que pertenecen al corte.

        Incluye las ventas ligadas al corte, más las ventas de efectivo/
        tarjeta/transferencia registradas a partir de la apertura que aún
        no están ligadas a ningún otro corte.
        """
        desde = self._fecha_desde_para(corte)
        from sqlalchemy import and_, or_
        return (
            Venta.estado == EstadoVentaEnum.COMPLETADA,
            Venta.metodo_pago.in_([mp for mp, _ in self.METODOS_CORTE]),
            or_(
                Venta.corte_caja_id == corte.id,
                and_(
                    Venta.corte_caja_id.is_(None),
                    Venta.fecha >= desde,
                ),
            ),
        )

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def obtener_corte_abierto(self):
        """El corte de caja actualmente abierto (cerrado=False) o None."""
        db = next(get_db())
        try:
            return (
                db.query(CorteCaja)
                .filter(CorteCaja.cerrado.is_(False))
                .first()
            )
        finally:
            db.close()

    def obtener_cortes(self, limite: int = 10):
        """Últimos cortes registrados, del más reciente al más antiguo."""
        db = next(get_db())
        try:
            return (
                db.query(CorteCaja)
                .options(joinedload(CorteCaja.usuario))
                .order_by(CorteCaja.fecha_cierre.desc().nullslast())
                .limit(limite)
                .all()
            )
        finally:
            db.close()

    def existe_corte_cerrado_hoy(self, exclude_id=None) -> bool:
        """¿Ya existe un corte cerrado el día de hoy? (para evitar duplicados)."""
        db = next(get_db())
        try:
            inicio = datetime.combine(date.today(), time.min)
            q = db.query(func.count(CorteCaja.id)).filter(
                CorteCaja.fecha_cierre >= inicio,
                CorteCaja.cerrado.is_(True),
            )
            if exclude_id:
                q = q.filter(CorteCaja.id != exclude_id)
            return (q.scalar() or 0) > 0
        finally:
            db.close()

    def _fecha_desde_para(self, corte) -> datetime:
        """Inicio del periodo del corte (su apertura, o el día si no hay)."""
        inicio_dia = datetime.combine(date.today(), time.min)
        if corte is not None and corte.fecha_apertura is not None:
            return corte.fecha_apertura
        return inicio_dia

    # ------------------------------------------------------------------
    # Apertura
    # ------------------------------------------------------------------

    @requiere_permiso("realizar_cortes")
    def abrir_corte(self, monto_inicial=0, usuario_id=None):
        """
        Abrir un corte de caja (solo uno a la vez).

        Si ya existe un corte abierto, lo devuelve sin crear otro. La vista
        es la encargada de pedir confirmación cuando ya existe un corte
        cerrado el mismo periodo (validación de duplicados).
        """
        db = next(get_db())
        try:
            existente = (
                db.query(CorteCaja)
                .filter(CorteCaja.cerrado.is_(False))
                .first()
            )
            if existente:
                return existente

            inicial = Decimal(str(monto_inicial or 0))
            if inicial < 0:
                raise ValueError("El monto inicial no puede ser negativo.")

            corte = CorteCaja(
                usuario_id=usuario_id if usuario_id is not None else self._obtener_usuario_id(db),
                monto_inicial=inicial,
            )
            db.add(corte)
            db.commit()
            db.refresh(corte)
            # Auditoría (Fase 15)
            BitacoraService().registrar(
                usuario_id=corte.usuario_id,
                accion="corte_abierto",
                detalle=f"Corte de caja abierto (monto inicial {inicial})",
            )
            return corte
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo abrir la caja: {e}")
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Resumen de ventas esperadas
    # ------------------------------------------------------------------

    def obtener_resumen(self, corte):
        """
        Monto esperado por método de pago para el corte.

        Returns:
            dict {MetodoPagoEnum: Decimal} con las ventas completadas
            de efectivo, tarjeta y transferencia del periodo.
        """
        if corte is None:
            return {mp: Decimal("0") for mp, _ in self.METODOS_CORTE}

        db = next(get_db())
        try:
            filtros = self._condicion_ventas_corte(corte)
            filas = (
                db.query(Venta.metodo_pago, func.coalesce(func.sum(Venta.total), 0))
                .filter(*filtros)
                .group_by(Venta.metodo_pago)
                .all()
            )
            resumen = {mp: Decimal("0") for mp, _ in self.METODOS_CORTE}
            for metodo, total in filas:
                resumen[metodo] = redondear_moneda(total)
            return resumen
        finally:
            db.close()

    def total_esperado(self, resumen) -> Decimal:
        """Suma del total esperado del periodo."""
        return redondear_moneda(sum(resumen.values(), Decimal("0")))

    # ------------------------------------------------------------------
    # Cierre
    # ------------------------------------------------------------------

    @requiere_permiso("realizar_cortes")
    def cerrar_corte(self, monto_final_real, observaciones=None):
        """
        Cerrar el corte abierto actual.

        Calcula el total esperado del sistema, lo compara contra el dinero
        real contado y guarda la diferencia junto con las observaciones.

        Args:
            monto_final_real: Dinero físico contado por el encargado.
            observaciones: Notas opcionales sobre el corte.

        Returns:
            CorteCaja cerrado.

        Raises:
            ValueError: Si no hay caja abierta o el monto es inválido.
        """
        db = next(get_db())
        try:
            corte = (
                db.query(CorteCaja)
                .filter(CorteCaja.cerrado.is_(False))
                .first()
            )
            if not corte:
                raise ValueError("No hay una caja abierta para cerrar.")

            real = Decimal(str(monto_final_real or 0))
            if real < 0:
                raise ValueError("El dinero contado no puede ser negativo.")

            esperado = (
                db.query(func.coalesce(func.sum(Venta.total), 0))
                .filter(*self._condicion_ventas_corte(corte))
                .scalar()
            )
            esperado = redondear_moneda(esperado or 0)
            diferencia = redondear_moneda(real - esperado)

            corte.monto_final_sistema = esperado
            corte.monto_final_real = real
            corte.diferencia = diferencia
            corte.observaciones = (observaciones or "").strip() or None
            corte.fecha_cierre = datetime.now()
            corte.cerrado = True

            db.commit()
            db.refresh(corte)
            # Auditoría (Fase 15)
            BitacoraService().registrar(
                usuario_id=corte.usuario_id,
                accion="corte_cerrado",
                detalle=(
                    f"Corte cerrado: esperado {esperado}, real {real}, "
                    f"diferencia {diferencia}"
                ),
            )
            return corte
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo cerrar la caja: {e}")
        finally:
            db.close()