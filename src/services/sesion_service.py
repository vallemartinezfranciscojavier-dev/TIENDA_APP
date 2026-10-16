"""
Estado de sesión del usuario actual.

Se actualiza al iniciar sesión y se limpia al cerrar. Las capas de servicio
y de vista consultan aquí el usuario activo (id, nombre y rol) en lugar de
recibir credenciales del administrador por defecto.
"""

from database.models import RolUsuarioEnum

_usuario_actual = None


def iniciar_sesion(usuario) -> None:
    """Guardar el usuario autenticado en la sesión."""
    global _usuario_actual
    _usuario_actual = {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "usuario": usuario.usuario,
        "rol": usuario.rol,
    }


def cerrar_sesion() -> None:
    """Limpiar la sesión actual."""
    global _usuario_actual
    _usuario_actual = None


def sesion_activa() -> bool:
    """¿Hay un usuario con sesión iniciada?"""
    return _usuario_actual is not None


def obtener_usuario_id():
    """Id del usuario actual (None si no hay sesión)."""
    return _usuario_actual["id"] if _usuario_actual else None


def obtener_nombre() -> str:
    """Nombre del usuario actual."""
    return _usuario_actual["nombre"] if _usuario_actual else "Sin sesión"


def obtener_rol():
    """Rol del usuario actual."""
    return _usuario_actual["rol"] if _usuario_actual else None


def es_admin() -> bool:
    """¿El usuario actual es administrador?"""
    rol = obtener_rol()
    return rol == RolUsuarioEnum.ADMIN


def datos_sesion() -> dict:
    """Copia de los datos de la sesión para mostrar en la interfaz."""
    return dict(_usuario_actual) if _usuario_actual else {}