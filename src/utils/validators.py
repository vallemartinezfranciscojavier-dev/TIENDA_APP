"""
Validadores de entrada.
"""

import re
from typing import Optional


def validar_email(email: str) -> bool:
    """Validar formato de email."""
    if not email:
        return True  # Email es opcional
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validar_telefono(telefono: str) -> bool:
    """Validar formato de teléfono mexicano."""
    if not telefono:
        return True
    # Permitir: 10 dígitos, con o sin código de país
    pattern = r'^(\+52\s?)?(\d{2,3}[\s-]?)?\d{3,4}[\s-]?\d{4}$'
    return bool(re.match(pattern, telefono))


def validar_codigo_barras(codigo: str) -> bool:
    """Validar código de barras (EAN-13, UPC-A, etc.)."""
    if not codigo:
        return True
    # Solo dígitos, longitud común 8, 12, 13, 14
    return codigo.isdigit() and len(codigo) in [8, 12, 13, 14]


def validar_rfc(rfc: str) -> bool:
    """Validar RFC mexicano básico."""
    if not rfc:
        return True
    # RFC persona física: 13 caracteres, persona moral: 12
    pattern = r'^([A-ZÑ&]{3,4})(\d{6})([A-Z0-9]{3})$'
    return bool(re.match(pattern, rfc.upper()))


def validar_precio(precio: float) -> bool:
    """Validar que el precio sea positivo."""
    return precio >= 0


def validar_cantidad(cantidad: float) -> bool:
    """Validar que la cantidad sea positiva."""
    return cantidad > 0


def validar_porcentaje(porcentaje: float) -> bool:
    """Validar porcentaje (0-100)."""
    return 0 <= porcentaje <= 100