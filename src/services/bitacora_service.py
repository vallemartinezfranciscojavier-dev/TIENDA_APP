"""
Bitácora de actividades.
Registro básico de acciones importantes del sistema (inicio/cierre de
sesión, ventas, gestión de usuarios, etc.).
"""

from datetime import date, datetime, timedelta

from database.connection import get_db
from database.models import RegistroActividad, Usuario


class BitacoraService:
    """Registro y consulta de actividades importantes."""

    def registrar(self, usuario_id=None, accion="", detalle="", usuario_nombre=None):
        """
        Registrar una acción en la bitácora.

        El registro nunca debe impedir la operación principal: si falla,
        se ignora (best-effort).
        """
        db = next(get_db())
        try:
            nombre = (usuario_nombre or "").strip() or None
            if not nombre and usuario_id:
                u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
                nombre = u.nombre if u else None
            db.add(RegistroActividad(
                usuario_id=usuario_id,
                usuario_nombre=nombre,
                accion=(accion or "").strip()[:50],
                detalle=(detalle or "").strip() or None,
            ))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def acciones_distintas(self) -> list:
        """Acciones distintas registradas (para el filtro de la vista de bitácora)."""
        db = next(get_db())
        try:
            filas = (
                db.query(RegistroActividad.accion)
                .distinct()
                .order_by(RegistroActividad.accion.asc())
                .all()
            )
            return [a[0] for a in filas if a[0]]
        finally:
            db.close()

    def registrar_login(self, usuario_id=None, usuario_nombre=None):
        self.registrar(usuario_id, "login", "Inicio de sesión", usuario_nombre)

    def registrar_logout(self, usuario_id=None, usuario_nombre=None):
        self.registrar(usuario_id, "logout", "Cierre de sesión", usuario_nombre)

    def obtener_recientes(
        self,
        limite: int = 50,
        accion: str = None,
        texto_usuario: str = None,
        fecha_inicio=None,
        fecha_fin=None,
    ) -> list:
        """
        Actividades más recientes, con filtros opcionales (Fase 15):

        - ``accion``: coincide por substring con la acción (insensible a
          mayúsculas).
        - ``texto_usuario``: coincide por substring con el nombre de usuario.
        - ``fecha_inicio`` / ``fecha_fin``: rango de fechas inclusivo (date o
          datetime). Para un ``date`` final se incluye todo ese día.
        """
        db = next(get_db())
        try:
            q = db.query(RegistroActividad)
            accion = (accion or "").strip()
            if accion:
                q = q.filter(RegistroActividad.accion.ilike(f"%{accion}%"))
            texto_usuario = (texto_usuario or "").strip()
            if texto_usuario:
                q = q.filter(RegistroActividad.usuario_nombre.ilike(f"%{texto_usuario}%"))
            if fecha_inicio is not None:
                q = q.filter(RegistroActividad.fecha >= fecha_inicio)
            if fecha_fin is not None:
                if isinstance(fecha_fin, date) and not isinstance(fecha_fin, datetime):
                    q = q.filter(RegistroActividad.fecha < fecha_fin + timedelta(days=1))
                else:
                    q = q.filter(RegistroActividad.fecha <= fecha_fin)
            return (
                q.order_by(RegistroActividad.fecha.desc())
                .limit(limite)
                .all()
            )
        finally:
            db.close()