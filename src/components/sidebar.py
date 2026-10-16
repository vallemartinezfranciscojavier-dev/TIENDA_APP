"""
Sidebar de navegación principal.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class Sidebar(QWidget):
    """Sidebar de navegación lateral."""

    navegacion_cambiada = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setObjectName("sidebar")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo / Título
        logo_frame = QFrame()
        logo_frame.setFixedHeight(80)
        logo_frame.setObjectName("logoFrame")
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel("SISTEMA DE\nGESTIÓN COMERCIAL")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setWordWrap(True)
        logo_label.setObjectName("logoLabel")
        logo_layout.addWidget(logo_label)

        layout.addWidget(logo_frame)

        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("separator")
        layout.addWidget(separator)

        # Botones de navegación
        self.botones = {}
        nav_items = [
            ("dashboard", "Dashboard"),
            ("punto_venta", "Punto de Venta"),
            ("productos", "Productos"),
            ("inventario", "Inventario"),
            ("clientes", "Clientes"),
            ("proveedores", "Proveedores"),
            ("compras", "Compras"),
            ("reportes", "Reportes"),
            ("corte_caja", "Corte de Caja"),
            ("configuracion", "Configuración"),
        ]

        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._on_nav_click(k))
            self.botones[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Versión
        version_label = QLabel("v1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setObjectName("versionLabel")
        layout.addWidget(version_label)

        # Seleccionar dashboard por defecto
        self.botones["dashboard"].setChecked(True)

    def aplicar_permisos(self, modulos: set):
        """
        Ocultar los módulos que el rol no tiene permitido ver (Fase 11).
        ``modulos`` es un conjunto con las claves permitidas.
        """
        visibles = []
        for key, btn in self.botones.items():
            permitido = key in modulos
            btn.setVisible(permitido)
            if permitido:
                visibles.append(key)

        # Si el módulo actualmente marcado ya no es visible, regresar al dashboard.
        if not any(btn.isChecked() and btn.isVisible() for btn in self.botones.values()):
            self._on_nav_click("dashboard" if "dashboard" in visibles else visibles[0])

    def _on_nav_click(self, key: str):
        for k, btn in self.botones.items():
            btn.setChecked(k == key)
        self.navegacion_cambiada.emit(key)