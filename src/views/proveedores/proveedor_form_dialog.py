"""
Diálogo para crear o editar un proveedor con todos los campos.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QLabel,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt

from services.proveedores_service import ProveedoresService


class ProveedorFormDialog(QDialog):
    """Diálogo para crear o editar un proveedor."""

    def __init__(self, parent=None, proveedor=None):
        super().__init__(parent)
        self.proveedor = proveedor
        self.es_edicion = proveedor is not None
        self.service = ProveedoresService()

        self.setObjectName("proveedorFormDialog")
        self.setWindowTitle("Editar Proveedor" if self.es_edicion else "Nuevo Proveedor")
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
        form.setSpacing(10)

        self.nombre_edit = QLineEdit(self)
        self.nombre_edit.setPlaceholderText("Ej: Distribuidora La Viga")
        self.nombre_edit.setMaxLength(200)
        form.addRow("Nombre *:", self.nombre_edit)

        self.contacto_edit = QLineEdit(self)
        self.contacto_edit.setPlaceholderText("Nombre de contacto (opcional)")
        self.contacto_edit.setMaxLength(100)
        form.addRow("Contacto:", self.contacto_edit)

        self.telefono_edit = QLineEdit(self)
        self.telefono_edit.setPlaceholderText("Teléfono (opcional)")
        self.telefono_edit.setMaxLength(20)
        form.addRow("Teléfono:", self.telefono_edit)

        self.email_edit = QLineEdit(self)
        self.email_edit.setPlaceholderText("Correo electrónico (opcional)")
        self.email_edit.setMaxLength(100)
        form.addRow("Email:", self.email_edit)

        self.direccion_edit = QLineEdit(self)
        self.direccion_edit.setPlaceholderText("Dirección (opcional)")
        self.direccion_edit.setMaxLength(250)
        form.addRow("Dirección:", self.direccion_edit)

        self.rfc_edit = QLineEdit(self)
        self.rfc_edit.setPlaceholderText("RFC (opcional)")
        self.rfc_edit.setMaxLength(13)
        form.addRow("RFC:", self.rfc_edit)

        self.activo_check = QCheckBox("Proveedor activo", self)
        if not self.es_edicion:
            self.activo_check.setChecked(True)
        form.addRow("Estado:", self.activo_check)

        layout.addLayout(form)

        # Botones
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
        """Rellenar el formulario con los valores del proveedor (edición)."""
        if not self.es_edicion:
            return

        p = self.proveedor
        self.nombre_edit.setText(p.nombre or "")
        self.contacto_edit.setText(p.contacto or "")
        self.telefono_edit.setText(p.telefono or "")
        self.email_edit.setText(p.email or "")
        self.direccion_edit.setText(p.direccion or "")
        self.rfc_edit.setText(p.rfc or "")
        self.activo_check.setChecked(bool(p.activo))

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------

    def _guardar(self):
        nombre = self.nombre_edit.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Datos inválidos", "El nombre del proveedor es obligatorio.")
            self.nombre_edit.setFocus()
            return

        datos = {
            "nombre": nombre,
            "contacto": self.contacto_edit.text().strip(),
            "telefono": self.telefono_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "direccion": self.direccion_edit.text().strip(),
            "rfc": self.rfc_edit.text().strip(),
            "activo": self.activo_check.isChecked(),
        }

        try:
            if self.es_edicion:
                self.service.actualizar(self.proveedor.id, datos)
            else:
                self.service.crear(datos)
        except ValueError as e:
            QMessageBox.warning(self, "Datos inválidos", str(e))
            return

        self.accept()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#proveedorFormDialog {
                background-color: #f5f5f5;
            }

            QLabel {
                color: #2c3e50;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
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