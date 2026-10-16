"""
Diálogo de ajuste manual de inventario.
Permite indicar el nuevo stock y el motivo del ajuste.
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

from services.inventario_service import InventarioService
from utils.formatters import formatear_numero


class AjusteDialog(QDialog):
    """Diálogo para ajustar el stock de un producto."""

    def __init__(self, producto, parent=None):
        super().__init__(parent)
        self.producto = producto
        self.inventario_service = InventarioService()
        self.stock_actual = (
            Decimal(str(producto.inventario.cantidad))
            if producto.inventario is not None
            else Decimal("0")
        )

        self.setWindowTitle("Ajustar Inventario")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setObjectName("ajusteDialog")

        self._setup_ui()
        self._aplicar_estilos()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Producto y stock actual
        lbl_producto = QLabel(self.producto.nombre)
        lbl_producto.setObjectName("lblProductoAjuste")
        lbl_producto.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_producto)

        lbl_stock = QLabel(f"Stock anterior: {formatear_numero(self.stock_actual, 3)}")
        lbl_stock.setObjectName("lblStockAnterior")
        lbl_stock.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_stock)

        form = QFormLayout()
        form.setSpacing(10)

        self.stock_spin = QDoubleSpinBox()
        self.stock_spin.setDecimals(3)
        self.stock_spin.setRange(0, 999999.999)
        self.stock_spin.setSingleStep(0.100)
        self.stock_spin.setGroupSeparatorShown(True)
        self.stock_spin.setValue(float(self.stock_actual))
        form.addRow("Nuevo stock:", self.stock_spin)

        self.motivo_edit = QLineEdit()
        self.motivo_edit.setPlaceholderText("Ej: Merma, error de conteo, caducado...")
        self.motivo_edit.setMaxLength(200)
        form.addRow("Motivo *:", self.motivo_edit)

        layout.addLayout(form)

        botones = QHBoxLayout()
        botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnSecundario")
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Guardar Ajuste")
        self.btn_guardar.setObjectName("btnPrimario")
        self.btn_guardar.clicked.connect(self._guardar)

        botones.addWidget(self.btn_cancelar)
        botones.addWidget(self.btn_guardar)
        layout.addLayout(botones)

    def _guardar(self):
        nueva = Decimal(str(self.stock_spin.value()))
        motivo = self.motivo_edit.text().strip()

        if not motivo:
            QMessageBox.warning(
                self, "Motivo requerido", "Indica el motivo del ajuste."
            )
            self.motivo_edit.setFocus()
            return

        try:
            usuario_id = self.inventario_service.obtener_usuario_admin()
            resultado = self.inventario_service.ajustar_stock(
                self.producto.id,
                nueva,
                notas=motivo,
                usuario_id=usuario_id,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Ajuste inválido", str(e))
            return

        if not resultado["modificado"]:
            QMessageBox.information(self, "Sin cambios", resultado["mensaje"])
            return

        QMessageBox.information(self, "Ajuste registrado", resultado["mensaje"])
        self.accept()

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#ajusteDialog {
                background-color: #f5f5f5;
            }

            #lblProductoAjuste {
                color: #2c3e50;
                font-size: 16px;
                font-weight: 700;
            }

            #lblStockAnterior {
                color: #7f8c8d;
                font-size: 13px;
            }

            QLabel {
                color: #2c3e50;
                font-size: 13px;
            }

            QLineEdit, QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
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