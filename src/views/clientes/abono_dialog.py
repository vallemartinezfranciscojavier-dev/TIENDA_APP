"""
Diálogo para registrar un abono (pago parcial) a un crédito de un cliente.
"""

from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QLabel,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt

from services.creditos_service import CreditosService
from utils.formatters import formatear_moneda


class AbonoDialog(QDialog):
    """Diálogo para registrar un abono a un crédito pendiente."""

    def __init__(self, cliente, creditos_pendientes, saldo_total, parent=None):
        """
        Args:
            cliente: Cliente al que se le registra el abono.
            creditos_pendientes: Lista de créditos (Credito) sin pagar.
            saldo_total: Saldo pendiente total del cliente.
        """
        super().__init__(parent)
        self.cliente = cliente
        self.creditos = creditos_pendientes
        self.saldo_total = saldo_total
        self.service = CreditosService()

        self.setWindowTitle(f"Registrar Abono - {cliente.nombre}")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setObjectName("abonoDialog")

        self._setup_ui()
        self._aplicar_estilos()
        self._on_credito_cambiado()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(16)

        lbl_saldo = QLabel(f"Saldo pendiente total: {formatear_moneda(self.saldo_total)}")
        lbl_saldo.setObjectName("lblSaldoTotal")
        lbl_saldo.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_saldo)

        form = QFormLayout()
        form.setSpacing(12)

        self.credito_combo = QComboBox()
        for credito in self.creditos:
            etiqueta = (
                f"Crédito #{credito.id} — "
                f"Pendiente {formatear_moneda(credito.monto_pendiente)}"
                f" (Folio: {credito.venta.folio if credito.venta else '—'})"
            )
            self.credito_combo.addItem(etiqueta, credito.id)
        self.credito_combo.currentIndexChanged.connect(self._on_credito_cambiado)
        form.addRow("Crédito a abonar:", self.credito_combo)

        self.monto_spin = QDoubleSpinBox()
        self.monto_spin.setPrefix("$ ")
        self.monto_spin.setDecimals(2)
        self.monto_spin.setRange(0.01, 999999.99)
        self.monto_spin.setSingleStep(50)
        self.monto_spin.setGroupSeparatorShown(True)
        self.monto_spin.valueChanged.connect(self._actualizar_maximo)
        form.addRow("Monto del abono:", self.monto_spin)

        self.notas_edit = QLineEdit()
        self.notas_edit.setPlaceholderText("Nota opcional (ej: pago parcial)")
        self.notas_edit.setMaxLength(200)
        form.addRow("Notas:", self.notas_edit)

        layout.addLayout(form)

        botones = QHBoxLayout()
        botones.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.clicked.connect(self.reject)

        btn_guardar = QPushButton("Registrar Abono")
        btn_guardar.setObjectName("btnPrimario")
        btn_guardar.clicked.connect(self._guardar)

        botones.addWidget(btn_cancelar)
        botones.addWidget(btn_guardar)
        layout.addLayout(botones)

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------

    def _credito_seleccionado(self):
        idx = self.credito_combo.currentIndex()
        if idx < 0 or idx >= len(self.creditos):
            return None
        return self.creditos[idx]

    def _on_credito_cambiado(self):
        credito = self._credito_seleccionado()
        if credito:
            self.monto_spin.setMaximum(float(credito.monto_pendiente))
            self.monto_spin.setValue(float(credito.monto_pendiente))

    def _actualizar_maximo(self):
        credito = self._credito_seleccionado()
        if credito:
            self.monto_spin.setMaximum(float(credito.monto_pendiente))

    def _guardar(self):
        credito = self._credito_seleccionado()
        if not credito:
            QMessageBox.warning(self, "Error", "Selecciona un crédito.")
            return

        monto = Decimal(str(self.monto_spin.value()))
        if monto <= 0:
            QMessageBox.warning(self, "Error", "El abono debe ser mayor a cero.")
            return

        try:
            resultado = self.service.registrar_abono(
                cliente_id=self.cliente.id,
                credito_id=credito.id,
                monto=monto,
                notas=self.notas_edit.text().strip() or None,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        QMessageBox.information(self, "Abono registrado", resultado["mensaje"])
        self.accept()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#abonoDialog {
                background-color: #f5f5f5;
            }

            QLabel {
                color: #2c3e50;
                font-size: 13px;
            }

            #lblSaldoTotal {
                color: #e67e22;
                font-size: 15px;
                font-weight: 700;
            }

            QComboBox, QLineEdit, QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 7px 8px;
                font-size: 13px;
                min-height: 22px;
                color: #2c3e50;
            }

            QComboBox:focus, QLineEdit:focus, QDoubleSpinBox:focus {
                border-color: #3498db;
            }

            QComboBox QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #3498db;
                selection-color: #ffffff;
            }

            QPushButton#btnPrimario {
                background-color: #27ae60;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 22px;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton#btnPrimario:hover {
                background-color: #219a52;
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
