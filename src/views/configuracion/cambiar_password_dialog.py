"""
Diálogo para cambiar la contraseña de un usuario (Fase 11).
Valida fortaleza y confirmación antes de guardar.
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

from services.usuarios_service import UsuarioService


class CambiarPasswordDialog(QDialog):
    """Diálogo para cambiar la contraseña de un usuario."""

    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)
        self.usuario = usuario
        self.service = UsuarioService()

        self.setObjectName("passwordDialog")
        self.setWindowTitle("Cambiar contraseña")
        self.setModal(True)
        self.setMinimumWidth(420)

        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        encabezado = QLabel(
            f"Usuario: {self.usuario.nombre}" if self.usuario else "Cambiar contraseña"
        )
        encabezado.setObjectName("titulo")
        layout.addWidget(encabezado)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setSpacing(10)

        self.nueva_edit = QLineEdit(self)
        self.nueva_edit.setEchoMode(QLineEdit.Password)
        self.nueva_edit.setMaxLength(64)
        self.nueva_edit.setPlaceholderText("Nueva contraseña")
        form.addRow("Nueva *:", self.nueva_edit)

        self.confirmar_edit = QLineEdit(self)
        self.confirmar_edit.setEchoMode(QLineEdit.Password)
        self.confirmar_edit.setMaxLength(64)
        self.confirmar_edit.setPlaceholderText("Repite la contraseña")
        self.confirmar_edit.returnPressed.connect(self._guardar)
        form.addRow("Confirmar *:", self.confirmar_edit)

        requisitos = QLabel(
            "Mínimo 8 caracteres con mayúscula, minúscula, número y símbolo."
        )
        requisitos.setObjectName("requisitos")
        form.addRow("", requisitos)

        layout.addLayout(form)

        botones = QHBoxLayout()
        botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar", self)
        self.btn_cancelar.setObjectName("btnSecundario")
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Guardar", self)
        self.btn_guardar.setObjectName("btnPrimario")
        self.btn_guardar.clicked.connect(self._guardar)

        botones.addWidget(self.btn_cancelar)
        botones.addWidget(self.btn_guardar)
        layout.addLayout(botones)

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------

    def _guardar(self):
        nueva = self.nueva_edit.text()
        confirmar = self.confirmar_edit.text()

        if nueva != confirmar:
            QMessageBox.warning(self, "Datos inválidos", "Las contraseñas no coinciden.")
            self.nueva_edit.clear()
            self.confirmar_edit.clear()
            self.nueva_edit.setFocus()
            return

        try:
            self.service.cambiar_password(self.usuario.id, nueva)
        except ValueError as e:
            QMessageBox.warning(self, "Datos inválidos", str(e))
            self.nueva_edit.clear()
            self.confirmar_edit.clear()
            self.nueva_edit.setFocus()
            return

        self.accept()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#passwordDialog {
                background-color: #f5f5f5;
            }

            QLabel#titulo {
                color: #2c3e50;
                font-size: 15px;
                font-weight: 600;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QLabel {
                color: #2c3e50;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QLabel#requisitos {
                color: #7f8c8d;
                font-size: 11px;
                font-style: italic;
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