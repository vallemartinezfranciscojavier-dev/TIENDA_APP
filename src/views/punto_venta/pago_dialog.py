"""
Diálogo de cobro para finalizar una venta.
Permite elegir método de pago, ingresar monto recibido y calcular cambio.
"""

from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
    QFrame,
)
from PySide6.QtCore import Qt

from database.models import MetodoPagoEnum
from services.clientes_service import ClientesService
from utils.calculations import redondear_moneda
from utils.formatters import formatear_moneda


class PagoDialog(QDialog):
    """Diálogo para cobrar una venta."""

    METODOS = [
        ("Efectivo", MetodoPagoEnum.EFECTIVO),
        ("Tarjeta", MetodoPagoEnum.TARJETA),
        ("Transferencia", MetodoPagoEnum.TRANSFERENCIA),
        ("Crédito (Fiado)", MetodoPagoEnum.FIADO),
    ]

    def __init__(self, total, parent=None):
        super().__init__(parent)
        self.total = redondear_moneda(Decimal(str(total)))
        self.metodo = MetodoPagoEnum.EFECTIVO
        self.recibido = self.total
        self.cambio = Decimal("0")
        self.cliente_id = None
        self._clientes = []

        self.setWindowTitle("Cobrar Venta")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setObjectName("pagoDialog")

        self._setup_ui()
        self._aplicar_estilos()
        self._actualizar_vista()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # --- Total a cobrar (destacado) ---
        lbl_total = QLabel("Total a cobrar")
        lbl_total.setObjectName("lblTotal")
        lbl_total.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_total)

        self.lbl_total_valor = QLabel(formatear_moneda(self.total))
        self.lbl_total_valor.setObjectName("lblTotalValor")
        self.lbl_total_valor.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_total_valor)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("sepPago")
        layout.addWidget(sep)

        # --- Método de pago ---
        fila_metodo = QHBoxLayout()
        fila_metodo.setSpacing(12)
        lbl_metodo = QLabel("Método de pago:")
        lbl_metodo.setObjectName("lblCampo")
        fila_metodo.addWidget(lbl_metodo)

        self.metodo_combo = QComboBox()
        self.metodo_combo.setObjectName("metodoCombo")
        for texto, valor in self.METODOS:
            self.metodo_combo.addItem(texto, valor)
        self.metodo_combo.currentIndexChanged.connect(self._on_metodo_cambiado)
        self.metodo_combo.setMinimumWidth(180)
        fila_metodo.addWidget(self.metodo_combo, 1)
        layout.addLayout(fila_metodo)

        # --- Monto recibido (solo efectivo) ---
        self.fila_recibido = QHBoxLayout()
        self.fila_recibido.setSpacing(12)
        lbl_recibido = QLabel("Monto recibido:")
        lbl_recibido.setObjectName("lblCampo")
        self.fila_recibido.addWidget(lbl_recibido)

        self.recibido_spin = QDoubleSpinBox()
        self.recibido_spin.setPrefix("$ ")
        self.recibido_spin.setDecimals(2)
        self.recibido_spin.setRange(0, 999999.99)
        self.recibido_spin.setSingleStep(10)
        self.recibido_spin.setGroupSeparatorShown(True)
        self.recibido_spin.setValue(float(self.total))
        self.recibido_spin.valueChanged.connect(self._actualizar_vista)
        self.recibido_spin.setMinimumWidth(180)
        self.fila_recibido.addWidget(self.recibido_spin, 1)
        layout.addLayout(self.fila_recibido)

        # --- Cliente (solo crédito/fiado) ---
        self.fila_cliente = QHBoxLayout()
        self.fila_cliente.setSpacing(12)
        lbl_cliente = QLabel("Cliente:")
        lbl_cliente.setObjectName("lblCampo")
        self.fila_cliente.addWidget(lbl_cliente)

        self.cliente_combo = QComboBox()
        self.cliente_combo.setObjectName("metodoCombo")
        self._cargar_clientes()
        self.cliente_combo.currentIndexChanged.connect(self._actualizar_vista)
        self.cliente_combo.setMinimumWidth(180)
        self.fila_cliente.addWidget(self.cliente_combo, 1)
        layout.addLayout(self.fila_cliente)
        self._set_fila_visible(self.fila_cliente, False)

        # --- Cambio ---
        self.fila_cambio = QHBoxLayout()
        self.fila_cambio.setSpacing(12)
        lbl_cambio = QLabel("Cambio:")
        lbl_cambio.setObjectName("lblCampo")
        self.fila_cambio.addWidget(lbl_cambio)

        self.lbl_cambio_valor = QLabel(formatear_moneda(Decimal("0")))
        self.lbl_cambio_valor.setObjectName("lblCambioValor")
        self.lbl_cambio_valor.setMinimumWidth(180)
        self.fila_cambio.addWidget(self.lbl_cambio_valor, 1)
        layout.addLayout(self.fila_cambio)

        # --- Error ---
        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("lblError")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        # Separador
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("sepPago")
        layout.addWidget(sep2)

        # --- Botones ---
        botones = QHBoxLayout()
        botones.setSpacing(12)
        botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnSecundario")
        self.btn_cancelar.clicked.connect(self.reject)
        botones.addWidget(self.btn_cancelar)

        self.btn_cobrar = QPushButton("Cobrar")
        self.btn_cobrar.setObjectName("btnPrimario")
        self.btn_cobrar.clicked.connect(self._aceptar)
        botones.addWidget(self.btn_cobrar)

        layout.addLayout(botones)

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------

    @staticmethod
    def _set_fila_visible(layout, visible: bool):
        """Mostrar/ocultar todos los widgets de un QHBoxLayout."""
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget is not None:
                widget.setVisible(visible)

    def _cargar_clientes(self):
        """Cargar clientes activos en el selector."""
        self._clientes = ClientesService().obtener_activos_para_selector()
        self.cliente_combo.clear()
        self.cliente_combo.addItem("Seleccionar cliente...", None)
        for cliente in self._clientes:
            etiqueta = cliente.nombre
            if cliente.telefono:
                etiqueta += f"  ·  {cliente.telefono}"
            self.cliente_combo.addItem(etiqueta, cliente.id)

    def _on_metodo_cambiado(self, index):
        self.metodo = self.METODOS[index][1]
        es_efectivo = self.metodo == MetodoPagoEnum.EFECTIVO
        es_credito = self.metodo == MetodoPagoEnum.FIADO

        self.recibido_spin.setVisible(es_efectivo)
        self._set_fila_visible(self.fila_recibido, es_efectivo)
        self._set_fila_visible(self.fila_cambio, es_efectivo)

        # Combo de cliente visible solo en crédito/fiado
        self._set_fila_visible(self.fila_cliente, es_credito)

        if es_efectivo:
            self.recibido_spin.setFocus()
        elif es_credito:
            self.cliente_combo.setFocus()
        self._actualizar_vista()

    def _actualizar_vista(self):
        """Recalcular cambio y habilitar/deshabilitar botón Cobrar."""
        es_efectivo = self.metodo == MetodoPagoEnum.EFECTIVO
        es_credito = self.metodo == MetodoPagoEnum.FIADO

        if es_efectivo:
            recibido = Decimal(str(self.recibido_spin.value()))
            self.cambio = redondear_moneda(recibido - self.total)
            if self.cambio < 0:
                self.lbl_cambio_valor.setText(f"FALTA: {formatear_moneda(-self.cambio)}")
                self.lbl_cambio_valor.setStyleSheet(
                    "color: #e74c3c; font-size: 18px; font-weight: 700;"
                )
            else:
                self.lbl_cambio_valor.setText(formatear_moneda(self.cambio))
                self.lbl_cambio_valor.setStyleSheet(
                    "color: #27ae60; font-size: 18px; font-weight: 700;"
                )
        else:
            self.cambio = Decimal("0")
            self.lbl_cambio_valor.setText("N/A")

        # Determinar si se puede cobrar
        if es_efectivo:
            puede_cobrar = self.cambio >= 0
        elif es_credito:
            puede_cobrar = self.cliente_combo.currentData() is not None
        else:
            puede_cobrar = True

        self.btn_cobrar.setEnabled(puede_cobrar)
        self.lbl_error.setVisible(not puede_cobrar)
        if not puede_cobrar:
            if es_efectivo:
                self.lbl_error.setText("El monto recibido es menor que el total")
            elif es_credito:
                self.lbl_error.setText("Selecciona un cliente para crédito")
            else:
                self.lbl_error.setText("")
        else:
            self.lbl_error.setText("")

    def _aceptar(self):
        """Confirmar el cobro."""
        es_efectivo = self.metodo == MetodoPagoEnum.EFECTIVO
        es_credito = self.metodo == MetodoPagoEnum.FIADO

        if es_efectivo:
            self.recibido = Decimal(str(self.recibido_spin.value()))
            if self.recibido < self.total:
                return  # Botón deshabilitado, pero por seguridad
        elif es_credito:
            self.cliente_id = self.cliente_combo.currentData()
            if not self.cliente_id:
                return
            self.recibido = self.total
        else:
            self.recibido = self.total
        self.accept()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#pagoDialog {
                background-color: #f8f9fa;
            }

            #lblTotal {
                color: #7f8c8d;
                font-size: 13px;
                font-weight: 500;
            }

            #lblTotalValor {
                color: #2c3e50;
                font-size: 30px;
                font-weight: 700;
                padding: 4px 0 8px;
            }

            #sepPago {
                border: none;
                background-color: #dee2e6;
                max-height: 1px;
            }

            #lblCampo {
                color: #2c3e50;
                font-size: 13px;
                font-weight: 500;
            }

            QComboBox#metodoCombo {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                color: #2c3e50;
                min-height: 22px;
            }

            QComboBox#metodoCombo:focus {
                border-color: #3498db;
            }

            QComboBox#metodoCombo::drop-down {
                border: none;
                width: 24px;
            }

            QComboBox#metodoCombo QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #3498db;
                selection-color: #ffffff;
                border: 1px solid #cbd5e0;
            }

            QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                min-height: 22px;
                color: #2c3e50;
            }

            QDoubleSpinBox:focus {
                border-color: #3498db;
            }

            #lblCambioValor {
                color: #27ae60;
                font-size: 18px;
                font-weight: 700;
            }

            #lblError {
                color: #e74c3c;
                font-size: 12px;
                font-weight: 600;
            }

            QPushButton#btnPrimario {
                background-color: #27ae60;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 28px;
                font-size: 14px;
                font-weight: 700;
            }

            QPushButton#btnPrimario:hover {
                background-color: #219a52;
            }

            QPushButton#btnPrimario:disabled {
                background-color: #bdc3c7;
                color: #ecf0f1;
            }

            QPushButton#btnSecundario {
                background-color: #ffffff;
                color: #2c3e50;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 10px 28px;
                font-size: 14px;
            }

            QPushButton#btnSecundario:hover {
                background-color: #f1f3f5;
                border-color: #95a5a6;
            }
        """)