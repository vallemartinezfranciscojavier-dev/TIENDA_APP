"""
Enforcement de permisos en la capa de negocio (Fase 14).

Los permisos se aplican DENTRO de los servicios con el decorador
``requiere_permiso``, no solamente ocultando botones en la interfaz:

1. Si no hay una sesión iniciada, se bloquea la operación.
2. Si el rol del usuario actual no tiene la acción permitida, se bloquea.

Raises:
    PermisoDenegado: hereda de ValueError para que los manejadores de
    error existentes de las vistas lo muestren sin cambios.
"""

import functools

from services.permisos_service import tiene_permiso
from services.sesion_service import sesion_activa, obtener_rol


class PermisoDenegado(ValueError):
    """Operación bloqueada por seguridad (sin sesión o sin permiso)."""


def requiere_permiso(accion: str):
    """
    Decorador para métodos de servicio: exige sesión activa y permiso de
    acción para el rol actual antes de ejecutar el método.

    Uso:
        @requiere_permiso("realizar_ventas")
        def crear_venta(self, ...):
            ...

    Si no hay sesión, la operación devuelve un error sin requerir sesión.
    """

    def decorador(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not sesion_activa():
                raise PermisoDenegado(
                    "Debe iniciar sesión para realizar esta operación."
                )
            if not tiene_permiso(obtener_rol(), accion):
                raise PermisoDenegado(
                    "No tiene permiso para realizar esta operación."
                )
            return func(*args, **kwargs)

        return wrapper

    return decorador