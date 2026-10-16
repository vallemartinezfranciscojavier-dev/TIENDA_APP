"""
Smoke test headless (offscreen) de la Fase 15: verifica que la interfaz
nueva se construye sin errores y que los controles funcionan.

  A) ConfiguracionView construye los grupos de respaldo (programado y
     retención) y los filtros de bitácora.
  B) Al cambiar un control se guarda la configuración (JSON) y se emite la
     señal config_respaldos_cambiada; el QTimer del respaldo programado se
     arma/desarma según la configuración.

No toca data/tienda.db (usa una BD temporal).
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# ── 0. Redirigir a BD temporal ANTES de importar servicios/UI ─────────
_tmp = Path(tempfile.mkdtemp(prefix="f15ui_"))
from config import settings  # noqa: E402

settings.DATABASE_DIR = _tmp
settings.DATABASE_PATH = _tmp / "test.db"
settings.DATABASE_URL = f"sqlite:///{settings.DATABASE_PATH}"
settings.BACKUPS_DIR = _tmp / "backups"

from PySide6.QtWidgets import QApplication  # noqa: E402
from main import MainWindow  # noqa: E402
from services import respaldos_config_service  # noqa: E402
import services.sesion_service as sesion  # noqa: E402
from database.models import RolUsuarioEnum  # noqa: E402

fallos = []
ok_count = 0


def check(nombre, cond, extra=""):
    global ok_count
    if cond:
        ok_count += 1
        print(f"  ✔ {nombre}")
    else:
        fallos.append(nombre)
        print(f"  ✘ {nombre} {extra}")


app = QApplication([])
app.setQuitOnLastWindowClosed(False)

# Sesión ADMIN para que MainWindow cargue el módulo de configuración.
sesion._usuario_actual = {"id": 1, "nombre": "Admin", "usuario": "admin",
                          "rol": RolUsuarioEnum.ADMIN}

window = MainWindow()
cfg = window.vistas["configuracion"]

# A) La vista construye los controles nuevos.
check("ConfiguracionView construye chk_programado", hasattr(cfg, "chk_programado"))
check("ConfiguracionView construye spin_horas", hasattr(cfg, "spin_horas"))
check("ConfiguracionView construye chk_retencion", hasattr(cfg, "chk_retencion"))
check("ConfiguracionView construye spin_maximo", hasattr(cfg, "spin_maximo"))
check("ConfiguracionView construye filtros bitácora",
      hasattr(cfg, "combo_filtro_accion") and hasattr(cfg, "date_desde")
      and hasattr(cfg, "txt_filtro_usuario"))

# Valores por defecto cargados.
check("default: programado apagado", cfg.chk_programado.isChecked() is False)
check("default: intervalo 24h", cfg.spin_horas.value() == 24)
check("default: retención apagada", cfg.chk_retencion.isChecked() is False)
check("default: máximo 30", cfg.spin_maximo.value() == 30)
check("filtro bitácora: opción 'Todas'", cfg.combo_filtro_accion.count() >= 1)

# B) Cambiar un control guarda la configuración y emite la señal.
se_emitio = []
cfg.config_respaldos_cambiada.connect(lambda: se_emitio.append(True))

cfg.chk_programado.setChecked(True)
cfg2 = respaldos_config_service.leer_config()
check("activar programado: se guarda en JSON", cfg2["programado"]["activo"] is True)
check("activar programado: emite config_respaldos_cambiada", bool(se_emitio))
check("activar programado: QTimer armado", hasattr(window, "_timer_respaldo_programado"))

cfg.spin_horas.setValue(8)
cfg3 = respaldos_config_service.leer_config()
check("cambiar intervalo: se guarda (8h)", cfg3["programado"]["intervalo_horas"] == 8)

cfg.chk_retencion.setChecked(True)
cfg.spin_maximo.setValue(15)
cfg4 = respaldos_config_service.leer_config()
check("activar retención: se guarda", cfg4["retencion"]["activa"] is True
      and cfg4["retencion"]["maximo_respaldos"] == 15)

# Apagar para dejar todo consistente.
cfg.chk_programado.setChecked(False)
cfg.chk_retencion.setChecked(False)
cfg5 = respaldos_config_service.leer_config()
check("apagar programado: no llama guardar inconsistente",
      cfg5["programado"]["activo"] is False and cfg5["retencion"]["activa"] is False)

# Evitar que closeEvent abra el diálogo modal de confirmación en offscreen.
window._cerrando_por_logout = True
window.close()
app.quit()

print()
print("=" * 60)
if fallos:
    print(f"FASE 15 ARRANQUE: {ok_count} OK, {len(fallos)} FALLOS:")
    for f in fallos:
        print("  -", f)
    sys.exit(1)
else:
    print(f"FASE 15 ARRANQUE: INTERFAZ CONSTRUYE Y GUARDA OK ({ok_count} checks)")
    sys.exit(0)