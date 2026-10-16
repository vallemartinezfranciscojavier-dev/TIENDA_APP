"""
Diálogo de historial de crédito/fiado de un cliente.
Muestra las ventas fiadas (créditos), los abonos realizados y el saldo
pendiente. Permite registrar nuevos abonos.
"""

from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QTabWidget,
    QWidget,
    QMessageBox,
)
from PySide6.QtCore import Qt

from services.creditos_service import CreditosService
from services.clientes_service import ClientesService
from utils.formatters import formatear_moneda, formatear_fecha
from views.clientes.abono_dialog import AbonoDialog


class CreditoDialog(QDialog):
    """Historial de crédito de un cliente."""

    CREDITOS_COLS = ["Folio", "Monto original", "Pendiente", "Fecha", "Estado"]
    ABONOS_COLS = ["Fecha", "Monto", "Usuario", "Notas"]

    def __init__(self, cliente, parent=None):
        super().__init__(parent)
        self.cliente = cliente
        self.service = CreditosService()

        self.setWindowTitle(f"Crédito / Fiado - {cliente.nombre}")
        self.setModal(True)
        self.resize(760, 560)
        self.setObjectName("creditoDialog")

        self._setup_ui()
        self._aplicar_estilos()
        self._cargar_historial()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # --- Encabezado ---
        header = QHBoxLayout()
        header.setSpacing(20)

        col_izq = QVBoxLayout()
        col_izq.setSpacing(2)
        lbl_nombre = QLabel(self.cliente.nombre)
        lbl_nombre.setObjectName("lblNombreCliente")
        col_izq.addWidget(lbl_nombre)

        lbl_datos = QLabel(
            f"Teléfono: {self.cliente.telefono or '—'}   ·   "
            f"Dirección: {self.cliente.direccion or '—'}"
        )
        lbl_datos.setObjectName("lblDatosCliente")
        col_izq.addWidget(lbl_datos)
        header.addLayout(col_izq, 1)

        col_der = QVBoxLayout()
        col_der.setSpacing(2)
        col_der.setAlignment(Qt.AlignRight)
        lbl_saldo_txt = QLabel("Saldo pendiente")
        lbl_saldo_txt.setObjectName("lblSaldoTxt")
        lbl_saldo_txt.setAlignment(Qt.AlignRight)
        col_der.addWidget(lbl_saldo_txt)
        self.lbl_saldo = QLabel("$0.00")
        self.lbl_saldo.setObjectName("lblSaldoValor")
        self.lbl_saldo.setAlignment(Qt.AlignRight)
        col_der.addWidget(self.lbl_saldo)
        header.addLayout(col_der)

        layout.addLayout(header)

        # --- Pestañas ---
        self.tabs = QTabWidget()
        self.tabs.setObjectName("creditoTabs")
        self.tabs.addTab(self._tab_creditos(), "Ventas a crédito")
        self.tabs.addTab(self._tab_abonos(), "Abonos")
        layout.addWidget(self.tabs, 1)

        # --- Botones ---
        botones = QHBoxLayout()
        botones.addStretch()

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("btnSecundario")
        btn_cerrar.clicked.connect(self.accept)

        btn_abonar = QPushButton("Registrar Abono")
        btn_abonar.setObjectName("btnPrimario")
        btn_abonar.clicked.connect(self._on_abonar)

        botones.addWidget(btn_cerrar)
        botones.addWidget(btn_abonar)
        layout.addLayout(botones)

    def _tab_creditos(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(10)

        self.tabla_creditos = QTableWidget(0, len(self.CREDITOS_COLS))
        self.tabla_creditos.setHorizontalHeaderLabels(self.CREDITOS_COLS)
        self.tabla_creditos.verticalHeader().setVisible(False)
        self.tabla_creditos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_creditos.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_creditos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_creditos.setAlternatingRowColors(True)
        self.tabla_creditos.setShowGrid(False)

        hdr = self.tabla_creditos.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tabla_creditos, 1)

        return tab

    def _tab_abonos(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(10)

        self.tabla_abonos = QTableWidget(0, len(self.ABONOS_COLS))
        self.tabla_abonos.setHorizontalHeaderLabels(self.ABONOS_COLS)
        self.tabla_abonos.verticalHeader().setVisible(False)
        self.tabla_abonos.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla_abonos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_abonos.setAlternatingRowColors(True)
        self.tabla_abonos.setShowGrid(False)

        hdr = self.tabla_abonos.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.tabla_abonos, 1)

        return tab

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    def _cargar_historial(self):
        historial = self.service.obtener_historial_completo(self.cliente.id)
        saldo = historial["saldo_pendiente"]
        self.lbl_saldo.setText(formatear_moneda(saldo))
        if saldo > 0:
            self.lbl_saldo.setStyleSheet(
                "color: #e67e22; font-size: 24px; font-weight: 700;"
            )
        else:
            self.lbl_saldo.setStyleSheet(
                "color: #27ae60; font-size: 24px; font-weight: 700;"
            )

        self._llenar_creditos(historial["creditos"])
        self._llenar_abonos()

    def _llenar_creditos(self, creditos):
        self.tabla_creditos.setRowCount(0)
        for credito in creditos:
            fila = self.tabla_creditos.rowCount()
            self.tabla_creditos.insertRow(fila)

            estado = "Pagado" if credito["pagado"] else "Pendiente"
            valores = [
                credito["folio"] or f"Crédito #{credito['id']}",
                formatear_moneda(credito["monto_original"]),
                formatear_moneda(credito["monto_pendiente"]),
                formatear_fecha(credito["fecha_creacion"]),
                estado,
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col in (1, 2):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col == 4 and not credito["pagado"]:
                    item.setForeground(Qt.darkRed)
                item.setData(Qt.UserRole, credito["id"])
                self.tabla_creditos.setItem(fila, col, item)

    def _llenar_abonos(self):
        abonos = self.service.obtener_abonos_por_cliente(self.cliente.id)
        self.tabla_abonos.setRowCount(0)
        for abono in abonos:
            fila = self.tabla_abonos.rowCount()
            self.tabla_abonos.insertRow(fila)
            valores = [
                formatear_fecha(abono.fecha, "%d/%m/%Y %H:%M"),
                formatear_moneda(abono.monto),
                abono.usuario.nombre if abono.usuario else "Sistema",
                abono.notas or "—",
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col == 1:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabla_abonos.setItem(fila, col, item)

    # ------------------------------------------------------------------
    # Abonos
    # ------------------------------------------------------------------

    def _on_abonar(self):
        """Abrir el diálogo para registrar un abono."""
        saldo = self.service.obtener_saldo_cliente(self.cliente.id)
        if saldo <= 0:
            QMessageBox.information(
                self, "Sin deuda", "Este cliente no tiene saldo pendiente."
            )
            return

        # Créditos pendientes disponibles
        pendientes = [
            c for c in self.service.obtener_creditos_por_cliente(self.cliente.id)
            if not c.pagado
        ]
        if not pendientes:
            QMessageBox.information(
                self, "Sin deuda", "Este cliente no tiene créditos pendientes."
            )
            return

        dialogo = AbonoDialog(self.cliente, pendientes, saldo, self)
        if dialogo.exec():
            # Recargar historial
            self._cargar_historial()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#creditoDialog {
                background-color: #f5f5f5;
            }

            #lblNombreCliente {
                color: #2c3e50;
                font-size: 18px;
                font-weight: 700;
            }

            #lblDatosCliente {
                color: #7f8c8d;
                font-size: 12px;
            }

            #lblSaldoTxt {
                color: #7f8c8d;
                font-size: 12px;
                font-weight: 600;
            }

            #lblSaldoValor {
                color: #e67e22;
                font-size: 24px;
                font-weight: 700;
            }

            QTabWidget#creditoTabs::pane {
                border: none;
                background-color: #f5f5f5;
            }

            QTabWidget#creditoTabs QTabBar::tab {
                background-color: #e3e8ee;
                color: #2c3e50;
                padding: 9px 22px;
                font-size: 13px;
                border: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
            }

            QTabWidget#creditoTabs QTabBar::tab:selected {
                background-color: #ffffff;
                color: #2c3e50;
                font-weight: 600;
            }

            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #dceaf7;
                selection-color: #1a252f;
            }

            QTableWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget QHeaderView::section {
                background-color: #2c3e50;
                color: #ffffff;
                padding: 8px 10px;
                border: none;
                font-size: 12px;
                font-weight: 600;
            }

            QPushButton#btnPrimario {
                background-color: #27ae60;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 9px 22px;
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
                padding: 9px 22px;
                font-size: 13px;
            }

            QPushButton#btnSecundario:hover {
                background-color: #f1f3f5;
                border-color: #95a5a6;
            }
        """)
