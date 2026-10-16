"""
Configuración de respaldos (Fase 15).

Persiste en ``data/configuracion_respaldos.json`` dos ajustes del
administrador:

- **Respaldo programado**: si está activo y cada cuántas horas se ejecuta
  mientras la aplicación esté abierta.
- **Política de retención**: si está activa y cuántos respaldos como máximo se
  conservan. Por defecto la política está INACTIVA: nada se borra
  automáticamente (requisito de la Fase 15: no eliminar respaldos sin una
  política configurable).

La escritura es atómica (archivo temporal + replace) para no dejar el archivo
a medias, y las lecturas son tolerantes: si el archivo falta o está corrupto,
se devuelven los valores por defecto sin romper la aplicación.
"""

import json
import os
from pathlib import Path

from config import settings

# Valores por defecto (seguros: no programado, sin retención).
INTERVALO_HORAS_DEFECTO = 24
RETENCION_MAX_DEFECTO = 30


def _ruta_config() -> Path:
    """Archivo de configuración; desplazado con settings.DATABASE_DIR en pruebas."""
    return settings.DATABASE_DIR / "configuracion_respaldos.json"


def _valores_validos(intervalo_horas: int, maximo_respaldos: int) -> tuple:
    """Entender enteros en rango lógico, con valores por defecto si no aplican."""
    intervalo = int(intervalo_horas) if isinstance(intervalo_horas, (int, float)) else INTERVALO_HORAS_DEFECTO
    maximo = int(maximo_respaldos) if isinstance(maximo_respaldos, (int, float)) else RETENCION_MAX_DEFECTO
    if intervalo < 1:
        intervalo = INTERVALO_HORAS_DEFECTO
    if maximo < 1:
        maximo = RETENCION_MAX_DEFECTO
    return intervalo, maximo


def defaults() -> dict:
    """Configuración por defecto (sin programación, sin retención)."""
    return {
        "programado": {
            "activo": False,
            "intervalo_horas": INTERVALO_HORAS_DEFECTO,
        },
        "retencion": {
            "activa": False,
            "maximo_respaldos": RETENCION_MAX_DEFECTO,
        },
    }


def leer_config() -> dict:
    """Leer la configuración actual (o los valores por defecto)."""
    ruta = _ruta_config()
    cfg = defaults()
    try:
        if not ruta.exists():
            return cfg
        with ruta.open("r", encoding="utf-8") as f:
            datos = json.load(f)
        prog = datos.get("programado") or {}
        ret = datos.get("retencion") or {}
        cfg["programado"]["activo"] = bool(prog.get("activo", False))
        cfg["programado"]["intervalo_horas"], _ = _valores_validos(
            prog.get("intervalo_horas", INTERVALO_HORAS_DEFECTO), RETENCION_MAX_DEFECTO
        )
        cfg["retencion"]["activa"] = bool(ret.get("activa", False))
        _, cfg["retencion"]["maximo_respaldos"] = _valores_validos(
            INTERVALO_HORAS_DEFECTO, ret.get("maximo_respaldos", RETENCION_MAX_DEFECTO)
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        # Archivo ausente o corrupto: usar por defecto, sin romper la app.
        pass
    return cfg


def guardar_config(datos: dict) -> dict:
    """
    Guardar la configuración completa de forma atómica.

    Args:
        datos: dict con las llaves ``programado`` y ``retencion``
            (se toman las que existan; el resto queda como está).

    Returns:
        dict con "exito" y la configuración guardada.
    """
    cfg = leer_config()
    prog = datos.get("programado") or {}
    ret = datos.get("retencion") or {}
    intervalo, maximo = _valores_validos(
        prog.get("intervalo_horas", cfg["programado"]["intervalo_horas"]),
        ret.get("maximo_respaldos", cfg["retencion"]["maximo_respaldos"]),
    )
    cfg["programado"]["activo"] = bool(prog.get("activo", cfg["programado"]["activo"]))
    cfg["programado"]["intervalo_horas"] = intervalo
    cfg["retencion"]["activa"] = bool(ret.get("activa", cfg["retencion"]["activa"]))
    cfg["retencion"]["maximo_respaldos"] = maximo

    ruta = _ruta_config()
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = ruta.with_suffix(".json.tmp")
        with temporal.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(str(temporal), str(ruta))
        return {"exito": True, "config": cfg}
    except OSError as e:
        return {"exito": False, "mensaje": f"No se pudo guardar la configuración: {e}"}


def guardar_programado(activo: bool, intervalo_horas: int) -> dict:
    """Activar/desactivar el respaldo programado y fijar el intervalo."""
    return guardar_config({"programado": {"activo": activo, "intervalo_horas": intervalo_horas}})


def guardar_retencion(activa: bool, maximo_respaldos: int) -> dict:
    """Activar/desactivar la política de retención y fijar el límite."""
    return guardar_config({"retencion": {"activa": activa, "maximo_respaldos": maximo_respaldos}})