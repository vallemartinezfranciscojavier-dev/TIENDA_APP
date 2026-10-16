"""
Servicio de respaldos y restauración (Fase 12 + Fase 15).

- Respaldo manual: copia consistente de la base de datos (API sqlite3.backup)
  a backups/backup_AAAA_MM_DD_HH_mm.db
- Respaldo automático diario: uno por día, al arrancar la aplicación, solo si
  aún no existe uno para hoy (backups/backup_AAAA_MM_DD.db)
- Respaldo programado (Fase 15): cada N horas mientras la app está abierta
  (backups/backup_programado_AAAA_MM_DD_HH_mm.db), sin duplicar dentro de la
  ventana del intervalo.
- Política de retención (Fase 15): si está activa, conserva solo los N
  respaldos más recientes. Por defecto INACTIVA: nada se borra automáticamente.
- Listado de respaldos con tamaño y fecha.
- Verificación de integridad (PRAGMA integrity_check).
- Restauración SEGURA mediante "bandera de restauración pendiente": la copia se
  aplica en el siguiente arranque, ANTES de que la aplicación conecte la base de
  datos, para nunca sobrescribir una BD que está en uso. Siempre se crea un
  respaldo preventivo del estado actual antes de restaurar.

Las operaciones importantes se registran en la bitácora (best-effort) para
auditoría.

Nota: las rutas se leen de `config.settings` en el momento de la llamada (no se
importan fijas) para poder redirigirlas en pruebas.
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from config import settings
from services import respaldos_config_service
from services.bitacora_service import BitacoraService
from services.seguridad_service import requiere_permiso

# Bitácora best-effort para auditoría (Fase 15).
_bitacora = BitacoraService()

# Bandera que indica una restauración pendiente de aplicar en el arranque.
FLAG_PATH = settings.DATABASE_DIR / "restaurar.flag"


def _formato_timestamp() -> str:
    """AAAA_MM_DD_HH_mm en hora local (igual que las fechas de ventas)."""
    return datetime.now().strftime("%Y_%m_%d_%H_%M")


def _formato_dia() -> str:
    return datetime.now().strftime("%Y_%m_%d")


def _crear_respaldo(ruta: Path) -> dict:
    """
    Copiar la base de datos actual a ``ruta`` con la API de respaldo de
    SQLite, que produce una copia consistente aunque haya lecturas/escrituras
    concurrentes de la aplicación.
    """
    try:
        origen = settings.DATABASE_PATH
        if not origen.exists():
            return {"exito": False, "mensaje": "No existe la base de datos."}

        ruta.parent.mkdir(parents=True, exist_ok=True)
        src = sqlite3.connect(str(origen))
        dst = sqlite3.connect(str(ruta))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

        return {
            "exito": True,
            "archivo": ruta.name,
            "ruta": str(ruta),
            "mensaje": f"Respaldo creado: {ruta.name}",
        }
    except Exception as e:
        return {"exito": False, "mensaje": f"Error al crear respaldo: {e}"}


def crear_respaldo_manual() -> dict:
    """Crear un respaldo con registro de hora: backup_AAAA_MM_DD_HH_mm.db."""
    nombre = f"backup_{_formato_timestamp()}.db"
    resultado = _crear_respaldo(settings.BACKUPS_DIR / nombre)
    if resultado["exito"]:
        _bitacora.registrar(accion="respaldo", detalle=f"Respaldo manual creado: {nombre}")
        aplicar_politica_retencion()
    return resultado


def crear_respaldo_diario() -> dict:
    """
    Respaldo automático diario: backup_AAAA_MM_DD.db.

    Si ya existe un respaldo para hoy no crea otro (evita duplicados al
    reabrir la aplicación en el mismo día).
    """
    nombre = f"backup_{_formato_dia()}.db"
    ruta = settings.BACKUPS_DIR / nombre
    if ruta.exists():
        return {
            "exito": True,
            "archivo": nombre,
            "ya_existia": True,
            "mensaje": f"Ya existe el respaldo de hoy: {nombre}",
        }
    resultado = _crear_respaldo(ruta)
    if resultado["exito"]:
        _bitacora.registrar(accion="respaldo", detalle=f"Respaldo diario automático: {nombre}")
        aplicar_politica_retencion()
    return resultado


def crear_respaldo_programado(intervalo_horas: int = 24) -> dict:
    """
    Respaldo del respaldo programado (Fase 15), con registro de hora.

    Se distingue con el prefijo ``backup_programado_``. No duplica dentro de la
    ventana del intervalo: si ya existe un respaldo programado más reciente que
    ``intervalo_horas`` horas, no crea otro (evita ráfagas si el temporizador
    se dispara de más).
    """
    ventana_segundos = max(1, int(intervalo_horas)) * 3600
    limite = datetime.now().timestamp() - ventana_segundos
    try:
        for archivo in settings.BACKUPS_DIR.glob("backup_programado_*.db"):
            try:
                if archivo.stat().st_mtime >= limite:
                    return {
                        "exito": True,
                        "archivo": archivo.name,
                        "ya_existia": True,
                        "mensaje": f"Ya existe un respaldo programado reciente: {archivo.name}",
                    }
            except OSError:
                continue
    except OSError:
        pass

    nombre = f"backup_programado_{_formato_timestamp()}.db"
    resultado = _crear_respaldo(settings.BACKUPS_DIR / nombre)
    if resultado["exito"]:
        _bitacora.registrar(accion="respaldo_programado", detalle=f"Respaldo programado: {nombre}")
        aplicar_politica_retencion()
    return resultado


def aplicar_politica_retencion() -> dict:
    """
    Aplicar la política de retención configurada (Fase 15).

    Solo actúa si la política está ACTIVA (por defecto inactiva: nada se borra
    automáticamente). Conserva los ``maximo_respaldos`` más recientes y elimina
    los respaldos más viejos que el límite. NUNCA toca los respaldos preventivos
    de restauración (``backup_pre_restauracion_*``), que se conservan siempre
    por seguridad.
    """
    retencion = respaldos_config_service.leer_config()["retencion"]
    if not retencion["activa"]:
        return {
            "exito": True,
            "aplicada": False,
            "eliminados": [],
            "mensaje": "Política de retención inactiva; no se eliminó nada.",
        }
    limite = retencion["maximo_respaldos"]
    candidatos = [
        Path(r["ruta"])
        for r in listar_respaldos()
        if not r["archivo"].startswith("backup_pre_restauracion_")
    ]
    candidatos.sort(key=lambda p: p.stat().st_mtime, reverse=True)  # más reciente primero
    excedentes = candidatos[limite:]
    eliminados = []
    for ruta in excedentes:
        try:
            ruta.unlink(missing_ok=True)
            eliminados.append(ruta.name)
        except OSError:
            continue
    if eliminados:
        _bitacora.registrar(
            accion="retencion",
            detalle=f"Retención: eliminados {len(eliminados)} respaldos viejos",
        )
    return {
        "exito": True,
        "aplicada": True,
        "eliminados": eliminados,
        "mensaje": f"Retención aplicada; se conservan {len(candidatos) - len(eliminados)} respaldos.",
    }


def listar_respaldos() -> list:
    """Respaldos disponibles (más recientes primero)."""
    respaldos = []
    directorio = settings.BACKUPS_DIR
    if directorio.exists():
        for archivo in directorio.glob("*.db"):
            try:
                stat = archivo.stat()
            except OSError:
                continue
            respaldos.append({
                "archivo": archivo.name,
                "ruta": str(archivo),
                "tamano_bytes": stat.st_size,
                "fecha": datetime.fromtimestamp(stat.st_mtime),
            })
    return sorted(respaldos, key=lambda r: r["archivo"], reverse=True)


def verificar_integridad(ruta: str | Path) -> dict:
    """Verificar que un archivo de respaldo esté íntegro (PRAGMA integrity_check)."""
    ruta = Path(ruta)
    if not ruta.exists():
        return {"exito": False, "resultado": "archivo inexistente"}
    try:
        conn = sqlite3.connect(str(ruta))
        try:
            fila = conn.execute("PRAGMA integrity_check").fetchone()
            resultado = fila[0] if fila else "desconocido"
            return {"exito": resultado == "ok", "resultado": resultado}
        finally:
            conn.close()
    except sqlite3.Error as e:
        return {"exito": False, "resultado": f"no es SQLite válido: {e}"}


@requiere_permiso("restaurar_respaldos")
def crear_flag_restauracion(nombre_respaldo: str) -> dict:
    """
    Programar la restauración de ``nombre_respaldo`` para el próximo arranque.

    Valida que el respaldo exista y pase la verificación de integridad antes
    de programar la restauración.
    """
    ruta = settings.BACKUPS_DIR / nombre_respaldo
    if not ruta.exists():
        return {"exito": False, "mensaje": "El respaldo seleccionado ya no existe."}

    integridad = verificar_integridad(ruta)
    if not integridad["exito"]:
        return {"exito": False, "mensaje": "El respaldo está dañado y no puede restaurarse."}

    try:
        FLAG_PATH.write_text(nombre_respaldo, encoding="utf-8")
    except OSError as e:
        return {"exito": False, "mensaje": f"No se pudo programar la restauración: {e}"}

    _bitacora.registrar(accion="restauracion", detalle=f"Restauración programada: {nombre_respaldo}")
    return {
        "exito": True,
        "mensaje": "Restauración programada. La aplicación se reiniciará para aplicarla.",
    }


def hay_restauracion_pendiente() -> bool:
    """Indica si existe una restauración programada por aplicar."""
    return FLAG_PATH.exists()


def aplicar_restauracion_pendiente() -> dict:
    """
    Aplicar la restauración pendiente (si existe).

    Debe llamarse al arrancar la aplicación, ANTES de conectar la base de
    datos. Restaura:
      1. Lee la bandera y valida el respaldo (existencia + integridad).
      2. Crea un respaldo preventivo del estado actual.
      3. Copia el respaldo sobre la base de datos.
      4. Borra la bandera.
    """
    if not hay_restauracion_pendiente():
        return {"exito": False, "mensaje": "No hay restauración pendiente."}

    nombre = ""
    try:
        nombre = FLAG_PATH.read_text(encoding="utf-8").strip()
    except OSError as e:
        return {"exito": False, "mensaje": f"No se pudo leer la restauración pendiente: {e}"}

    ruta_respaldo = settings.BACKUPS_DIR / nombre
    if not ruta_respaldo.exists():
        FLAG_PATH.unlink(missing_ok=True)
        _bitacora.registrar(
            accion="restauracion_cancelada",
            detalle=f"El respaldo a restaurar ya no existía: {nombre}",
        )
        return {
            "exito": False,
            "mensaje": "El respaldo a restaurar ya no existe. Se canceló la restauración.",
        }

    integridad = verificar_integridad(ruta_respaldo)
    if not integridad["exito"]:
        FLAG_PATH.unlink(missing_ok=True)
        _bitacora.registrar(
            accion="restauracion_cancelada",
            detalle=f"El respaldo a restaurar estaba dañado: {nombre}",
        )
        return {
            "exito": False,
            "mensaje": "El respaldo a restaurar está dañado. Se canceló la restauración.",
        }

    # Respaldo preventivo del estado actual antes de restaurar.
    preventivo = _crear_respaldo(
        settings.BACKUPS_DIR / f"backup_pre_restauracion_{_formato_timestamp()}.db"
    )
    if not preventivo["exito"]:
        return {
            "exito": False,
            "mensaje": "No se pudo crear el respaldo preventivo. "
                       "La restauración se canceló por seguridad.",
        }

    try:
        shutil.copy2(str(ruta_respaldo), settings.DATABASE_PATH)
    except OSError as e:
        return {"exito": False, "mensaje": f"Error al restaurar: {e}"}

    FLAG_PATH.unlink(missing_ok=True)

    _bitacora.registrar(
        accion="restauracion",
        detalle=f"BD restaurada desde '{nombre}' (preventivo: {preventivo.get('archivo')})",
    )
    return {
        "exito": True,
        "mensaje": f"Base de datos restaurada desde '{nombre}'.",
        "respaldo_seleccionado": nombre,
        "respaldo_preventivo": preventivo.get("archivo"),
    }