"""
Cálculos comerciales.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union


def redondear_moneda(valor: Union[float, Decimal, int], decimales: int = 2) -> Decimal:
    """Redondear a decimales específicos para moneda."""
    d = Decimal(str(valor))
    quantize_exp = Decimal('0.1') ** decimales
    return d.quantize(quantize_exp, rounding=ROUND_HALF_UP)


def calcular_subtotal(cantidad: Union[float, Decimal], precio_unitario: Union[float, Decimal]) -> Decimal:
    """Calcular subtotal (cantidad × precio)."""
    return redondear_moneda(Decimal(str(cantidad)) * Decimal(str(precio_unitario)))


def calcular_descuento(subtotal: Union[float, Decimal], porcentaje_descuento: Union[float, Decimal]) -> Decimal:
    """Calcular descuento por porcentaje."""
    return redondear_moneda(Decimal(str(subtotal)) * Decimal(str(porcentaje_descuento)) / Decimal('100'))


def calcular_impuesto(subtotal: Union[float, Decimal], tasa_impuesto: Union[float, Decimal] = 16) -> Decimal:
    """Calcular impuesto (IVA 16% por defecto)."""
    return redondear_moneda(Decimal(str(subtotal)) * Decimal(str(tasa_impuesto)) / Decimal('100'))


def calcular_total(subtotal: Union[float, Decimal], descuento: Union[float, Decimal], impuestos: Union[float, Decimal]) -> Decimal:
    """Calcular total final."""
    return redondear_moneda(Decimal(str(subtotal)) - Decimal(str(descuento)) + Decimal(str(impuestos)))


def calcular_precio_por_peso(precio_por_kg: Union[float, Decimal], peso_kg: Union[float, Decimal]) -> Decimal:
    """Calcular precio por peso en kilogramos."""
    return redondear_moneda(Decimal(str(precio_por_kg)) * Decimal(str(peso_kg)))


def gramos_a_kilogramos(gramos: Union[float, Decimal]) -> Decimal:
    """Convertir gramos a kilogramos."""
    return redondear_moneda(Decimal(str(gramos)) / Decimal('1000'), 3)


def kilogramos_a_gramos(kilogramos: Union[float, Decimal]) -> Decimal:
    """Convertir kilogramos a gramos."""
    return redondear_moneda(Decimal(str(kilogramos)) * Decimal('1000'), 0)