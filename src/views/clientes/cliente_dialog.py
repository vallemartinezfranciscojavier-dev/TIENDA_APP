"""
Diálogo para crear o editar un cliente.
"""

from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt

from services.clientes_service import ClientesService
from utils.formatters import formatear_moneda


class ClienteDialog(QDialog):
    """Diálogo para crear o editar un cliente."""

    def __init__(self, cliente=None, parent=None):
        """
        Args:
            cliente: Si se pasa un cliente existente, el diálogo entra en
                     modo edición; de lo contrario es creación.
        """
        super().__init__(parent)
        self.cliente = cliente
        self.service = ClientesService()
        self._resultado = None

        es_edicion = cliente is not None
        self.setWindowTitle("Editar Cliente" if es_edicion else "Nuevo Cliente")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setObjectName("clienteDialog")

        self._setup_ui(es_edicion)
        self._aplicar_estilos()

        if es_edicion:
            self._cargar_datos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self, es_edicion: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        form = QFormLayout()
        form.setSpacing(12)

        self.nombre_edit = QLineEdit()
        self.nombre_edit.setPlaceholderText("Ej: Juan Pérez López")
        self.nombre_edit.setMaxLength(200)
        form.addRow("Nombre *:", self.nombre_edit)

        self.telefono_edit = QLineEdit()
        self.telefono_edit.setPlaceholderText("Ej: 5555123456")
        self.telefono_edit.setMaxLength(20)
        form.addRow("Teléfono:", self.telefono_edit)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Ej: correo@ejemplo.com (opcional)")
        self.email_edit.setMaxLength(100)
        form.addRow("Email:", self.email_edit)

        self.direccion_edit = QLineEdit()
        self.direccion_edit.setPlaceholderText("Dirección (opcional)")
        self.direccion_edit.setMaxLength(300)
        form.addRow("Dirección:", self.direccion_edit)

        self.limite_spin = QDoubleSpinBox()
        self.limite_spin.setPrefix("$ ")
        self.limite_spin.setDecimals(2)
        self.limite_spin.setRange(0, 999999.99)
        self.limite_spin.setSingleStep(100)
        self.limite_spin.setGroupSeparatorShown(True)
        self.limite_spin.setSpecialValueText("Sin límite")
        form.addRow("Límite de crédito:", self.limite_spin)

        layout.addLayout(form)

        # --- Nota para edición ---
        if es_edicion:
            lbl_saldo = QLabel(
                f"Saldo actual del cliente: {formatear_moneda(self.cliente.saldo_actual)}"
            )
            lbl_saldo.setObjectName("lblSaldo")
            lbl_saldo.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl_saldo)

        # --- Botones ---
        botones = QHBoxLayout()
        botones.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.clicked.connect(self.reject)

        btn_texto = "Actualizar" if es_edicion else "Crear Cliente"
        btn_guardar = QPushButton(btn_texto)
        btn_guardar.setObjectName("btnPrimario")
        btn_guardar.clicked.connect(self._guardar)

        botones.addWidget(btn_cancelar)
        botones.addWidget(btn_guardar)
        layout.addLayout(botones)

    def _cargar_datos(self):
        """Cargar los datos del cliente en el formulario (modo edición)."""
        c = self.cliente
        self.nombre_edit.setText(c.nombre or "")
        self.telefono_edit.setText(c.telefono or "")
        self.email_edit.setText(c.email or "")
        self.direccion_edit.setText(c.direccion or "")
        self.limite_spin.setValue(float(c.limite_credito or 0))

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------

    def _guardar(self):
        datos = {
            "nombre": self.nombre_edit.text(),
            "telefono": self.telefono_edit.text(),
            "email": self.email_edit.text(),
            "direccion": self.direccion_edit.text(),
            "limite_credito": self.limite_spin.value(),
        }

        try:
            if self.cliente:
                self._resultado = self.service.editar(self.cliente.id, datos)
            else:
                self._resultado = self.service.crear(datos)
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        self.accept()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#clienteDialog {
                background-color: #f5f5f5;
            }

            QLabel {
                color: #2c3e50;
                font-size: 13px;
            }

            #lblSaldo {
                color: #7f8c8d;
                font-size: 12px;
                font-style: italic;
            }

            QLineEdit, QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 7px 8px;
                font-size: 13px;
                min-height: 22px;
                color: #2c3e50;
            }

            QLineEdit:focus, QDoubleSpinBox:focus {
                border-color: #3498db;
            }

            QPushButton#btnPrimario {
                background-color: #3498db;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 22px;
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
                padding: 8px 22px;
                font-size: 13px;
            }

            QPushButton#btnSecundario:hover {
                background-color: #f1f3f5;
                border-color: #95a5a6;
            }
        """)
