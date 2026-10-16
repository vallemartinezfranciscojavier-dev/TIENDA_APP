"""
Servicio de usuarios.
Autenticación, creación de usuarios, gestión de roles, contraseñas
y configuración del primer administrador.
"""

from sqlalchemy import func

from database.connection import get_db
from database.models import Usuario, RolUsuarioEnum
from services.seguridad_service import requiere_permiso
from utils.security import (
    hash_password,
    verify_password,
    validar_fortaleza_password,
)


class UsuarioService:
    """Lógica de negocio de los usuarios del sistema."""

    # ------------------------------------------------------------------
    # Primer usuario / autenticación
    # ------------------------------------------------------------------

    def existe_usuario(self) -> bool:
        """¿Hay al menos un usuario registrado?"""
        db = next(get_db())
        try:
            return (db.query(func.count(Usuario.id)).scalar() or 0) > 0
        finally:
            db.close()

    def crear_primer_admin(self, nombre: str, usuario: str, password: str) -> Usuario:
        """
        Crear el primer administrador del sistema (solo cuando no hay
        usuarios registrados). No permite credenciales universales.
        """
        db = next(get_db())
        try:
            if (db.query(func.count(Usuario.id)).scalar() or 0) > 0:
                raise ValueError(
                    "Ya existe un usuario registrado; no se puede crear el "
                    "administrador inicial."
                )

            nombre = (nombre or "").strip()
            usuario_login = (usuario or "").strip()
            if not nombre or not usuario_login:
                raise ValueError("El nombre y el usuario son obligatorios.")

            es_valida, advertencias = validar_fortaleza_password(password or "")
            if not es_valida:
                raise ValueError(
                    "La contraseña no cumple los requisitos:\n- "
                    + "\n- ".join(advertencias)
                )

            if len(usuario_login) < 3:
                raise ValueError("El nombre de usuario debe tener al menos 3 caracteres.")

            admin = Usuario(
                nombre=nombre,
                usuario=usuario_login,
                password_hash=hash_password(password),
                rol=RolUsuarioEnum.ADMIN,
                activo=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            return admin
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo crear el administrador: {e}")
        finally:
            db.close()

    def autenticar(self, usuario: str, password: str):
        """
        Validar credenciales.

        Returns:
            Usuario autenticado (activo) o None si las credenciales no
            coinciden.
        """
        usuario = (usuario or "").strip()
        if not usuario or not password:
            return None

        db = next(get_db())
        try:
            u = db.query(Usuario).filter(
                func.lower(Usuario.usuario) == usuario.lower()
            ).first()
            if not u or not u.activo:
                return None
            if verify_password(password, u.password_hash):
                return u
            return None
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Gestión de usuarios
    # ------------------------------------------------------------------

    def listar(self) -> list:
        """Todos los usuarios ordenados por nombre."""
        db = next(get_db())
        try:
            return db.query(Usuario).order_by(Usuario.nombre).all()
        finally:
            db.close()

    def obtener_por_id(self, usuario_id: int):
        db = next(get_db())
        try:
            return db.query(Usuario).filter(Usuario.id == usuario_id).first()
        finally:
            db.close()

    def _validar_nuevo(self, db, nombre, usuario_login, password, rol, usuario_id=None):
        """Validaciones compartidas al crear/editar un usuario."""
        nombre = (nombre or "").strip()
        usuario_login = (usuario_login or "").strip()

        if not nombre:
            raise ValueError("El nombre es obligatorio.")
        if len(usuario_login) < 3:
            raise ValueError("El nombre de usuario debe tener al menos 3 caracteres.")

        # Unicidad del nombre de usuario
        q = db.query(func.count(Usuario.id)).filter(
            func.lower(Usuario.usuario) == usuario_login.lower()
        )
        if usuario_id is not None:
            q = q.filter(Usuario.id != usuario_id)
        if (q.scalar() or 0) > 0:
            raise ValueError(f"El usuario '{usuario_login}' ya está registrado.")

        if password:
            es_valida, advertencias = validar_fortaleza_password(password)
            if not es_valida:
                raise ValueError(
                    "La contraseña no cumple los requisitos:\n- "
                    + "\n- ".join(advertencias)
                )

        if rol is not None and not isinstance(rol, RolUsuarioEnum):
            try:
                rol = RolUsuarioEnum(rol)
            except ValueError:
                raise ValueError("El rol indicado no es válido.")

        return nombre, usuario_login

    @requiere_permiso("administrar_usuarios")
    def crear_usuario(self, nombre, usuario, password, rol=None) -> Usuario:
        """
        Crear un empleado/usuario nuevo. La contraseña es obligatoria al
        crear (debe cumplir la política de fortaleza).
        """
        db = next(get_db())
        try:
            nombre, usuario_login = self._validar_nuevo(
                db, nombre, usuario, password, rol
            )
            if not password:
                raise ValueError("La contraseña es obligatoria al crear un usuario.")

            nuevo = Usuario(
                nombre=nombre,
                usuario=usuario_login,
                password_hash=hash_password(password),
                rol=rol if rol is not None else RolUsuarioEnum.VENDEDOR,
                activo=True,
            )
            db.add(nuevo)
            db.commit()
            db.refresh(nuevo)
            return nuevo
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo crear el usuario: {e}")
        finally:
            db.close()

    @requiere_permiso("administrar_usuarios")
    def actualizar_usuario(self, usuario_id: int, nombre=None, rol=None, activo=None) -> Usuario:
        """Actualizar datos de un usuario (nombre, rol, estado)."""
        db = next(get_db())
        try:
            u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
            if not u:
                raise ValueError("El usuario no existe.")

            if nombre is not None:
                nombre = (nombre or "").strip()
                if not nombre:
                    raise ValueError("El nombre no puede estar vacío.")
                u.nombre = nombre

            if rol is not None:
                if not isinstance(rol, RolUsuarioEnum):
                    try:
                        rol = RolUsuarioEnum(rol)
                    except ValueError:
                        raise ValueError("El rol indicado no es válido.")
                u.rol = rol

            if activo is not None:
                u.activo = bool(activo)

            db.commit()
            db.refresh(u)
            return u
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo actualizar el usuario: {e}")
        finally:
            db.close()

    @requiere_permiso("administrar_usuarios")
    def cambiar_password(self, usuario_id: int, nueva_password: str) -> Usuario:
        """Cambiar la contraseña de un usuario (validando fortaleza)."""
        db = next(get_db())
        try:
            u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
            if not u:
                raise ValueError("El usuario no existe.")

            es_valida, advertencias = validar_fortaleza_password(nueva_password or "")
            if not es_valida:
                raise ValueError(
                    "La contraseña no cumple los requisitos:\n- "
                    + "\n- ".join(advertencias)
                )

            u.password_hash = hash_password(nueva_password)
            db.commit()
            db.refresh(u)
            return u
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo cambiar la contraseña: {e}")
        finally:
            db.close()

    @requiere_permiso("administrar_usuarios")
    def alternar_activo(self, usuario_id: int) -> Usuario:
        """Activar o desactivar un usuario (no se elimina físicamente)."""
        db = next(get_db())
        try:
            u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
            if not u:
                raise ValueError("El usuario no existe.")
            if u.rol == RolUsuarioEnum.ADMIN and u.activo:
                # Evitar desactivar al último administrador activo.
                admins_activos = (
                    db.query(func.count(Usuario.id))
                    .filter(
                        Usuario.rol == RolUsuarioEnum.ADMIN,
                        Usuario.activo.is_(True),
                    )
                    .scalar()
                    or 0
                )
                if admins_activos <= 1:
                    raise ValueError(
                        "No se puede desactivar al último administrador activo."
                    )
            u.activo = not u.activo
            db.commit()
            db.refresh(u)
            return u
        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo cambiar el estado del usuario: {e}")
        finally:
            db.close()