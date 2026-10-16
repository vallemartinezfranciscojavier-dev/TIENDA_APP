"""
Vista del módulo de Inventario.
Dos pestañas: Existencias (consulta con filtros y ajustes) y Movimientos
(historial de entradas, salidas y ajustes).
"""

from decimal import Decimal

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QTabWidget,
    QMessageBox,
)
from PySide6.QtCore import Qt

from database.models import TipoMovimientoEnum
from services.inventario_service import InventarioService
from services.productos_service import ProductosService
from utils.formatters import (
    formatear_numero,
    formatear_fecha_hora,
    formatear_fecha,
)
from views.inventario.ajuste_dialog import AjusteDialog


ETIQUETA_TIPO = {
    TipoMovimientoEnum.ENTRADA: "Entrada",
    TipoMovimientoEnum.SALIDA: "Salida",
    TipoMovimientoEnum.AJUSTE: "Ajuste",
    TipoMovimientoEnum.DEVOLUCION: "Devolución",
}

ETIQUETA_REFERENCIA = {
    "venta": "Venta",
    "compra": "Compra",
    "ajuste": "Ajuste",
    "alta_inicial": "Alta inicial",
    "devolucion": "Devolución",
}


class InventarioView(QWidget):
    """Vista de inventario con existencias y movimientos."""

    CATALOGO_COLS = ["Producto", "Categoría", "Stock Actual", "Stock Mínimo", "Estado"]
    MOVIMIENTOS_COLS = ["Fecha", "Producto", "Tipo", "Cantidad", "Usuario", "Referencia"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inventarioView")
        self.inventario_service = InventarioService()
        self.productos_service = ProductosService()
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
        self.tabs.setObjectName("inventarioTabs")
        self.tabs.addTab(self._crear_tab_existencias(), "Existencias")
        self.tabs.addTab(self._crear_tab_movimientos(), "Movimientos")
        layout.addWidget(self.tabs)

    def _crear_tab_existencias(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        # --- Filtros ---
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("busquedaInv")
        self.search_edit.setPlaceholderText("Buscar por nombre o código...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._recargar)
        toolbar.addWidget(self.search_edit, 1)

        self.categoria_filtro = QComboBox()
        self.categoria_filtro.setObjectName("filtroInv")
        self.categoria_filtro.setMinimumWidth(160)
        self.categoria_filtro.currentIndexChanged.connect(self._recargar)
        toolbar.addWidget(self.categoria_filtro)

        self.estado_filtro = QComboBox()
        self.estado_filtro.setObjectName("filtroInv")
        self.estado_filtro.addItem("Todos", "todos")
        self.estado_filtro.addItem("Bajo stock", "bajo")
        self.estado_filtro.addItem("Sin stock", "sin_stock")
        self.estado_filtro.setMinimumWidth(120)
        self.estado_filtro.currentIndexChanged.connect(self._recargar)
        toolbar.addWidget(self.estado_filtro)

        self.btn_ajustar = QPushButton("Ajustar Stock")
        self.btn_ajustar.setObjectName("btnPrimario")
        self.btn_ajustar.clicked.connect(self._on_ajustar)
        toolbar.addWidget(self.btn_ajustar)

        layout.addLayout(toolbar)

        # --- Tabla ---
        self.tabla = QTableWidget(0, len(self.CATALOGO_COLS))
        self.tabla.setObjectName("tablaInv")
        self.tabla.setHorizontalHeaderLabels(self.CATALOGO_COLS)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        self.tabla.itemSelectionChanged.connect(self._actualizar_botones)
        self.tabla.cellDoubleClicked.connect(lambda *_: self._on_ajustar())

        hdr = self.tabla.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tabla, 1)

        self.info_label = QLabel("")
        self.info_label.setObjectName("infoLabel")
        layout.addWidget(self.info_label)

        self.btn_ajustar.setEnabled(False)
        return tab

    def _crear_tab_movimientos(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.mov_search_edit = QLineEdit()
        self.mov_search_edit.setObjectName("busquedaInv")
        self.mov_search_edit.setPlaceholderText("Filtrar por producto...")
        self.mov_search_edit.setClearButtonEnabled(True)
        self.mov_search_edit.textChanged.connect(self._recargar_movimientos)
        toolbar.addWidget(self.mov_search_edit, 1)

        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setObjectName("btnSecundario")
        self.btn_actualizar.clicked.connect(self._recargar_movimientos)
        toolbar.addWidget(self.btn_actualizar)

        layout.addLayout(toolbar)

        self.tabla_movimientos = QTableWidget(0, len(self.MOVIMIENTOS_COLS))
        self.tabla_movimientos.setObjectName("tablaInv")
        self.tabla_movimientos.setHorizontalHeaderLabels(self.MOVIMIENTOS_COLS)
        self.tabla_movimientos.verticalHeader().setVisible(False)
        self.tabla_movimientos.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla_movimientos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_movimientos.setAlternatingRowColors(True)
        self.tabla_movimientos.setShowGrid(False)

        hdr = self.tabla_movimientos.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.tabla_movimientos, 1)

        self.mov_info_label = QLabel("")
        self.mov_info_label.setObjectName("infoLabel")
        layout.addWidget(self.mov_info_label)

        return tab

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._recargar_categorias()
        self._recargar()
        if self.tabs.currentIndex() == 1:
            self._recargar_movimientos()

    # ------------------------------------------------------------------
    # Existencias
    # ------------------------------------------------------------------

    def _recargar_categorias(self):
        actual_id = self.categoria_filtro.currentData()
        self.categoria_filtro.blockSignals(True)
        self.categoria_filtro.clear()
        self.categoria_filtro.addItem("Todas las categorías", None)
        for cat in self.productos_service.obtener_categorias():
            self.categoria_filtro.addItem(cat.nombre, cat.id)
        if actual_id is not None:
            idx = self.categoria_filtro.findData(actual_id)
            self.categoria_filtro.setCurrentIndex(idx if idx >= 0 else 0)
        self.categoria_filtro.blockSignals(False)

    def _recargar(self):
        termino = self.search_edit.text()
        categoria_id = self.categoria_filtro.currentData()
        estado = self.estado_filtro.currentData() or "todos"

        self._catalogo = self.inventario_service.obtener_catalogo(
            estado=estado,
            categoria_id=categoria_id,
            termino=termino,
        )

        self.tabla.setRowCount(0)
        for producto in self._catalogo:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)

            stock = (
                Decimal(str(producto.inventario.cantidad))
                if producto.inventario is not None
                else Decimal("0")
            )
            minimo = Decimal(str(producto.stock_minimo or 0))
            categoria = producto.categoria.nombre if producto.categoria else "—"

            valores = [
                producto.nombre,
                categoria,
                formatear_numero(stock, 3),
                formatear_numero(minimo, 3),
                "Activo" if producto.activo else "Inactivo",
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col in (2, 3, 4):
                    item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, producto.id)
                self.tabla.setItem(fila, col, item)

        total = len(self._catalogo)
        self.info_label.setText(
            f"{total} producto(s)" if total != 1 else "1 producto"
        )
        self._actualizar_botones()

    def _producto_seleccionado(self):
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._catalogo):
            return None
        return self._catalogo[fila]

    def _actualizar_botones(self):
        self.btn_ajustar.setEnabled(self._producto_seleccionado() is not None)

    def _on_ajustar(self):
        producto = self._producto_seleccionado()
        if not producto:
            return
        dialogo = AjusteDialog(producto, self)
        if dialogo.exec():
            self._recargar()

    # ------------------------------------------------------------------
    # Movimientos
    # ------------------------------------------------------------------

    def _recargar_movimientos(self):
        termino = self.mov_search_edit.text()
        movimientos = self.inventario_service.obtener_movimientos(termino=termino, limite=200)

        self.tabla_movimientos.setRowCount(0)
        for m in movimientos:
            fila = self.tabla_movimientos.rowCount()
            self.tabla_movimientos.insertRow(fila)

            nombre_producto = m.producto.nombre if m.producto else "—"
            usuario = m.usuario.nombre if m.usuario else "Sistema"
            referencia = self._formatear_referencia(m.referencia_tipo, m.referencia_id)
            cantidad_decimal = Decimal(str(m.cantidad))
            signo = "+" if cantidad_decimal >= 0 else ""
            cantidad_txt = signo + formatear_numero(cantidad_decimal, 3)

            valores = [
                formatear_fecha_hora(m.fecha, "%d/%m/%Y %H:%M"),
                nombre_producto,
                ETIQUETA_TIPO.get(m.tipo, str(m.tipo.value)),
                cantidad_txt,
                usuario,
                referencia,
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col in (2, 3):
                    item.setTextAlignment(Qt.AlignCenter)
                # Colorear entradas (verdes) y salidas/ajustes negativos (rojos)
                if col == 3:
                    if m.tipo == TipoMovimientoEnum.ENTRADA:
                        item.setForeground(Qt.darkGreen)
                    elif cantidad_decimal < 0:
                        item.setForeground(Qt.red)
                self.tabla_movimientos.setItem(fila, col, item)

        self.mov_info_label.setText(
            f"Mostrando {len(movimientos)} movimiento(s)."
        )

    def _formatear_referencia(self, tipo, ref_id):
        if tipo and ref_id:
            etiqueta = ETIQUETA_REFERENCIA.get(tipo, tipo)
            return f"{etiqueta} #{ref_id}"
        return "—"

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QWidget#inventarioView {
                background-color: #f5f5f5;
            }

            QTabWidget#inventarioTabs::pane {
                border: none;
                background-color: #f5f5f5;
            }

            QTabWidget#inventarioTabs QTabBar::tab {
                background-color: #e3e8ee;
                color: #2c3e50;
                padding: 9px 22px;
                font-size: 13px;
                border: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
            }

            QTabWidget#inventarioTabs QTabBar::tab:selected {
                background-color: #ffffff;
                color: #2c3e50;
                font-weight: 600;
            }

            QTabWidget#inventarioTabs QTabBar::tab:hover:!selected {
                background-color: #d4dbe3;
            }

            QLineEdit#busquedaInv {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 7px 10px;
                font-size: 13px;
                color: #2c3e50;
            }

            QLineEdit#busquedaInv:focus {
                border-color: #3498db;
            }

            QComboBox#filtroInv {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                color: #2c3e50;
            }

            QComboBox#filtroInv QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #3498db;
                selection-color: #ffffff;
            }

            QTableWidget#tablaInv {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #dceaf7;
                selection-color: #1a252f;
            }

            QTableWidget#tablaInv::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget#tablaInv QHeaderView::section {
                background-color: #2c3e50;
                color: #ffffff;
                padding: 8px 10px;
                border: none;
                font-size: 12px;
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

            #infoLabel {
                color: #7f8c8d;
                font-size: 12px;
            }
        """)