"""
Navbar superior.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class Navbar(QWidget):
    """Barra de navegación superior."""

    logout_solicitado = Signal()
    usuario_cambiado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setObjectName("navbar")
        self.usuario_actual = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Título de la sección actual
        self.titulo_label = QLabel("Dashboard")
        self.titulo_label.setObjectName("tituloLabel")
        layout.addWidget(self.titulo_label)

        layout.addStretch()

        # Usuario actual
        self.usuario_label = QLabel("Usuario: No identificado")
        self.usuario_label.setObjectName("usuarioLabel")
        layout.addWidget(self.usuario_label)

        # Botón cerrar sesión
        self.btn_logout = QPushButton("Cerrar Sesión")
        self.btn_logout.setObjectName("logoutButton")
        self.btn_logout.clicked.connect(self.logout_solicitado.emit)
        layout.addWidget(self.btn_logout)

    def establecer_titulo(self, titulo: str):
        self.titulo_label.setText(titulo)

    def establecer_usuario(self, nombre: str, rol: str):
        self.usuario_actual = {"nombre": nombre, "rol": rol}
        self.usuario_label.setText(f"Usuario: {nombre} ({rol})")