"""Driver temporal: verificar arranque de la app + respaldo diario automático.

Monkeypatch de LoginDialog.exec para aceptar sin importar credenciales reales.
Al aceptar, mostrar_login construye MainWindow, que ejecuta _respaldo_diario_automatico.
"""
import sys

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import QTimer

import services.respaldos_service as rs
import main as m
from views.login import LoginDialog


def _autologin(self):
    # No necesita credenciales: main solo revisa dialog.exec() == Accepted.
    return QDialog.Accepted


LoginDialog.exec = _autologin

salida = {"corrio": False, "respaldos": []}


def _check():
    salida["respaldos"] = [x["archivo"] for x in rs.listar_respaldos()]
    print("RESPALDOS_AL_MOSTRAR:", salida["respaldos"])
    print("VENTANA_VISIBLE:", str(getattr(getattr(m.app, "_ventana_actual", None), "isVisible", lambda: False)()) if False else "n/a")
    salida["corrio"] = True
    QApplication.instance().quit()


QTimer.singleShot(7000, _check)
try:
    rc = m.main()
except SystemExit:
    rc = 0
print("MAIN_RC:", rc, "| CORRIO:", salida["corrio"])