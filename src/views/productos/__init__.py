"""
Módulo de vistas de productos.
"""

from views.productos.productos_view import ProductosView
from views.productos.producto_dialog import ProductoDialog, etiqueta_tipo_venta

__all__ = [
    "ProductosView",
    "ProductoDialog",
    "etiqueta_tipo_venta",
]