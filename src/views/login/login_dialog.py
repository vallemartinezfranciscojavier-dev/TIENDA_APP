"""
Pantalla profesional de inicio de sesión (Fase 11).

Permite autenticar un usuario con usuario y contraseña. Solo se acepta el
diálogo si las credenciales son correctas y el usuario está activo.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import Qt

from config.settings import APP_NAME, APP_VERSION
from services.usuarios_service import UsuarioService
from services.bitacora_service import BitacoraService
from services.sesion_service import iniciar_sesion
from services.permisos_service import etiqueta_rol


class LoginDialog(QDialog):
    """Diálogo de inicio de sesión."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = UsuarioService()
        self.bitacora = BitacoraService()
        self.usuario_autenticado = None

        self.setObjectName("loginDialog")
        self.setWindowTitle("Iniciar sesión")
        self.setModal(True)
        self.setFixedSize(420, 480)

        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 36, 32, 28)
        layout.setSpacing(14)

        layout.addStretch(1)

        # Marca / nombre de la aplicación
        lbl_app = QLabel(APP_NAME)
        lbl_app.setObjectName("loginAppName")
        lbl_app.setAlignment(Qt.AlignCenter)
        lbl_app.setWordWrap(True)
        layout.addWidget(lbl_app)

        lbl_version = QLabel(f"Versión {APP_VERSION}")
        lbl_version.setObjectName("loginVersion")
        lbl_version.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_version)

        layout.addSpacing(22)

        self.usuario_edit = QLineEdit()
        self.usuario_edit.setObjectName("loginCampo")
        self.usuario_edit.setPlaceholderText("Usuario")
        self.usuario_edit.setMaxLength(60)
        self.usuario_edit.returnPressed.connect(self._validar)
        layout.addWidget(self.usuario_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setObjectName("loginCampo")
        self.password_edit.setPlaceholderText("Contraseña")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMaxLength(64)
        self.password_edit.returnPressed.connect(self._validar)
        layout.addWidget(self.password_edit)

        self.error_label = QLabel("")
        self.error_label.setObjectName("loginError")
        self.error_label.setWordWrap(True)
        self.error_label.setMinimumHeight(42)
        layout.addWidget(self.error_label)

        self.btn_entrar = QPushButton("Iniciar sesión")
        self.btn_entrar.setObjectName("btnEntrar")
        self.btn_entrar.setCursor(Qt.PointingHandCursor)
        self.btn_entrar.clicked.connect(self._validar)
        layout.addWidget(self.btn_entrar)

        layout.addStretch(2)

        footer = QLabel("Acceso restringido. Sistema de gestión comercial.")
        footer.setObjectName("loginFooter")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------

    def _validar(self):
        usuario = self.usuario_edit.text().strip()
        password = self.password_edit.text()

        if not usuario or not password:
            self._mostrar_error("Ingresa tu usuario y contraseña.")
            return

        # La validación nunca debe cerrar la app: ante un error transitorio
        # (p. ej. de base de datos) se muestra un mensaje y se conserva el
        # diálogo. El detalle queda registrado en data/errores.log.
        try:
            u = self.service.autenticar(usuario, password)
        except Exception:
            import traceback
            traceback.print_exc()
            self._mostrar_error(
                "No se pudo validar las credenciales. Inténtalo de nuevo."
            )
            return

        if u is None:
            self._mostrar_error("Usuario o contraseña incorrectos.")
            self.password_edit.clear()
            self.password_edit.setFocus()
            return

        # Credenciales válidas: iniciar sesión y registrar en bitácora.
        try:
            self.usuario_autenticado = u
            iniciar_sesion(u)
            self.bitacora.registrar_login(
                usuario_id=u.id, usuario_nombre=u.nombre
            )
        except Exception:
            import traceback
            traceback.print_exc()
            self._mostrar_error(
                "No se pudo abrir la sesión. Inténtalo de nuevo."
            )
            return
        self.aceptar()

    def _mostrar_error(self, mensaje: str):
        self.error_label.setText(mensaje)

    def aceptar(self) -> None:
        """Cerrar el diálogo con resultado aceptado."""
        self.accept()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#loginDialog {
                background-color: #eef1f5;
            }

            QLabel#loginAppName {
                color: #2c3e50;
                font-size: 22px;
                font-weight: 700;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QLabel#loginVersion {
                color: #7f8c8d;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QLineEdit#loginCampo {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
                color: #2c3e50;
                min-height: 24px;
            }

            QLineEdit#loginCampo:focus {
                border-color: #3498db;
            }

            QLabel#loginError {
                color: #c0392b;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding-top: 4px;
            }

            QPushButton#btnEntrar {
                background-color: #3498db;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 11px 16px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QPushButton#btnEntrar:hover {
                background-color: #2980b9;
            }

            QPushButton#btnEntrar:pressed {
                background-color: #21618c;
            }

            QLabel#loginFooter {
                color: #95a5a6;
                font-size: 11px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)