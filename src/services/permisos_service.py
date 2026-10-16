"""
Permisos por rol de usuario.

Dos capas:
1. PERMISOS_MODULOS: qué módulos puede VER cada rol (sidebar / Fase 11).
2. PERMISOS_ACCION: qué ACCIONES puede EJECUTAR cada rol (Fase 14). Estos
   permisos se aplican en la capa de negocio (services) mediante el
   decorador requiere_permiso, no solo ocultando botones.

El rol VENDEDOR se presenta al usuario como "Empleado" (perfil de la Fase 11).
"""

from database.models import RolUsuarioEnum

# Módulos accesibles por rol (claves de navegación de la sidebar).
PERMISOS_MODULOS = {
    RolUsuarioEnum.ADMIN: {
        "dashboard", "punto_venta", "productos", "inventario",
        "clientes", "proveedores", "compras", "reportes",
        "corte_caja", "configuracion",
    },
    RolUsuarioEnum.VENDEDOR: {
        "dashboard", "punto_venta", "productos",
    },
    RolUsuarioEnum.CAJERO: {
        "dashboard", "punto_venta", "corte_caja",
    },
    RolUsuarioEnum.ALMACEN: {
        "dashboard", "productos", "inventario", "compras",
    },
}

# Etiquetas legibles para mostrar en la interfaz.
ETIQUETAS_ROL = {
    RolUsuarioEnum.ADMIN: "Administrador",
    RolUsuarioEnum.VENDEDOR: "Empleado",
    RolUsuarioEnum.CAJERO: "Cajero",
    RolUsuarioEnum.ALMACEN: "Almacén",
}

# Roles presentados al crear/editar un usuario (orden lógico).
ROLES_GESTIONABLES = [
    RolUsuarioEnum.ADMIN,
    RolUsuarioEnum.VENDEDOR,
    RolUsuarioEnum.CAJERO,
    RolUsuarioEnum.ALMACEN,
]

# ----------------------------------------------------------------------
# Acciones de negocio (Fase 14)
#
# Se ejecutan en la capa de servicios (decorador requiere_permiso) y
# bloquean la operación aunque se oculte el botón correspondiente.
# ----------------------------------------------------------------------

# Permisos que administra el sistema (catálogo de la Fase 14).
ACCIONES = [
    "realizar_ventas",
    "cancelar_ventas",
    "modificar_productos",
    "modificar_precios",
    "ajustar_inventario",
    "registrar_compras",
    "consultar_reportes",
    "administrar_clientes",
    "administrar_fiados",
    "realizar_cortes",
    "administrar_usuarios",
    "configurar_sistema",
    "restaurar_respaldos",
]

# Permisos de acción por rol.
# - ADMIN: acceso completo (todas las acciones).
# - VENDEDOR (Empleado): SOLO vender (decisión del usuario para la Fase 14).
# - CAJERO: ventas + cortes de caja.
# - ALMACEN: mercancía (productos, precios, inventario y compras).
PERMISOS_ACCION = {
    RolUsuarioEnum.ADMIN: set(ACCIONES),
    RolUsuarioEnum.VENDEDOR: {"realizar_ventas"},
    RolUsuarioEnum.CAJERO: {"realizar_ventas", "realizar_cortes"},
    RolUsuarioEnum.ALMACEN: {
        "registrar_compras",
        "modificar_productos",
        "modificar_precios",
        "ajustar_inventario",
    },
}


def modulos_permitidos(rol) -> set:
    """Conjunto de módulos permitidos para un rol."""
    return PERMISOS_MODULOS.get(rol, set())


def etiqueta_rol(rol) -> str:
    """Etiqueta legible de un rol."""
    return ETIQUETAS_ROL.get(rol, str(rol))


def es_admin(rol) -> bool:
    """¿El rol tiene acceso completo al sistema?"""
    return rol == RolUsuarioEnum.ADMIN


def puede_editar_productos(rol) -> bool:
    """¿El rol puede crear/editar/desactivar productos (no solo consultarlos)?"""
    return rol == RolUsuarioEnum.ADMIN


def tiene_permiso(rol, accion: str) -> bool:
    """¿El rol tiene permiso para ejecutar la acción indicada?

    Acciones posibles: ACCIONES (catálogo de la Fase 14). Si el rol o la
    acción no existen, el permiso se niega por seguridad.
    """
    return accion in PERMISOS_ACCION.get(rol, set())


def hay_permiso_actual(accion: str) -> bool:
    """¿El usuario con sesión tiene permiso para la acción? (para la UI)."""
    from services.sesion_service import obtener_rol

    return tiene_permiso(obtener_rol(), accion)