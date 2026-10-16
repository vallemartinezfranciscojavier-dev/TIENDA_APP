"""
Diálogo para crear o editar un usuario del sistema (Fase 11).

Al crear exige una contraseña robusta. Al editar no se solicita
contraseña (se cambia aparte con un diálogo específico).
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QLabel,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt

from services.usuarios_service import UsuarioService
from services.permisos_service import ROLES_GESTIONABLES, etiqueta_rol


class UsuarioDialog(QDialog):
    """Diálogo para crear o editar un usuario."""

    def __init__(self, parent=None, usuario=None, es_primer_admin: bool = False):
        super().__init__(parent)
        self.usuario = usuario
        self.es_edicion = usuario is not None
        self.service = UsuarioService()

        self.setObjectName("usuarioDialog")
        self.setWindowTitle("Editar Usuario" if self.es_edicion else "Nuevo Usuario")
        self.setModal(True)
        self.setMinimumWidth(480)

        self._setup_ui()
        self._aplicar_estilos()
        self._cargar_datos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setSpacing(10)

        self.nombre_edit = QLineEdit(self)
        self.nombre_edit.setPlaceholderText("Nombre completo")
        self.nombre_edit.setMaxLength(100)
        form.addRow("Nombre *:", self.nombre_edit)

        self.usuario_edit = QLineEdit(self)
        self.usuario_edit.setPlaceholderText("Nombre de usuario")
        self.usuario_edit.setMaxLength(60)
        form.addRow("Usuario *:", self.usuario_edit)

        self.rol_combo = QComboBox(self)
        for rol in ROLES_GESTIONABLES:
            self.rol_combo.addItem(etiqueta_rol(rol), rol)
        form.addRow("Rol:", self.rol_combo)

        if self.es_edicion:
            self.activo_check = QCheckBox("Usuario activo", self)
            form.addRow("Estado:", self.activo_check)

            # Nota de contraseña
            nota = QLabel("La contraseña se cambia por separado.")
            nota.setObjectName("notaPassword")
            form.addRow("", nota)
        else:
            self.password_edit = QLineEdit(self)
            self.password_edit.setPlaceholderText("Contraseña")
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.password_edit.setMaxLength(64)
            form.addRow("Contraseña *:", self.password_edit)

            self.confirmar_edit = QLineEdit(self)
            self.confirmar_edit.setPlaceholderText("Repite la contraseña")
            self.confirmar_edit.setEchoMode(QLineEdit.Password)
            self.confirmar_edit.setMaxLength(64)
            self.confirmar_edit.returnPressed.connect(self._guardar)
            form.addRow("Confirmar *:", self.confirmar_edit)

            requisitos = QLabel(
                "Mínimo 8 caracteres con mayúscula, minúscula, número y símbolo."
            )
            requisitos.setObjectName("requisitosPassword")
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
    # Datos
    # ------------------------------------------------------------------

    def _cargar_datos(self):
        """Rellenar el formulario con los valores del usuario (edición)."""
        if not self.es_edicion:
            return

        u = self.usuario
        self.nombre_edit.setText(u.nombre or "")
        self.usuario_edit.setText(u.usuario or "")
        idx = self.rol_combo.findData(u.rol)
        if idx >= 0:
            self.rol_combo.setCurrentIndex(idx)
        self.activo_check.setChecked(bool(u.activo))

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------

    def _guardar(self):
        nombre = self.nombre_edit.text().strip()
        usuario = self.usuario_edit.text().strip()
        rol = self.rol_combo.currentData()

        if not nombre:
            QMessageBox.warning(self, "Datos inválidos", "El nombre es obligatorio.")
            self.nombre_edit.setFocus()
            return
        if len(usuario) < 3:
            QMessageBox.warning(
                self, "Datos inválidos",
                "El nombre de usuario debe tener al menos 3 caracteres.",
            )
            self.usuario_edit.setFocus()
            return

        try:
            if self.es_edicion:
                self.service.actualizar_usuario(
                    self.usuario.id,
                    nombre=nombre,
                    rol=rol,
                    activo=self.activo_check.isChecked(),
                )
            else:
                if not self.password_edit.text():
                    QMessageBox.warning(
                        self, "Datos inválidos", "La contraseña es obligatoria."
                    )
                    self.password_edit.setFocus()
                    return
                if self.password_edit.text() != self.confirmar_edit.text():
                    QMessageBox.warning(
                        self, "Datos inválidos", "Las contraseñas no coinciden."
                    )
                    self.password_edit.clear()
                    self.confirmar_edit.clear()
                    self.password_edit.setFocus()
                    return
                self.service.crear_usuario(
                    nombre, usuario, self.password_edit.text(), rol=rol
                )
        except ValueError as e:
            QMessageBox.warning(self, "Datos inválidos", str(e))
            return

        self.accept()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#usuarioDialog {
                background-color: #f5f5f5;
            }

            QLabel {
                color: #2c3e50;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QLabel#notaPassword, QLabel#requisitosPassword {
                color: #7f8c8d;
                font-size: 11px;
                font-style: italic;
            }

            QLineEdit, QComboBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                min-height: 22px;
                color: #2c3e50;
            }

            QLineEdit:focus, QComboBox:focus {
                border-color: #3498db;
            }

            QComboBox QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #3498db;
                selection-color: #ffffff;
            }

            QCheckBox {
                color: #2c3e50;
                font-size: 13px;
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