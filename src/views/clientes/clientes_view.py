"""
Vista del módulo de Clientes y Sistema de Fiado.
Dos pestañas: Clientes (CRUD) y Fiados (clientes con saldo pendiente).
"""

from decimal import Decimal

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QTabWidget,
    QMessageBox,
)
from PySide6.QtCore import Qt

from services.clientes_service import ClientesService
from services.creditos_service import CreditosService
from utils.formatters import formatear_moneda
from views.clientes.cliente_dialog import ClienteDialog
from views.clientes.credito_dialog import CreditoDialog


class ClientesView(QWidget):
    """Vista de clientes con catálogo y módulo de fiados."""

    CLIENTES_COLS = ["Nombre", "Teléfono", "Dirección", "Límite crédito", "Saldo", "Estado"]
    FIADOS_COLS = ["Cliente", "Teléfono", "Saldo pendiente"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("clientesView")
        self.clientes_service = ClientesService()
        self.creditos_service = CreditosService()
        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("clientesTabs")
        self.tabs.addTab(self._crear_tab_clientes(), "Clientes")
        self.tabs.addTab(self._crear_tab_fiados(), "Fiados")
        layout.addWidget(self.tabs)

    def _crear_tab_clientes(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        # --- Barra de herramientas ---
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("busquedaCli")
        self.search_edit.setPlaceholderText("Buscar por nombre, teléfono o email...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._recargar)
        toolbar.addWidget(self.search_edit, 1)

        self.btn_nuevo = QPushButton("Nuevo Cliente")
        self.btn_nuevo.setObjectName("btnPrimario")
        self.btn_nuevo.clicked.connect(self._on_nuevo)
        toolbar.addWidget(self.btn_nuevo)

        self.btn_editar = QPushButton("Editar")
        self.btn_editar.setObjectName("btnSecundario")
        self.btn_editar.clicked.connect(self._on_editar)
        toolbar.addWidget(self.btn_editar)

        self.btn_credito = QPushButton("Crédito / Fiado")
        self.btn_credito.setObjectName("btnSecundario")
        self.btn_credito.clicked.connect(self._on_credito)
        toolbar.addWidget(self.btn_credito)

        self.btn_estado = QPushButton("Desactivar")
        self.btn_estado.setObjectName("btnSecundario")
        self.btn_estado.clicked.connect(self._on_cambiar_estado)
        toolbar.addWidget(self.btn_estado)

        layout.addLayout(toolbar)

        # --- Tabla ---
        self.tabla = QTableWidget(0, len(self.CLIENTES_COLS))
        self.tabla.setObjectName("tablaCli")
        self.tabla.setHorizontalHeaderLabels(self.CLIENTES_COLS)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        self.tabla.itemSelectionChanged.connect(self._actualizar_botones)
        self.tabla.cellDoubleClicked.connect(lambda *_: self._on_credito())

        hdr = self.tabla.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tabla, 1)

        self.info_label = QLabel("")
        self.info_label.setObjectName("infoLabel")
        layout.addWidget(self.info_label)

        self.btn_editar.setEnabled(False)
        self.btn_credito.setEnabled(False)
        self.btn_estado.setEnabled(False)
        return tab

    def _crear_tab_fiados(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        lbl = QLabel("Clientes con deuda pendiente:")
        lbl.setObjectName("lblFiados")
        toolbar.addWidget(lbl)

        toolbar.addStretch()

        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setObjectName("btnSecundario")
        self.btn_actualizar.clicked.connect(self._recargar_fiados)
        toolbar.addWidget(self.btn_actualizar)

        layout.addLayout(toolbar)

        self.tabla_fiados = QTableWidget(0, len(self.FIADOS_COLS))
        self.tabla_fiados.setObjectName("tablaCli")
        self.tabla_fiados.setHorizontalHeaderLabels(self.FIADOS_COLS)
        self.tabla_fiados.verticalHeader().setVisible(False)
        self.tabla_fiados.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_fiados.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_fiados.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_fiados.setAlternatingRowColors(True)
        self.tabla_fiados.setShowGrid(False)
        self.tabla_fiados.itemSelectionChanged.connect(self._actualizar_boton_fiados)
        self.tabla_fiados.cellDoubleClicked.connect(self._abrir_credito_de_fiados)

        hdr = self.tabla_fiados.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tabla_fiados, 1)

        # Botón para abrir historial/abonar desde la pestaña Fiados
        fila_botones = QHBoxLayout()
        fila_botones.addStretch()
        self.btn_abonar = QPushButton("Ver / Abonar deuda")
        self.btn_abonar.setObjectName("btnPrimario")
        self.btn_abonar.clicked.connect(self._abrir_credito_de_fiados)
        self.btn_abonar.setEnabled(False)
        fila_botones.addWidget(self.btn_abonar)
        layout.addLayout(fila_botones)

        self.fiados_info_label = QLabel("")
        self.fiados_info_label.setObjectName("infoLabel")
        layout.addWidget(self.fiados_info_label)

        return tab

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._recargar()
        if self.tabs.currentIndex() == 1:
            self._recargar_fiados()

    # ------------------------------------------------------------------
    # Clientes
    # ------------------------------------------------------------------

    def _recargar(self):
        termino = self.search_edit.text()
        self._clientes = self.clientes_service.buscar(termino, incluir_inactivos=True)

        self.tabla.setRowCount(0)
        for cliente in self._clientes:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)

            valores = [
                cliente.nombre,
                cliente.telefono or "—",
                cliente.direccion or "—",
                formatear_moneda(cliente.limite_credito or 0),
                formatear_moneda(cliente.saldo_actual or 0),
                "Activo" if cliente.activo else "Inactivo",
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col in (3, 4):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col == 5:
                    item.setTextAlignment(Qt.AlignCenter)
                    if not cliente.activo:
                        item.setForeground(Qt.gray)
                    elif (cliente.saldo_actual or 0) > 0:
                        item.setForeground(Qt.darkRed)
                item.setData(Qt.UserRole, cliente.id)
                self.tabla.setItem(fila, col, item)

        total = len(self._clientes)
        self.info_label.setText(f"{total} cliente(s)" if total != 1 else "1 cliente")
        self._actualizar_botones()

    def _cliente_seleccionado(self):
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._clientes):
            return None
        return self._clientes[fila]

    def _actualizar_botones(self):
        cliente = self._cliente_seleccionado()
        self.btn_editar.setEnabled(cliente is not None)
        self.btn_credito.setEnabled(cliente is not None)
        if cliente:
            self.btn_estado.setEnabled(True)
            self.btn_estado.setText("Desactivar" if cliente.activo else "Activar")
        else:
            self.btn_estado.setEnabled(False)
            self.btn_estado.setText("Desactivar")

    def _on_nuevo(self):
        dialogo = ClienteDialog(parent=self)
        if dialogo.exec():
            self._recargar()

    def _on_editar(self):
        cliente = self._cliente_seleccionado()
        if not cliente:
            return
        dialogo = ClienteDialog(cliente, self)
        if dialogo.exec():
            self._recargar()

    def _on_credito(self):
        cliente = self._cliente_seleccionado()
        if not cliente:
            return
        self._abrir_credito(cliente)

    def _abrir_credito(self, cliente):
        dialogo = CreditoDialog(cliente, self)
        dialogo.exec()
        self._recargar()

    def _on_cambiar_estado(self):
        cliente = self._cliente_seleccionado()
        if not cliente:
            return
        accion = "desactivar" if cliente.activo else "activar"
        respuesta = QMessageBox.question(
            self,
            f"{'Desactivar' if cliente.activo else 'Activar'} cliente",
            f"¿Desea {accion} al cliente '{cliente.nombre}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta == QMessageBox.Yes:
            try:
                self.clientes_service.cambiar_estado(cliente.id, not cliente.activo)
            except ValueError as e:
                QMessageBox.warning(self, "Error", str(e))
                return
            self._recargar()

    # ------------------------------------------------------------------
    # Fiados
    # ------------------------------------------------------------------

    def _recargar_fiados(self):
        filas = self.creditos_service.obtener_clientes_con_saldo()
        self._fiados = filas

        self.tabla_fiados.setRowCount(0)
        for fila_info in filas:
            cliente = fila_info["cliente"]
            fila = self.tabla_fiados.rowCount()
            self.tabla_fiados.insertRow(fila)

            valores = [
                cliente.nombre,
                cliente.telefono or "—",
                formatear_moneda(fila_info["saldo"]),
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col == 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item.setData(Qt.UserRole, cliente.id)
                self.tabla_fiados.setItem(fila, col, item)

        total_saldo = sum(
            (Decimal(str(f["saldo"])) for f in filas), Decimal("0")
        )
        self.fiados_info_label.setText(
            f"{len(filas)} cliente(s) con deuda. "
            f"Total pendiente: {formatear_moneda(total_saldo)}"
        )
        self._actualizar_boton_fiados()

    def _cliente_fiado_seleccionado(self):
        fila = self.tabla_fiados.currentRow()
        if fila < 0 or fila >= len(self._fiados):
            return None
        return self._fiados[fila]["cliente"]

    def _actualizar_boton_fiados(self):
        self.btn_abonar.setEnabled(self._cliente_fiado_seleccionado() is not None)

    def _abrir_credito_de_fiados(self):
        cliente = self._cliente_fiado_seleccionado()
        if not cliente:
            return
        self._abrir_credito(cliente)
        self._recargar_fiados()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QWidget#clientesView {
                background-color: #f5f5f5;
            }

            QTabWidget#clientesTabs::pane {
                border: none;
                background-color: #f5f5f5;
            }

            QTabWidget#clientesTabs QTabBar::tab {
                background-color: #e3e8ee;
                color: #2c3e50;
                padding: 9px 22px;
                font-size: 13px;
                border: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
            }

            QTabWidget#clientesTabs QTabBar::tab:selected {
                background-color: #ffffff;
                color: #2c3e50;
                font-weight: 600;
            }

            QLineEdit#busquedaCli {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 7px 10px;
                font-size: 13px;
                color: #2c3e50;
            }

            QLineEdit#busquedaCli:focus {
                border-color: #3498db;
            }

            QTableWidget#tablaCli {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #dceaf7;
                selection-color: #1a252f;
            }

            QTableWidget#tablaCli::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget#tablaCli QHeaderView::section {
                background-color: #2c3e50;
                color: #ffffff;
                padding: 8px 10px;
                border: none;
                font-size: 12px;
                font-weight: 600;
            }

            #lblFiados {
                color: #2c3e50;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton#btnPrimario {
                background-color: #3498db;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton#btnPrimario:hover {
                background-color: #2980b9;
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
                padding: 8px 18px;
                font-size: 13px;
            }

            QPushButton#btnSecundario:hover {
                background-color: #f1f3f5;
                border-color: #95a5a6;
            }

            QPushButton#btnSecundario:disabled {
                color: #bdc3c7;
                background-color: #f8f9fa;
            }

            #infoLabel {
                color: #7f8c8d;
                font-size: 12px;
            }
        """)
