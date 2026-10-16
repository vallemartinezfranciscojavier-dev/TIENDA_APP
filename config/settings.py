"""
Configuración centralizada de la aplicación.
"""

import os
import sys
from pathlib import Path

# Directorio base del proyecto.
# - En desarrollo: la raíz del proyecto (config/ queda dentro).
# - En ejecutable PyInstaller: la carpeta del .exe, para que la base de datos
#   y los respaldos vivan junto a la aplicación y no en una carpeta temporal
#   (_MEIPASS) que se borra al cerrar.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

# Configuración de la aplicación
APP_NAME = "Sistema de Gestión Comercial"
APP_VERSION = "1.0.0"

# Configuración de base de datos
DATABASE_DIR = BASE_DIR / "data"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "tienda.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Directorio de respaldos
BACKUPS_DIR = BASE_DIR / "backups"
BACKUPS_DIR.mkdir(exist_ok=True)

# Configuración de interfaz
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 600

# Configuración de tema
THEME = "light"  # light, dark