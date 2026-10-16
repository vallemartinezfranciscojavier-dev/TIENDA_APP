"""
Diálogo para registrar un proveedor nuevo (alta rápida desde compras).
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QLabel,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt

from services.proveedores_service import ProveedoresService


class ProveedorDialog(QDialog):
    """Diálogo para crear un proveedor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = ProveedoresService()
        self.setWindowTitle("Nuevo Proveedor")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setObjectName("proveedorDialog")

        self._setup_ui()
        self._aplicar_estilos()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self.nombre_edit = QLineEdit()
        self.nombre_edit.setPlaceholderText("Ej: Distribuidora La Viga")
        self.nombre_edit.setMaxLength(200)
        form.addRow("Nombre *:", self.nombre_edit)

        self.contacto_edit = QLineEdit()
        self.contacto_edit.setPlaceholderText("Nombre de contacto (opcional)")
        self.contacto_edit.setMaxLength(100)
        form.addRow("Contacto:", self.contacto_edit)

        self.telefono_edit = QLineEdit()
        self.telefono_edit.setPlaceholderText("Teléfono (opcional)")
        self.telefono_edit.setMaxLength(20)
        form.addRow("Teléfono:", self.telefono_edit)

        layout.addLayout(form)

        botones = QHBoxLayout()
        botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnSecundario")
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.setObjectName("btnPrimario")
        self.btn_guardar.clicked.connect(self._guardar)

        botones.addWidget(self.btn_cancelar)
        botones.addWidget(self.btn_guardar)
        layout.addLayout(botones)

    def _guardar(self):
        nombre = self.nombre_edit.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Datos inválidos", "El nombre del proveedor es obligatorio.")
            self.nombre_edit.setFocus()
            return

        try:
            self.proveedor = self.service.crear({
                "nombre": nombre,
                "contacto": self.contacto_edit.text(),
                "telefono": self.telefono_edit.text(),
            })
        except ValueError as e:
            QMessageBox.warning(self, "Datos inválidos", str(e))
            return

        self.accept()

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#proveedorDialog {
                background-color: #f5f5f5;
            }

            QLabel {
                color: #2c3e50;
                font-size: 13px;
            }

            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                min-height: 22px;
                color: #2c3e50;
            }

            QLineEdit:focus {
                border-color: #3498db;
            }

            QPushButton#btnPrimario {
                background-color: #3498db;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton#btnPrimario:hover {
                background-color: #2980b9;
            }

            QPushButton#btnSecundario {
                background-color: #ffffff;
                color: #2c3e50;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
            }

            QPushButton#btnSecundario:hover {
                background-color: #f1f3f5;
                border-color: #95a5a6;
            }
        """)