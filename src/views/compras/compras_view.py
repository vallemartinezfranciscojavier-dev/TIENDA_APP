"""
Vista del módulo de Compras.
Permite seleccionar el proveedor, agregar productos con cantidad y precio de
compra, y registrar la compra (que aumenta el inventario).
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
    QDoubleSpinBox,
    QSplitter,
    QMessageBox,
)
from PySide6.QtCore import Qt

from database.models import TipoVentaEnum
from services.compras_service import ComprasService
from services.productos_service import ProductosService
from services.proveedores_service import ProveedoresService
from utils.calculations import redondear_moneda
from utils.formatters import formatear_moneda, formatear_numero
from views.compras.proveedor_dialog import ProveedorDialog
from views.productos.producto_dialog import etiqueta_tipo_venta


PASO_POR_TIPO = {
    TipoVentaEnum.KILOGRAMO: Decimal("0.100"),
    TipoVentaEnum.GRAMOS: Decimal("100"),
}


class ComprasView(QWidget):
    """Vista de administración de compras."""

    RESULTADOS_COLS = ["Código", "Nombre", "Precio", "Stock"]
    DETALLE_COLS = ["Producto", "Tipo", "Cantidad", "P. Compra", "Subtotal"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("comprasView")
        self.compras_service = ComprasService()
        self.productos_service = ProductosService()
        self.proveedores_service = ProveedoresService()
        self._detalle = []  # lista de dicts de línea de compra
        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Barra superior: proveedor + total ---
        toolbar = QWidget()
        toolbar.setObjectName("comprasToolbar")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(20, 14, 20, 14)
        tb.setSpacing(10)

        lbl_prov = QLabel("Proveedor:")
        lbl_prov.setObjectName("lblCampo")
        tb.addWidget(lbl_prov)

        self.proveedor_combo = QComboBox()
        self.proveedor_combo.setObjectName("comboProveedor")
        self.proveedor_combo.setMinimumWidth(220)
        tb.addWidget(self.proveedor_combo, 1)

        self.btn_nuevo_proveedor = QPushButton("Nuevo Proveedor")
        self.btn_nuevo_proveedor.setObjectName("btnSecundario")
        self.btn_nuevo_proveedor.clicked.connect(self._on_nuevo_proveedor)
        tb.addWidget(self.btn_nuevo_proveedor)

        self.lbl_total_compra = QLabel("Total: $0.00")
        self.lbl_total_compra.setObjectName("lblTotalCompra")
        tb.addWidget(self.lbl_total_compra)

        layout.addWidget(toolbar)

        # --- Splitter: izquierda búsqueda / derecha detalle ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        splitter.addWidget(self._crear_panel_busqueda())
        splitter.addWidget(self._crear_panel_detalle())
        splitter.setSizes([520, 640])

        layout.addWidget(splitter, 1)

    def _crear_panel_busqueda(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("panelBusqueda")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)

        enc = QLabel("Buscar Producto")
        enc.setObjectName("panelTitulo")
        layout.addWidget(enc)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("busqueda")
        self.search_edit.setPlaceholderText("Buscar por nombre o código...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._buscar)
        self.search_edit.returnPressed.connect(self._agregar_primero)
        layout.addWidget(self.search_edit)

        self.tabla_resultados = QTableWidget(0, len(self.RESULTADOS_COLS))
        self.tabla_resultados.setObjectName("tablaCompra")
        self.tabla_resultados.setHorizontalHeaderLabels(self.RESULTADOS_COLS)
        self.tabla_resultados.verticalHeader().setVisible(False)
        self.tabla_resultados.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_resultados.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_resultados.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_resultados.setAlternatingRowColors(True)
        self.tabla_resultados.setShowGrid(False)
        self.tabla_resultados.cellDoubleClicked.connect(lambda *_: self._agregar_seleccionado())

        hdr = self.tabla_resultados.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.tabla_resultados, 1)

        self.lbl_resultados = QLabel("Escribe para buscar productos.")
        self.lbl_resultados.setObjectName("infoLabel")
        layout.addWidget(self.lbl_resultados)

        self.btn_agregar = QPushButton("Agregar al Detalle")
        self.btn_agregar.setObjectName("btnPrimario")
        self.btn_agregar.setEnabled(False)
        self.btn_agregar.clicked.connect(self._agregar_seleccionado)
        layout.addWidget(self.btn_agregar)

        return panel

    def _crear_panel_detalle(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("panelDetalle")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)

        enc = QLabel("Detalle de Compra")
        enc.setObjectName("panelTitulo")
        layout.addWidget(enc)

        self.tabla_detalle = QTableWidget(0, len(self.DETALLE_COLS))
        self.tabla_detalle.setObjectName("tablaDetalle")
        self.tabla_detalle.setHorizontalHeaderLabels(self.DETALLE_COLS)
        self.tabla_detalle.verticalHeader().setVisible(False)
        self.tabla_detalle.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_detalle.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_detalle.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_detalle.setAlternatingRowColors(True)
        self.tabla_detalle.setShowGrid(False)
        self.tabla_detalle.itemSelectionChanged.connect(self._cargar_linea_seleccion)

        hdr = self.tabla_detalle.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tabla_detalle, 1)

        # --- Controles de línea ---
        fila_controles = QHBoxLayout()
        fila_controles.setSpacing(8)

        self.lbl_cantidad = QLabel("Cantidad:")
        self.lbl_cantidad.setObjectName("lblCampo")
        fila_controles.addWidget(self.lbl_cantidad)

        self.cantidad_spin = QDoubleSpinBox()
        self.cantidad_spin.setObjectName("spinCant")
        self.cantidad_spin.setRange(0, 999999.999)
        self.cantidad_spin.setDecimals(3)
        self.cantidad_spin.setSingleStep(1)
        fila_controles.addWidget(self.cantidad_spin, 1)

        self.lbl_precio = QLabel("Precio:")
        self.lbl_precio.setObjectName("lblCampo")
        fila_controles.addWidget(self.lbl_precio)

        self.precio_spin = QDoubleSpinBox()
        self.precio_spin.setObjectName("spinPrecio")
        self.precio_spin.setPrefix("$ ")
        self.precio_spin.setDecimals(2)
        self.precio_spin.setRange(0, 999999.99)
        self.precio_spin.setSingleStep(5)
        fila_controles.addWidget(self.precio_spin, 1)

        layout.addLayout(fila_controles)

        # --- Acciones ---
        fila_acciones = QHBoxLayout()
        fila_acciones.setSpacing(8)

        self.btn_aplicar = QPushButton("Actualizar")
        self.btn_aplicar.setObjectName("btnSecundario")
        self.btn_aplicar.setToolTip("Aplicar cantidad y precio a la línea seleccionada")
        self.btn_aplicar.clicked.connect(self._aplicar_linea)
        fila_acciones.addWidget(self.btn_aplicar)

        self.btn_eliminar = QPushButton("Eliminar")
        self.btn_eliminar.setObjectName("btnPeligro")
        self.btn_eliminar.clicked.connect(self._eliminar_linea)
        fila_acciones.addWidget(self.btn_eliminar)

        self.btn_vaciar = QPushButton("Vaciar")
        self.btn_vaciar.setObjectName("btnSecundario")
        self.btn_vaciar.clicked.connect(self._vaciar_detalle)
        fila_acciones.addWidget(self.btn_vaciar)

        layout.addLayout(fila_acciones)
        layout.addStretch()

        # --- Registrar compra ---
        self.btn_registrar = QPushButton("Registrar Compra")
        self.btn_registrar.setObjectName("btnRegistrar")
        self.btn_registrar.setFixedHeight(48)
        self.btn_registrar.clicked.connect(self._on_registrar)
        layout.addWidget(self.btn_registrar)

        self._actualizar_estado()
        self._actualizar_total()

        return panel

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._cargar_proveedores()
        self._buscar()
        self.search_edit.setFocus()

    def _cargar_proveedores(self):
        """Cargar proveedores activos en el combo conservando selección."""
        actual_id = self.proveedor_combo.currentData()
        self.proveedor_combo.blockSignals(True)
        self.proveedor_combo.clear()
        self.proveedor_combo.addItem("Selecciona un proveedor...", None)
        for prov in self.proveedores_service.obtener_activos():
            self.proveedor_combo.addItem(prov.nombre, prov.id)
        if actual_id is not None:
            idx = self.proveedor_combo.findData(actual_id)
            self.proveedor_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.proveedor_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Búsqueda
    # ------------------------------------------------------------------

    def _buscar(self):
        termino = self.search_edit.text()
        self._resultados = self.productos_service.buscar(termino, None, "activos")

        self.tabla_resultados.setRowCount(0)
        for producto in self._resultados:
            fila = self.tabla_resultados.rowCount()
            self.tabla_resultados.insertRow(fila)
            stock = (
                Decimal(str(producto.inventario.cantidad))
                if producto.inventario is not None
                else Decimal("0")
            )
            valores = [
                producto.codigo,
                producto.nombre,
                formatear_moneda(producto.precio_venta),
                formatear_numero(stock, 3),
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col in (2, 3):
                    item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, producto.id)
                self.tabla_resultados.setItem(fila, col, item)

        self.lbl_resultados.setText(
            f"{len(self._resultados)} producto(s) encontrado(s)."
        )
        self.btn_agregar.setEnabled(len(self._resultados) > 0)

    def _agregar_primero(self):
        if self._resultados:
            self.tabla_resultados.selectRow(0)
            self._agregar_seleccionado()

    def _resultado_seleccionado(self):
        fila = self.tabla_resultados.currentRow()
        if fila < 0 or fila >= len(self._resultados):
            return None
        return self._resultados[fila]

    # ------------------------------------------------------------------
    # Detalle
    # ------------------------------------------------------------------

    def _agregar_seleccionado(self):
        producto = self._resultado_seleccionado()
        if not producto:
            return

        paso = PASO_POR_TIPO.get(producto.tipo_venta, Decimal("1"))

        linea = next(
            (l for l in self._detalle if l["producto_id"] == producto.id), None
        )
        if linea:
            linea["cantidad"] += paso
        else:
            # Precio por defecto: último precio de compra si existe
            precio_def = Decimal(str(producto.precio_compra or 0))
            self._detalle.append({
                "producto_id": producto.id,
                "nombre": producto.nombre,
                "tipo_venta": producto.tipo_venta,
                "cantidad": paso,
                "precio": precio_def,
            })

        self._refrescar_detalle()
        # Seleccionar la línea agregada/actualizada
        idx = next(
            (i for i, l in enumerate(self._detalle) if l["producto_id"] == producto.id),
            0,
        )
        self.tabla_detalle.selectRow(idx)

    def _cargar_linea_seleccion(self):
        fila = self.tabla_detalle.currentRow()
        if fila < 0 or fila >= len(self._detalle):
            return
        linea = self._detalle[fila]
        self.cantidad_spin.blockSignals(True)
        self.precio_spin.blockSignals(True)
        self.cantidad_spin.setValue(float(linea["cantidad"]))
        self.precio_spin.setValue(float(linea["precio"]))
        self.cantidad_spin.blockSignals(False)
        self.precio_spin.blockSignals(False)

    def _aplicar_linea(self):
        fila = self.tabla_detalle.currentRow()
        if fila < 0 or fila >= len(self._detalle):
            QMessageBox.information(self, "Selecciona una línea", "Selecciona una línea del detalle.")
            return
        linea = self._detalle[fila]
        cantidad = Decimal(str(self.cantidad_spin.value()))
        precio = Decimal(str(self.precio_spin.value()))
        if cantidad <= 0:
            QMessageBox.warning(self, "Datos inválidos", "La cantidad debe ser mayor a cero.")
            return
        if precio < 0:
            QMessageBox.warning(self, "Datos inválidos", "El precio no puede ser negativo.")
            return
        linea["cantidad"] = cantidad
        linea["precio"] = precio
        self._refrescar_detalle()
        self.tabla_detalle.selectRow(fila)

    def _eliminar_linea(self):
        fila = self.tabla_detalle.currentRow()
        if fila < 0 or fila >= len(self._detalle):
            return
        del self._detalle[fila]
        self._refrescar_detalle()

    def _vaciar_detalle(self):
        if not self._detalle:
            return
        respuesta = QMessageBox.question(
            self,
            "Vaciar detalle",
            "¿Deseas vaciar el detalle de la compra?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta == QMessageBox.Yes:
            self._detalle = []
            self._refrescar_detalle()

    def _refrescar_detalle(self):
        self.tabla_detalle.setRowCount(0)
        for linea in self._detalle:
            fila = self.tabla_detalle.rowCount()
            self.tabla_detalle.insertRow(fila)
            subtotal = redondear_moneda(linea["cantidad"] * linea["precio"])
            valores = [
                linea["nombre"],
                etiqueta_tipo_venta(linea["tipo_venta"]),
                formatear_numero(linea["cantidad"], 3),
                formatear_moneda(linea["precio"]),
                formatear_moneda(subtotal),
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col in (2, 3, 4):
                    item.setTextAlignment(Qt.AlignCenter)
                self.tabla_detalle.setItem(fila, col, item)

        self._actualizar_total()
        self._actualizar_estado()

    def _total_detalle(self):
        suma = sum(
            redondear_moneda(l["cantidad"] * l["precio"])
            for l in self._detalle
        )
        return redondear_moneda(suma)

    def _actualizar_total(self):
        self.lbl_total_compra.setText(f"Total: {formatear_moneda(self._total_detalle())}")

    def _actualizar_estado(self):
        tiene = bool(self._detalle)
        self.btn_registrar.setEnabled(
            tiene and self.proveedor_combo.currentData() is not None
        )

    # ------------------------------------------------------------------
    # Registrar compra
    # ------------------------------------------------------------------

    def _on_registrar(self):
        if not self._detalle:
            QMessageBox.information(self, "Detalle vacío", "Agrega productos al detalle.")
            return
        proveedor_id = self.proveedor_combo.currentData()
        if not proveedor_id:
            QMessageBox.warning(self, "Proveedor requerido", "Selecciona un proveedor.")
            return

        try:
            items = [
                {
                    "producto_id": l["producto_id"],
                    "cantidad": l["cantidad"],
                    "precio": l["precio"],
                }
                for l in self._detalle
            ]
            compra = self.compras_service.crear_compra(
                items=items,
                proveedor_id=proveedor_id,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Error al registrar compra", str(e))
            return

        QMessageBox.information(
            self,
            "Compra registrada",
            f"Compra {compra.folio} registrada correctamente.\n"
            f"Total: {formatear_moneda(compra.total)}\n"
            "El inventario se actualizó.",
        )

        self._detalle = []
        self._refrescar_detalle()
        self._buscar()
        self.search_edit.clear()
        self.search_edit.setFocus()

    def _on_nuevo_proveedor(self):
        dialogo = ProveedorDialog(self)
        if dialogo.exec():
            self._cargar_proveedores()
            idx = self.proveedor_combo.findData(dialogo.proveedor.id)
            if idx >= 0:
                self.proveedor_combo.setCurrentIndex(idx)
            self._actualizar_estado()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QWidget#comprasView {
                background-color: #f5f5f5;
            }

            QWidget#comprasToolbar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
            }

            #lblCampo {
                color: #2c3e50;
                font-size: 13px;
                font-weight: 500;
            }

            #lblTotalCompra {
                color: #2c3e50;
                font-size: 17px;
                font-weight: 700;
            }

            QComboBox#comboProveedor {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                min-height: 22px;
                color: #2c3e50;
            }

            QComboBox#comboProveedor:focus {
                border-color: #3498db;
            }

            QComboBox#comboProveedor QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #3498db;
                selection-color: #ffffff;
            }

            #panelBusqueda, #panelDetalle {
                background-color: #f5f5f5;
            }

            #panelTitulo {
                color: #2c3e50;
                font-size: 17px;
                font-weight: 600;
                padding: 4px 0;
            }

            QLineEdit#busqueda {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                color: #2c3e50;
            }

            QLineEdit#busqueda:focus {
                border-color: #3498db;
            }

            QTableWidget#tablaCompra, QTableWidget#tablaDetalle {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #dceaf7;
                selection-color: #1a252f;
            }

            QTableWidget#tablaCompra::item, QTableWidget#tablaDetalle::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget#tablaCompra QHeaderView::section,
            QTableWidget#tablaDetalle QHeaderView::section {
                background-color: #2c3e50;
                color: #ffffff;
                padding: 8px 10px;
                border: none;
                font-size: 12px;
                font-weight: 600;
            }

            #infoLabel {
                color: #7f8c8d;
                font-size: 12px;
            }

            QDoubleSpinBox#spinCant, QDoubleSpinBox#spinPrecio {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                min-height: 22px;
                color: #2c3e50;
            }

            QDoubleSpinBox#spinCant:focus, QDoubleSpinBox#spinPrecio:focus {
                border-color: #3498db;
            }

            QPushButton#btnPrimario {
                background-color: #3498db;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 9px 18px;
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
                padding: 9px 18px;
                font-size: 13px;
            }

            QPushButton#btnSecundario:hover {
                background-color: #f1f3f5;
                border-color: #95a5a6;
            }

            QPushButton#btnPeligro {
                background-color: #e74c3c;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 9px 18px;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton#btnPeligro:hover {
                background-color: #c0392b;
            }

            QPushButton#btnRegistrar {
                background-color: #3498db;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 15px;
                font-weight: 700;
            }

            QPushButton#btnRegistrar:hover {
                background-color: #2980b9;
            }

            QPushButton#btnRegistrar:disabled {
                background-color: #bdc3c7;
                color: #ecf0f1;
            }
        """)