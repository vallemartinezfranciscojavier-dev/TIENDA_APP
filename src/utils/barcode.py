"""
Utilidades para códigos de barras.
"""

import re
from typing import Optional


def generar_ean13(base: str = "") -> str:
    """
    Generar un EAN-13 válido.
    Los primeros 12 dígitos son el código, el 13 es dígito de control.
    """
    if not base:
        import random
        base = ''.join(str(random.randint(0, 9)) for _ in range(12))
    elif len(base) > 12:
        base = base[:12]
    elif len(base) < 12:
        base = base.zfill(12)

    # Calcular dígito de control EAN-13
    suma = 0
    for i, digito in enumerate(base):
        d = int(digito)
        if i % 2 == 0:
            suma += d
        else:
            suma += d * 3

    digito_control = (10 - (suma % 10)) % 10
    return base + str(digito_control)


def validar_ean13(codigo: str) -> bool:
    """Validar código EAN-13."""
    if not codigo or len(codigo) != 13 or not codigo.isdigit():
        return False

    suma = 0
    for i, digito in enumerate(codigo[:12]):
        d = int(digito)
        if i % 2 == 0:
            suma += d
        else:
            suma += d * 3

    digito_control = (10 - (suma % 10)) % 10
    return digito_control == int(codigo[12])


def validar_upca(codigo: str) -> bool:
    """Validar código UPC-A (12 dígitos)."""
    if not codigo or len(codigo) != 12 or not codigo.isdigit():
        return False

    # UPC-A usa el mismo algoritmo que EAN-13 pero con 11 dígitos base
    suma = 0
    for i, digito in enumerate(codigo[:11]):
        d = int(digito)
        if i % 2 == 0:
            suma += d * 3
        else:
            suma += d

    digito_control = (10 - (suma % 10)) % 10
    return digito_control == int(codigo[11])


def normalizar_codigo_barras(codigo: str) -> Optional[str]:
    """
    Normalizar código de barras quitando espacios y guiones.
    Retorna None si no es válido.
    """
    if not codigo:
        return None

    limpio = re.sub(r'[\s-]', '', codigo)

    # Validar longitudes comunes
    if len(limpio) in [8, 12, 13, 14] and limpio.isdigit():
        return limpio

    return None


def es_codigo_valido(codigo: str) -> bool:
    """Verificar si un código de barras es válido (cualquier formato común)."""
    normalizado = normalizar_codigo_barras(codigo)
    if not normalizado:
        return False

    if len(normalizado) == 13:
        return validar_ean13(normalizado)
    elif len(normalizado) == 12:
        return validar_upca(normalizado)
    elif len(normalizado) == 8:
        # EAN-8
        return True  # Validación simplificada
    elif len(normalizado) == 14:
        # GTIN-14
        return True  # Validación simplificada

    return False