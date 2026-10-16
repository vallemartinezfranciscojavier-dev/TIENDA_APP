"""
Configuración segura del primer administrador (Fase 11).

Se muestra únicamente cuando el sistema no tiene usuarios registrados.
No existen credenciales universales: el administrador define su propia
cuenta con una contraseña robusta desde el primer arranque.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QLabel,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt

from config.settings import APP_NAME
from services.usuarios_service import UsuarioService
from services.bitacora_service import BitacoraService
from services.sesion_service import iniciar_sesion


class PrimerAdminDialog(QDialog):
    """Diálogo de alta del primer administrador."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = UsuarioService()
        self.bitacora = BitacoraService()
        self.admin_creado = None

        self.setObjectName("primerAdminDialog")
        self.setWindowTitle("Configuración inicial")
        self.setModal(True)
        self.setFixedSize(460, 520)

        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 28)
        layout.setSpacing(14)

        lbl_titulo = QLabel("Configuración inicial")
        lbl_titulo.setObjectName("paTitulo")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_titulo)

        descripcion = QLabel(
            "El sistema no tiene usuarios registrados. "
            "Crea la cuenta de administrador para comenzar. "
            "Estas credenciales son exclusivas de este sistema; "
            "no se usa una contraseña genérica."
        )
        descripcion.setObjectName("paDescripcion")
        descripcion.setWordWrap(True)
        description_h = QVBoxLayout()
        description_h.setAlignment(Qt.AlignCenter)
        lbl_desc = QLabel(APP_NAME)
        lbl_desc.setObjectName("paApp")
        lbl_desc.setAlignment(Qt.AlignCenter)
        description_h.addWidget(lbl_desc)
        layout.addLayout(description_h)
        layout.addWidget(descripcion)

        layout.addSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setSpacing(12)

        self.nombre_edit = QLineEdit()
        self.nombre_edit.setObjectName("paCampo")
        self.nombre_edit.setPlaceholderText("Nombre completo (ej: Ana López)")
        self.nombre_edit.setMaxLength(100)
        form.addRow("Nombre *:", self.nombre_edit)

        self.usuario_edit = QLineEdit()
        self.usuario_edit.setObjectName("paCampo")
        self.usuario_edit.setPlaceholderText("Nombre de usuario (mínimo 3 letras)")
        self.usuario_edit.setMaxLength(60)
        form.addRow("Usuario *:", self.usuario_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setObjectName("paCampo")
        self.password_edit.setPlaceholderText("Contraseña segura")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMaxLength(64)
        form.addRow("Contraseña *:", self.password_edit)

        self.confirmar_edit = QLineEdit()
        self.confirmar_edit.setObjectName("paCampo")
        self.confirmar_edit.setPlaceholderText("Repite la contraseña")
        self.confirmar_edit.setEchoMode(QLineEdit.Password)
        self.confirmar_edit.setMaxLength(64)
        self.confirmar_edit.returnPressed.connect(self._guardar)
        form.addRow("Confirmar *:", self.confirmar_edit)

        layout.addLayout(form)

        requisitos = QLabel(
            "La contraseña debe tener mínimo 8 caracteres e incluir "
            "mayúscula, minúscula, número y símbolo (!@#$%^&*)."
        )
        requisitos.setObjectName("paRequisitos")
        requisitos.setWordWrap(True)
        layout.addWidget(requisitos)

        layout.addStretch(1)

        self.btn_crear = QPushButton("Crear administrador y continuar")
        self.btn_crear.setObjectName("btnCrear")
        self.btn_crear.setCursor(Qt.PointingHandCursor)
        self.btn_crear.clicked.connect(self._guardar)
        layout.addWidget(self.btn_crear)

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------

    def _guardar(self):
        nombre = self.nombre_edit.text().strip()
        usuario = self.usuario_edit.text().strip()
        password = self.password_edit.text()
        confirmar = self.confirmar_edit.text()

        if not nombre:
            self._error("El nombre es obligatorio.")
            self.nombre_edit.setFocus()
            return
        if len(usuario) < 3:
            self._error("El nombre de usuario debe tener al menos 3 caracteres.")
            self.usuario_edit.setFocus()
            return
        if password != confirmar:
            self._error("Las contraseñas no coinciden.")
            self.password_edit.clear()
            self.confirmar_edit.clear()
            self.password_edit.setFocus()
            return

        try:
            admin = self.service.crear_primer_admin(nombre, usuario, password)
        except ValueError as e:
            self._error(str(e))
            return

        # Sesión iniciada automáticamente con la cuenta recién creada.
        self.admin_creado = admin
        iniciar_sesion(admin)
        self.bitacora.registrar_login(
            usuario_id=admin.id, usuario_nombre=admin.nombre
        )
        self.accept()

    def _error(self, mensaje: str):
        QMessageBox.warning(self, "Datos inválidos", mensaje)

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#primerAdminDialog {
                background-color: #eef1f5;
            }

            QLabel#paTitulo {
                color: #2c3e50;
                font-size: 21px;
                font-weight: 700;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QLabel#paApp {
                color: #3498db;
                font-size: 13px;
                font-weight: 600;
                font-family: 'Segoe UI', Arial, sans-serif;
                margin-top: 4px;
            }

            QLabel#paDescripcion {
                color: #5d6d7e;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QLabel#paRequisitos {
                color: #7f8c8d;
                font-size: 11px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QLineEdit#paCampo {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 6px;
                padding: 9px 11px;
                font-size: 13px;
                color: #2c3e50;
                min-height: 22px;
            }

            QLineEdit#paCampo:focus {
                border-color: #3498db;
            }

            QPushButton#btnCrear {
                background-color: #3498db;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 11px 16px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QPushButton#btnCrear:hover {
                background-color: #2980b9;
            }

            QPushButton#btnCrear:pressed {
                background-color: #21618c;
            }
        """)