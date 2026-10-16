"""
Vista principal del módulo de Productos.
Tabla, búsqueda, filtros, alta, edición y activar/desactivar.
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
    QMessageBox,
)
from PySide6.QtCore import Qt, QItemSelection

from services.productos_service import ProductosService
from utils.formatters import formatear_numero, formatear_moneda
from views.productos.producto_dialog import ProductoDialog, etiqueta_tipo_venta
from views.productos.etiqueta_dialog import EtiquetaDialog


class ProductosView(QWidget):
    """Vista de administración de productos."""

    COLUMNAS = ["Código", "Nombre", "Categoría", "Tipo de Venta", "Precio Venta", "Stock", "Estado"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("productosView")
        self.service = ProductosService()
        self._productos = []
        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ---- Barra de herramientas superior ----
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.search_edit = QLineEdit(self)
        self.search_edit.setObjectName("productosBusqueda")
        self.search_edit.setPlaceholderText("Buscar por nombre, código o código de barras...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(240)
        self.search_edit.textChanged.connect(self._recargar)
        toolbar.addWidget(self.search_edit, 1)

        self.categoria_filtro = QComboBox(self)
        self.categoria_filtro.setObjectName("productosFiltro")
        self.categoria_filtro.setMinimumWidth(160)
        self.categoria_filtro.currentIndexChanged.connect(self._recargar)
        toolbar.addWidget(self.categoria_filtro)

        self.estado_filtro = QComboBox(self)
        self.estado_filtro.setObjectName("productosFiltro")
        self.estado_filtro.addItem("Todos", "todos")
        self.estado_filtro.addItem("Activos", "activos")
        self.estado_filtro.addItem("Inactivos", "inactivos")
        self.estado_filtro.setMinimumWidth(110)
        self.estado_filtro.currentIndexChanged.connect(self._recargar)
        toolbar.addWidget(self.estado_filtro)

        self.btn_nuevo = QPushButton("Nuevo Producto", self)
        self.btn_nuevo.setObjectName("btnPrimario")
        self.btn_nuevo.clicked.connect(self._on_nuevo)
        toolbar.addWidget(self.btn_nuevo)

        self.btn_etiquetas = QPushButton("Etiquetas", self)
        self.btn_etiquetas.setObjectName("btnSecundario")
        self.btn_etiquetas.setToolTip(
            "Generar etiquetas de precios con código de barras (40x25 mm)."
        )
        self.btn_etiquetas.clicked.connect(self._on_etiquetas)
        toolbar.addWidget(self.btn_etiquetas)

        layout.addLayout(toolbar)

        # ---- Tabla ----
        self.tabla = QTableWidget(0, len(self.COLUMNAS), self)
        self.tabla.setObjectName("productosTabla")
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)

        header = self.tabla.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self.tabla.itemSelectionChanged.connect(self._actualizar_estado_botones)
        self.tabla.cellDoubleClicked.connect(self._on_doble_click)
        layout.addWidget(self.tabla, 1)

        # ---- Barra de acciones inferior ----
        acciones = QHBoxLayout()
        acciones.setSpacing(10)

        self.info_label = QLabel("")
        self.info_label.setObjectName("productosInfo")
        acciones.addWidget(self.info_label)

        acciones.addStretch()

        self.btn_editar = QPushButton("Editar", self)
        self.btn_editar.setObjectName("btnSecundario")
        self.btn_editar.clicked.connect(self._on_editar)
        acciones.addWidget(self.btn_editar)

        self.btn_toggle = QPushButton("Desactivar", self)
        self.btn_toggle.setObjectName("btnPeligro")
        self.btn_toggle.clicked.connect(self._on_toggle)
        acciones.addWidget(self.btn_toggle)

        layout.addLayout(acciones)

        self._actualizar_estado_botones()

    # ------------------------------------------------------------------
    # Permisos (Fase 11)
    # ------------------------------------------------------------------

    def set_modo_lectura(self, lectura: bool):
        """
        Modo consulta: se ocultan los botones de alta/edición/activación.
        Usado para roles sin permiso de modificar productos (Empleado).
        """
        self._modo_lectura = bool(lectura)
        self.btn_nuevo.setVisible(not self._modo_lectura)
        self.btn_editar.setVisible(not self._modo_lectura)
        self.btn_toggle.setVisible(not self._modo_lectura)
        self._actualizar_estado_botones()

    def _on_doble_click(self):
        """Doble clic: solo abre edición si el rol puede modificar."""
        if not getattr(self, "_modo_lectura", False):
            self._on_editar()

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def showEvent(self, event):
        """Al mostrar la vista, refrescar filtros y datos."""
        super().showEvent(event)
        self._recargar_categorias()
        self._recargar()

    def _recargar_categorias(self):
        """Refrescar el combo de categorías conservando la selección."""
        actual_id = self.categoria_filtro.currentData()
        self.categoria_filtro.blockSignals(True)
        self.categoria_filtro.clear()
        self.categoria_filtro.addItem("Todas las categorías", None)
        for cat in self.service.obtener_categorias():
            self.categoria_filtro.addItem(cat.nombre, cat.id)
        if actual_id is not None:
            idx = self.categoria_filtro.findData(actual_id)
            self.categoria_filtro.setCurrentIndex(idx if idx >= 0 else 0)
        self.categoria_filtro.blockSignals(False)

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    def _recargar(self):
        """Cargar productos según los filtros activos."""
        termino = self.search_edit.text()
        categoria_id = self.categoria_filtro.currentData()
        estado = self.estado_filtro.currentData() or "todos"

        self._productos = self.service.buscar(termino, categoria_id, estado)

        self.tabla.setRowCount(0)
        now = Qt.AlignLeft | Qt.AlignVCenter
        centro = Qt.AlignCenter

        for producto in self._productos:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)

            stock = producto.inventario.cantidad if producto.inventario is not None else Decimal("0")
            nombre_categoria = producto.categoria.nombre if producto.categoria else "—"

            valores = [
                producto.codigo,
                producto.nombre,
                nombre_categoria,
                etiqueta_tipo_venta(producto.tipo_venta),
                formatear_moneda(producto.precio_venta),
                formatear_numero(stock, 3),
                "Activo" if producto.activo else "Inactivo",
            ]

            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col in (5, 6):
                    item.setTextAlignment(centro)
                else:
                    item.setTextAlignment(now)
                # Referencia al producto para las acciones
                item.setData(Qt.UserRole, producto.id)
                self.tabla.setItem(fila, col, item)

        total = len(self._productos)
        if total == 1:
            self.info_label.setText("Mostrando 1 producto")
        else:
            self.info_label.setText(f"Mostrando {total} productos")

        self._actualizar_estado_botones()

    def _producto_seleccionado(self):
        """Obtener el producto correspondiente a la fila seleccionada."""
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._productos):
            return None
        return self._productos[fila]

    def _actualizar_estado_botones(self):
        """Habilitar/deshabilitar botones según la selección."""
        producto = self._producto_seleccionado()
        tiene_seleccion = producto is not None
        self.btn_editar.setEnabled(tiene_seleccion)
        self.btn_toggle.setEnabled(tiene_seleccion)
        if producto is not None:
            self.btn_toggle.setText("Desactivar" if producto.activo else "Activar")

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _on_nuevo(self):
        """Abrir diálogo para crear un producto."""
        if getattr(self, "_modo_lectura", False):
            return
        dialogo = ProductoDialog(self)
        if dialogo.exec():
            self._recargar()

    def _on_etiquetas(self):
        """Abrir el diálogo de etiquetas con los productos visibles."""
        if not self._productos:
            QMessageBox.information(
                self, "Sin productos",
                "No hay productos para etiquetar.",
            )
            return
        dialogo = EtiquetaDialog(self._productos, self)
        dialogo.exec()

    def _on_editar(self):
        """Abrir diálogo para editar el producto seleccionado."""
        if getattr(self, "_modo_lectura", False):
            return
        producto = self._producto_seleccionado()
        if not producto:
            return
        dialogo = ProductoDialog(self, producto=producto)
        if dialogo.exec():
            self._recargar()

    def _on_toggle(self):
        """Activar o desactivar el producto seleccionado (con confirmación)."""
        if getattr(self, "_modo_lectura", False):
            return
        producto = self._producto_seleccionado()
        if not producto:
            return

        if producto.activo:
            respuesta = QMessageBox.question(
                self,
                "Desactivar producto",
                f"¿Deseas desactivar el producto '{producto.nombre}'?\n"
                "No se eliminará de la base de datos, solo se ocultará.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if respuesta == QMessageBox.Yes:
                self.service.desactivar(producto.id)
        else:
            respuesta = QMessageBox.question(
                self,
                "Activar producto",
                f"¿Deseas activar el producto '{producto.nombre}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if respuesta == QMessageBox.Yes:
                self.service.activar(producto.id)

        self._recargar()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        """Estilos del módulo de productos, consistentes con la app."""
        self.setStyleSheet("""
            QWidget#productosView {
                background-color: #f5f5f5;
            }

            QLineEdit#productosBusqueda {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 7px 10px;
                font-size: 13px;
                color: #2c3e50;
            }

            QLineEdit#productosBusqueda:focus {
                border-color: #3498db;
            }

            QComboBox#productosFiltro {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                color: #2c3e50;
            }

            QComboBox#productosFiltro QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #3498db;
                selection-color: #ffffff;
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

            QPushButton#btnPeligro {
                background-color: #e74c3c;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton#btnPeligro:hover {
                background-color: #c0392b;
            }

            QPushButton#btnPrimario:disabled,
            QPushButton#btnSecundario:disabled,
            QPushButton#btnPeligro:disabled {
                background-color: #bdc3c7;
                color: #ecf0f1;
                border-color: #bdc3c7;
            }

            QLabel#productosInfo {
                color: #7f8c8d;
                font-size: 12px;
            }

            QTableWidget#productosTabla {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #dceaf7;
                selection-color: #1a252f;
            }

            QTableWidget#productosTabla::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget#productosTabla QHeaderView::section {
                background-color: #2c3e50;
                color: #ffffff;
                padding: 8px 10px;
                border: none;
                font-size: 12px;
                font-weight: 600;
            }
        """)