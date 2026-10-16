"""
Formateadores para presentación de datos.
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Union, Optional


def formatear_moneda(valor: Union[float, Decimal, int, None], simbolo: str = "$") -> str:
    """Formatear valor como moneda mexicana."""
    if valor is None:
        return f"{simbolo}0.00"
    d = Decimal(str(valor))
    return f"{simbolo}{d:,.2f}"


def formatear_numero(valor: Union[float, Decimal, int, None], decimales: int = 2) -> str:
    """Formatear número con separadores de miles."""
    if valor is None:
        return "0" + (".0" * decimales if decimales > 0 else "")
    d = Decimal(str(valor))
    fmt = f"{{:,.{decimales}f}}"
    return fmt.format(d)


def formatear_fecha(fecha: Union[datetime, date, str, None], formato: str = "%d/%m/%Y") -> str:
    """Formatear fecha."""
    if fecha is None:
        return ""
    if isinstance(fecha, str):
        try:
            fecha = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
        except ValueError:
            return fecha
    if isinstance(fecha, datetime):
        return fecha.strftime(formato)
    if isinstance(fecha, date):
        return fecha.strftime(formato)
    return str(fecha)


def formatear_fecha_hora(fecha: Union[datetime, str, None], formato: str = "%d/%m/%Y %H:%M") -> str:
    """Formatear fecha y hora."""
    return formatear_fecha(fecha, formato)


def formatear_hora(fecha: Union[datetime, str, None]) -> str:
    """Formatear solo la hora (HH:MM)."""
    return formatear_fecha(fecha, "%H:%M")


def formatear_peso(valor: Union[float, Decimal, int, None], unidad: str = "kg") -> str:
    """Formatear peso con unidad."""
    if valor is None:
        return f"0 {unidad}"
    d = Decimal(str(valor))
    if unidad == "kg":
        return f"{d:.3f} kg"
    elif unidad == "g":
        return f"{d:.0f} g"
    return f"{d} {unidad}"


def formatear_porcentaje(valor: Union[float, Decimal, int, None]) -> str:
    """Formatear porcentaje."""
    if valor is None:
        return "0%"
    d = Decimal(str(valor))
    return f"{d:.1f}%"


def formatear_folio(tipo: str, numero: int, ancho: int = 6) -> str:
    """Formatear folio (ej: VTA-000001, CMP-000001)."""
    return f"{tipo.upper()}-{numero:0{ancho}d}"


def truncar_texto(texto: str, max_longitud: int = 50, sufijo: str = "...") -> str:
    """Truncar texto largo."""
    if not texto or len(texto) <= max_longitud:
        return texto or ""
    return texto[:max_longitud - len(sufijo)] + sufijo