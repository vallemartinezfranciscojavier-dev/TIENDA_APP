"""Driver temporal: verificar arranque de la app en Fase 14 (permisos).

Monkeypatch de LoginDialog.exec para autenticar al admin real (iniciar_sesion
con u.rol enum) y aceptar, para que MainWindow se construya CON sesión activa.
Un watchdog imprime progreso a un archivo de log por si algo bloquea.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import QTimer

LOG = Path(__file__).resolve().parent / "data" / "_verif_f14_arranque.log"
LOG.parent.mkdir(exist_ok=True)


def log(msg):
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg, file=sys.stderr, flush=True)


from services.usuarios_service import UsuarioService
from services.sesion_service import iniciar_sesion, sesion_activa, obtener_rol
import main as m
from views.login import LoginDialog


def _autologin(self):
    u = UsuarioService().autenticar("admin", "admin123")
    if u is None:
        log("AUTOLOGIN: no encontró admin → forzar None")
        return QDialog.Rejected
    iniciar_sesion(u)
    log("AUTOLOGIN: sesión iniciada rol=" + str(obtener_rol()))
    return QDialog.Accepted


LoginDialog.exec = _autologin


# Instalar el check desde dentro del app (el loop ya corre cuando show() se ejecuta)
_show_original = m.MainWindow.show


def _show_con_check(self):
    _show_original(self)

    def _check():
        app = QApplication.instance()
        win = getattr(app, "_ventana_actual", None) if app else None
        estado = {
            "sesion_activa": sesion_activa(),
            "ventana_creada": win is not None,
            "ventana_visible": bool(win and win.isVisible()),
        }
        log("CHECK: " + repr(estado))
        if win is not None:
            from services.permisos_service import hay_permiso_actual
            log("CHECK: cancelar_ventas=" + str(hay_permiso_actual("cancelar_ventas")))
        QApplication.instance().quit()

    QTimer.singleShot(6000, _check)


m.MainWindow.show = _show_con_check

try:
    rc = m.main()
except SystemExit:
    rc = 0
log("MAIN_RC: " + str(rc))
sys.exit(rc)