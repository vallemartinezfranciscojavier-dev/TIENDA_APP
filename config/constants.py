"""
Constantes de la aplicación.
"""

# Tipos de venta
TIPO_VENTA_PIEZA = "pieza"
TIPO_VENTA_KILOGRAMO = "kilogramo"
TIPO_VENTA_GRAMOS = "gramos"
TIPO_VENTA_BOLSA = "bolsa"
TIPO_VENTA_UNIDAD_PERSONALIZADA = "unidad_personalizada"

TIPOS_VENTA = [
    TIPO_VENTA_PIEZA,
    TIPO_VENTA_KILOGRAMO,
    TIPO_VENTA_GRAMOS,
    TIPO_VENTA_BOLSA,
    TIPO_VENTA_UNIDAD_PERSONALIZADA,
]

# Unidades de medida
UNIDAD_KG = "kg"
UNIDAD_G = "g"
UNIDAD_PIEZA = "pza"
UNIDAD_BOLSA = "bolsa"

# Estados de venta
ESTADO_VENTA_PENDIENTE = "pendiente"
ESTADO_VENTA_COMPLETADA = "completada"
ESTADO_VENTA_CANCELADA = "cancelada"
ESTADO_VENTA_FIADO = "fiado"

# Tipos de movimiento de inventario
TIPO_MOVIMIENTO_ENTRADA = "entrada"
TIPO_MOVIMIENTO_SALIDA = "salida"
TIPO_MOVIMIENTO_AJUSTE = "ajuste"
TIPO_MOVIMIENTO_DEVOLUCION = "devolucion"

# Roles de usuario
ROL_ADMIN = "admin"
ROL_VENDEDOR = "vendedor"
ROL_CAJERO = "cajero"
ROL_ALMACEN = "almacen"

# Métodos de pago
METODO_EFECTIVO = "efectivo"
METODO_TARJETA = "tarjeta"
METODO_TRANSFERENCIA = "transferencia"
METODO_FIADO = "fiado"

METODOS_PAGO = [
    METODO_EFECTIVO,
    METODO_TARJETA,
    METODO_TRANSFERENCIA,
    METODO_FIADO,
]