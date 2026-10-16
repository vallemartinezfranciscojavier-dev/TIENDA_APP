"""
Vista del Punto de Venta.
Permite buscar productos, agregarlos al carrito (por pieza o por peso),
ajustar cantidades y cobrar la venta.
"""

from decimal import Decimal

from PySide6.QtWidgets import (
    QApplication,
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
    QDoubleSpinBox,
    QSplitter,
    QMessageBox,
    QFrame,
)
from PySide6.QtCore import Qt, QEvent

from database.models import TipoVentaEnum, MetodoPagoEnum
from services.ventas_service import VentasService
from services.sesion_service import obtener_usuario_id
from services.permisos_service import hay_permiso_actual
from services.productos_service import ProductosService
from utils.barcode import normalizar_codigo_barras
from utils.calculations import redondear_moneda
from utils.formatters import formatear_moneda, formatear_numero
from views.productos.producto_dialog import etiqueta_tipo_venta
from views.punto_venta.pago_dialog import PagoDialog
from views.punto_venta.cancelar_venta_dialog import CancelarVentaDialog


# Configuración de la cantidad/peso según el tipo de venta
CONFIG_TIPO = {
    TipoVentaEnum.PIEZA: {"decimales": 0, "paso": 1, "minimo": 1, "unidad": "pza", "lbl": "Cantidad"},
    TipoVentaEnum.BOLSA: {"decimales": 0, "paso": 1, "minimo": 1, "unidad": "bolsa", "lbl": "Cantidad"},
    TipoVentaEnum.UNIDAD_PERSONALIZADA: {"decimales": 0, "paso": 1, "minimo": 1, "unidad": "und", "lbl": "Cantidad"},
    TipoVentaEnum.KILOGRAMO: {"decimales": 3, "paso": Decimal("0.100"), "minimo": Decimal("0.001"), "unidad": "kg", "lbl": "Peso (kg)"},
    TipoVentaEnum.GRAMOS: {"decimales": 0, "paso": 100, "minimo": 1, "unidad": "g", "lbl": "Peso (g)"},
}


class PuntoVentaView(QWidget):
    """Vista principal del Punto de Venta."""

    RESULTADOS_COLS = ["Código", "Nombre", "Precio", "Existencias"]
    CARRITO_COLS = ["Producto", "Tipo", "Cantidad", "Precio", "Subtotal"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("puntoVentaView")
        self.ventas_service = VentasService()
        self.productos_service = ProductosService()
        self._carrito = []  # lista de dicts de producto
        self._setup_ui()
        self._aplicar_estilos()
        self._instalar_filtro_enter()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Splitter: izquierda (búsqueda) / derecha (carrito)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        splitter.addWidget(self._crear_panel_busqueda())
        splitter.addWidget(self._crear_panel_carrito())
        splitter.setSizes([520, 640])

        layout.addWidget(splitter)

    def _crear_panel_busqueda(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("panelBusqueda")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Encabezado
        enc = QLabel("Buscar Producto")
        enc.setObjectName("panelTitulo")
        layout.addWidget(enc)

        # Buscador
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("posBusqueda")
        self.search_edit.setPlaceholderText(
            "Buscar por nombre o escanear código de barras..."
        )
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._buscar)
        # Enter se maneja de forma global con un eventFilter (integrado con el
        # lector de códigos de barras, que envía Enter con cualquier foco).
        layout.addWidget(self.search_edit)

        # Tabla de resultados
        self.tabla_resultados = QTableWidget(0, len(self.RESULTADOS_COLS))
        self.tabla_resultados.setObjectName("posTabla")
        self.tabla_resultados.setHorizontalHeaderLabels(self.RESULTADOS_COLS)
        self.tabla_resultados.verticalHeader().setVisible(False)
        self.tabla_resultados.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_resultados.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_resultados.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_resultados.setAlternatingRowColors(True)
        self.tabla_resultados.setShowGrid(False)
        self.tabla_resultados.cellDoubleClicked.connect(lambda *_: self._agregar_seleccionado())

        header = self.tabla_resultados.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.tabla_resultados, 1)

        # Estado de resultados
        self.lbl_resultados = QLabel("Escribe para buscar productos.")
        self.lbl_resultados.setObjectName("infoLabel")
        layout.addWidget(self.lbl_resultados)

        # Botón agregar
        self.btn_agregar = QPushButton("Agregar al Carrito")
        self.btn_agregar.setObjectName("btnPrimario")
        self.btn_agregar.setEnabled(False)
        self.btn_agregar.clicked.connect(self._agregar_seleccionado)
        layout.addWidget(self.btn_agregar)

        return panel

    def _crear_panel_carrito(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("panelCarrito")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Encabezado
        enc = QLabel("Carrito de Compra")
        enc.setObjectName("panelTitulo")
        layout.addWidget(enc)

        # Tabla del carrito
        self.tabla_carrito = QTableWidget(0, len(self.CARRITO_COLS))
        self.tabla_carrito.setObjectName("carritoTabla")
        self.tabla_carrito.setHorizontalHeaderLabels(self.CARRITO_COLS)
        self.tabla_carrito.verticalHeader().setVisible(False)
        self.tabla_carrito.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_carrito.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_carrito.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_carrito.setAlternatingRowColors(True)
        self.tabla_carrito.setShowGrid(False)
        self.tabla_carrito.itemSelectionChanged.connect(self._cargar_cantidad_seleccion)

        hdr = self.tabla_carrito.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tabla_carrito, 1)

        # --- Controles de cantidad ---
        self.controles_frame = QFrame()
        controles = QHBoxLayout(self.controles_frame)
        controles.setContentsMargins(0, 0, 0, 0)
        controles.setSpacing(8)

        self.lbl_cantidad = QLabel("Cantidad:")
        self.lbl_cantidad.setObjectName("lblCampo")
        controles.addWidget(self.lbl_cantidad)

        self.cantidad_spin = QDoubleSpinBox()
        self.cantidad_spin.setObjectName("cantidadSpin")
        self.cantidad_spin.setRange(0, 999999.999)
        self.cantidad_spin.setDecimals(0)
        self.cantidad_spin.setSingleStep(1)
        controles.addWidget(self.cantidad_spin, 1)

        self.btn_mas = QPushButton("+")
        self.btn_mas.setObjectName("btnIcono")
        self.btn_mas.setFixedWidth(40)
        self.btn_mas.setToolTip("Aumentar cantidad")
        self.btn_mas.clicked.connect(self._aumentar_cantidad)
        controles.addWidget(self.btn_mas)

        self.btn_menos = QPushButton("-")
        self.btn_menos.setObjectName("btnIcono")
        self.btn_menos.setFixedWidth(40)
        self.btn_menos.setToolTip("Disminuir cantidad")
        self.btn_menos.clicked.connect(self._disminuir_cantidad)
        controles.addWidget(self.btn_menos)

        layout.addWidget(self.controles_frame)

        # --- Acciones de carrito ---
        fila_acciones = QHBoxLayout()
        fila_acciones.setSpacing(8)

        self.btn_aplicar = QPushButton("Aplicar")
        self.btn_aplicar.setObjectName("btnSecundario")
        self.btn_aplicar.setToolTip("Aplicar la cantidad/peso indicada")
        self.btn_aplicar.clicked.connect(self._aplicar_cantidad)
        fila_acciones.addWidget(self.btn_aplicar)

        self.btn_eliminar = QPushButton("Eliminar")
        self.btn_eliminar.setObjectName("btnPeligro")
        self.btn_eliminar.setToolTip("Quitar el producto seleccionado")
        self.btn_eliminar.clicked.connect(self._eliminar_seleccionado)
        fila_acciones.addWidget(self.btn_eliminar)

        self.btn_vaciar = QPushButton("Vaciar Carrito")
        self.btn_vaciar.setObjectName("btnSecundario")
        self.btn_vaciar.clicked.connect(self._vaciar_carrito)
        fila_acciones.addWidget(self.btn_vaciar)

        layout.addLayout(fila_acciones)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("posSeparador")
        layout.addWidget(sep)

        # --- Totales ---
        self.lbl_subtotal = QLabel("Subtotal: $0.00")
        self.lbl_subtotal.setObjectName("lblSubtotal")
        layout.addWidget(self.lbl_subtotal)

        fila_descuento = QHBoxLayout()
        lbl_desc = QLabel("Descuento:")
        lbl_desc.setObjectName("lblCampo")
        fila_descuento.addWidget(lbl_desc)
        self.descuento_spin = QDoubleSpinBox()
        self.descuento_spin.setPrefix("$ ")
        self.descuento_spin.setDecimals(2)
        self.descuento_spin.setRange(0, 999999.99)
        self.descuento_spin.setSingleStep(5)
        self.descuento_spin.setGroupSeparatorShown(True)
        self.descuento_spin.valueChanged.connect(self._actualizar_totales)
        fila_descuento.addWidget(self.descuento_spin, 1)
        layout.addLayout(fila_descuento)

        self.lbl_total = QLabel("Total: $0.00")
        self.lbl_total.setObjectName("lblTotal")
        layout.addWidget(self.lbl_total)

        layout.addStretch()

        # --- Botón cobrar ---
        self.btn_cobrar = QPushButton("Cobrar")
        self.btn_cobrar.setObjectName("btnCobrar")
        self.btn_cobrar.setFixedHeight(52)
        self.btn_cobrar.clicked.connect(self._on_cobrar)
        layout.addWidget(self.btn_cobrar)

        # --- Botón cancelar venta (Fase 14): visible solo con permiso ---
        self.btn_cancelar_venta = QPushButton("Cancelar Venta")
        self.btn_cancelar_venta.setObjectName("btnCancelarVenta")
        self.btn_cancelar_venta.setFixedHeight(42)
        self.btn_cancelar_venta.setToolTip(
            "Reversar una venta por folio: repone el inventario y la "
            "excluye de reportes y cortes."
        )
        self.btn_cancelar_venta.clicked.connect(self._cancelar_venta)
        self.btn_cancelar_venta.setVisible(hay_permiso_actual("cancelar_ventas"))
        layout.addWidget(self.btn_cancelar_venta)

        self._actualizar_estado_controles()
        self._actualizar_totales()

        return panel

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._buscar()
        self.search_edit.setFocus()

    # ------------------------------------------------------------------
    # Búsqueda
    # ------------------------------------------------------------------

    def _buscar(self):
        """Buscar productos activos según el texto ingresado."""
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
            cfg = CONFIG_TIPO.get(producto.tipo_venta, CONFIG_TIPO[TipoVentaEnum.PIEZA])
            stock_txt = formatear_numero(stock, cfg["decimales"]) + f" {cfg['unidad']}"

            valores = [
                producto.codigo,
                producto.nombre,
                formatear_moneda(producto.precio_venta),
                stock_txt,
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col in (2, 3):
                    item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, producto.id)
                self.tabla_resultados.setItem(fila, col, item)

        total = len(self._resultados)
        if total == 1:
            self.lbl_resultados.setText("1 producto encontrado.")
        else:
            self.lbl_resultados.setText(f"{total} productos encontrados.")

        self._actualizar_estado_botones()

    # ------------------------------------------------------------------
    # Lector de código de barras (modo teclado USB)
    # ------------------------------------------------------------------

    def _instalar_filtro_enter(self):
        """
        Capturar la tecla Enter desde cualquier control de este módulo.
        Un lector de códigos de barras en modo teclado USB "teclea" el código
        y envía un Enter sin importar qué control tenga el foco; así el
        escaneo funciona aunque el cajero haya dejado el foco en otro lado.
        """
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Enter global mientras el Punto de Venta esté activo."""
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            foco = QApplication.focusWidget()
            if (
                foco is not None
                and self.isVisible()
                and self.isAncestorOf(foco)
                and foco.window() is self.window()  # sin diálogos encima (pago, etc.)
            ):
                # Los controles de cantidad/descuento usan Enter para confirmar su valor.
                if foco in (self.cantidad_spin, self.descuento_spin):
                    return super().eventFilter(obj, event)
                self._manejar_enter()
                event.accept()
                return True
        return super().eventFilter(obj, event)

    def _manejar_enter(self):
        """
        Acción al presionar Enter (botón 'Agregar' o escaneo del lector):
        1. Si el texto es un código de barras válido -> coincidencia exacta.
        2. Si no, agrega el primer resultado de la búsqueda por nombre.
        3. Si no hay nada, beep + aviso.
        Al final limpia el buscador y le devuelve el foco para escanear en cadena.
        """
        termino = self.search_edit.text().strip()

        producto = self._buscar_por_escaner(termino)
        if producto is not None:
            self._agregar_producto(producto)
        elif self._resultados:
            self.tabla_resultados.selectRow(0)
            self._agregar_seleccionado()
        else:
            self._aviso_no_encontrado(termino)

        self.search_edit.clear()
        self.search_edit.setFocus()

    def _buscar_por_escaner(self, termino):
        """Si el texto parece un código de barras, buscar el producto exacto."""
        normalizado = normalizar_codigo_barras(termino)
        if not normalizado:
            return None
        return self.productos_service.obtener_por_codigo_barras(normalizado)

    def _aviso_no_encontrado(self, termino):
        """Beep + aviso cuando el código escaneado no corresponde a ningún producto."""
        QApplication.beep()
        if termino:
            QMessageBox.warning(
                self,
                "No encontrado",
                f"No hay ningún producto con '{termino}'.\n"
                "Revisa el nombre o el código de barras.",
            )
        else:
            QMessageBox.warning(
                self,
                "Búsqueda vacía",
                "Escribe un nombre o escanea un código de barras.",
            )

    def _resultado_seleccionado(self):
        fila = self.tabla_resultados.currentRow()
        if fila < 0 or fila >= len(self._resultados):
            return None
        return self._resultados[fila]

    # ------------------------------------------------------------------
    # Carrito
    # ------------------------------------------------------------------

    def _agregar_seleccionado(self):
        """Agregar el producto seleccionado de la tabla de resultados."""
        producto = self._resultado_seleccionado()
        if not producto:
            return
        self._agregar_producto(producto)

    def _agregar_producto(self, producto) -> bool:
        """Agregar un producto al carrito respetando su tipo de venta.

        Devuelve True si se agregó; False si no había stock o estaba inactivo.
        """
        if not getattr(producto, "activo", True):
            QApplication.beep()
            QMessageBox.warning(
                self,
                "Producto inactivo",
                f"'{producto.nombre}' está desactivado y no puede venderse.",
            )
            return False

        stock = (
            Decimal(str(producto.inventario.cantidad))
            if producto.inventario is not None
            else Decimal("0")
        )
        cfg = CONFIG_TIPO.get(producto.tipo_venta, CONFIG_TIPO[TipoVentaEnum.PIEZA])

        # Buscar si ya está en el carrito
        existente = next(
            (i for i in self._carrito if i["producto_id"] == producto.id), None
        )

        if existente:
            # Aumentar según el paso del tipo de venta
            nueva = existente["cantidad"] + cfg["paso"]
            if not self._validar_stock(producto, nueva, cfg):
                return False
            existente["cantidad"] = nueva
        else:
            # Cantidad inicial: 1 unidad o un peso base razonable
            inicial = (
                cfg["paso"]
                if producto.tipo_venta in (TipoVentaEnum.KILOGRAMO, TipoVentaEnum.GRAMOS)
                else cfg["minimo"]
            )
            if not self._validar_stock(producto, inicial, cfg):
                return False
            self._carrito.append({
                "producto_id": producto.id,
                "nombre": producto.nombre,
                "tipo_venta": producto.tipo_venta,
                "precio": Decimal(str(producto.precio_venta)),
                "cantidad": inicial,
                "unidad": cfg["unidad"],
            })

        self._refrescar_carrito()
        return True

    def _validar_stock(self, producto, cantidad, cfg) -> bool:
        """Validar que la cantidad no supere el stock disponible."""
        stock = (
            Decimal(str(producto.inventario.cantidad))
            if producto.inventario is not None
            else Decimal("0")
        )
        if cantidad > stock:
            QMessageBox.warning(
                self,
                "Inventario insuficiente",
                f"No hay suficiente stock de '{producto.nombre}'.\n"
                f"Disponible: {formatear_numero(stock, cfg['decimales'])} {cfg['unidad']} "
                f"- Solicitado: {formatear_numero(cantidad, cfg['decimales'])} {cfg['unidad']}",
            )
            return False
        return True

    def _cargar_cantidad_seleccion(self):
        """Al seleccionar una fila del carrito, cargar su cantidad en el spin."""
        fila = self.tabla_carrito.currentRow()
        if fila < 0 or fila >= len(self._carrito):
            return
        item = self._carrito[fila]
        cfg = CONFIG_TIPO.get(item["tipo_venta"], CONFIG_TIPO[TipoVentaEnum.PIEZA])

        self.cantidad_spin.blockSignals(True)
        self.cantidad_spin.setDecimals(cfg["decimales"])
        self.cantidad_spin.setSingleStep(float(cfg["paso"]))
        self.cantidad_spin.setMinimum(float(cfg["minimo"]))
        self.cantidad_spin.setValue(float(item["cantidad"]))
        self.cantidad_spin.blockSignals(False)

        self.lbl_cantidad.setText(f"{cfg['lbl']}:")

    def _item_seleccionado_carrito(self):
        fila = self.tabla_carrito.currentRow()
        if fila < 0 or fila >= len(self._carrito):
            return None, -1
        return self._carrito[fila], fila

    def _aplicar_cantidad(self):
        """Aplicar el valor del spin al producto seleccionado."""
        item, fila = self._item_seleccionado_carrito()
        if item is None:
            QMessageBox.information(self, "Selecciona un producto", "Selecciona un producto del carrito.")
            return
        cfg = CONFIG_TIPO.get(item["tipo_venta"], CONFIG_TIPO[TipoVentaEnum.PIEZA])
        nueva = Decimal(str(self.cantidad_spin.value()))

        producto = self._obtener_producto(item["producto_id"])
        if not self._validar_stock(producto, nueva, cfg):
            return
        item["cantidad"] = nueva
        self._refrescar_carrito()
        self.tabla_carrito.selectRow(fila)

    def _aumentar_cantidad(self):
        item, fila = self._item_seleccionado_carrito()
        if item is None:
            return
        cfg = CONFIG_TIPO.get(item["tipo_venta"], CONFIG_TIPO[TipoVentaEnum.PIEZA])
        nueva = item["cantidad"] + cfg["paso"]
        producto = self._obtener_producto(item["producto_id"])
        if not self._validar_stock(producto, nueva, cfg):
            return
        item["cantidad"] = nueva
        self._refrescar_carrito()
        self.tabla_carrito.selectRow(fila)

    def _disminuir_cantidad(self):
        item, fila = self._item_seleccionado_carrito()
        if item is None:
            return
        cfg = CONFIG_TIPO.get(item["tipo_venta"], CONFIG_TIPO[TipoVentaEnum.PIEZA])
        nueva = item["cantidad"] - cfg["paso"]
        if nueva < cfg["minimo"]:
            nueva = cfg["minimo"]
        item["cantidad"] = nueva
        self._refrescar_carrito()
        self.tabla_carrito.selectRow(fila)

    def _eliminar_seleccionado(self):
        item, fila = self._item_seleccionado_carrito()
        if item is None:
            return
        del self._carrito[fila]
        self._refrescar_carrito()

    def _vaciar_carrito(self):
        if not self._carrito:
            return
        respuesta = QMessageBox.question(
            self,
            "Vaciar carrito",
            "¿Deseas vaciar el carrito de compra?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta == QMessageBox.Yes:
            self._carrito = []
            self._refrescar_carrito()

    def _obtener_producto(self, producto_id):
        return self.productos_service.obtener_por_id(producto_id)

    def _refrescar_carrito(self):
        """Recargar la tabla del carrito y los totales."""
        self.tabla_carrito.setRowCount(0)
        for item in self._carrito:
            fila = self.tabla_carrito.rowCount()
            self.tabla_carrito.insertRow(fila)

            cfg = CONFIG_TIPO.get(item["tipo_venta"], CONFIG_TIPO[TipoVentaEnum.PIEZA])
            subtotal = redondear_moneda(item["cantidad"] * item["precio"])
            cantidad_txt = (
                formatear_numero(item["cantidad"], cfg["decimales"]) + f" {item['unidad']}"
            )

            valores = [
                item["nombre"],
                etiqueta_tipo_venta(item["tipo_venta"]),
                cantidad_txt,
                formatear_moneda(item["precio"]),
                formatear_moneda(subtotal),
            ]
            for col, valor in enumerate(valores):
                celda = QTableWidgetItem(str(valor))
                if col in (2, 3, 4):
                    celda.setTextAlignment(Qt.AlignCenter)
                self.tabla_carrito.setItem(fila, col, celda)

        self._actualizar_totales()
        self._actualizar_estado_controles()

    # ------------------------------------------------------------------
    # Totales
    # ------------------------------------------------------------------

    def _calcular_subtotal(self):
        suma = sum(
            redondear_moneda(item["cantidad"] * item["precio"])
            for item in self._carrito
        )
        return redondear_moneda(suma)

    def _calcular_descuento(self):
        return redondear_moneda(Decimal(str(self.descuento_spin.value())))

    def _calcular_total(self):
        subtotal = self._calcular_subtotal()
        descuento = self._calcular_descuento()
        total = redondear_moneda(subtotal - descuento)
        if total < 0:
            total = Decimal("0")
        return total

    def _actualizar_totales(self):
        subtotal = self._calcular_subtotal()
        descuento = self._calcular_descuento()
        total = self._calcular_total()

        self.lbl_subtotal.setText(f"Subtotal: {formatear_moneda(subtotal)}")
        if descuento > 0:
            self.lbl_subtotal.setText(
                f"Subtotal: {formatear_moneda(subtotal)}  "
                f"(Descuento: -{formatear_moneda(descuento)})"
            )
        self.lbl_total.setText(f"Total: {formatear_moneda(total)}")

    def _actualizar_estado_controles(self):
        """Habilitar/deshabilitar controles según el estado del carrito."""
        tiene_items = bool(self._carrito)
        self.btn_agregar.setEnabled(self.tabla_resultados.currentRow() >= 0)
        self.cantidad_spin.setEnabled(tiene_items)
        self.btn_mas.setEnabled(tiene_items)
        self.btn_menos.setEnabled(tiene_items)
        self.btn_aplicar.setEnabled(tiene_items)
        self.btn_eliminar.setEnabled(tiene_items)
        self.btn_vaciar.setEnabled(tiene_items)
        self.btn_cobrar.setEnabled(tiene_items)

    def _actualizar_estado_botones(self):
        self.btn_agregar.setEnabled(self.tabla_resultados.currentRow() >= 0)

    # ------------------------------------------------------------------
    # Cobrar
    # ------------------------------------------------------------------

    def _on_cobrar(self):
        """Abrir el diálogo de pago y registrar la venta."""
        if not self._carrito:
            QMessageBox.information(
                self, "Carrito vacío", "Agrega productos al carrito antes de cobrar."
            )
            return

        total = self._calcular_total()
        descuento = self._calcular_descuento()

        dialogo = PagoDialog(total, self)
        if not dialogo.exec():
            return

        try:
            items = [
                {"producto_id": item["producto_id"], "cantidad": item["cantidad"]}
                for item in self._carrito
            ]
            venta = self.ventas_service.crear_venta(
                items=items,
                metodo_pago=dialogo.metodo,
                recibido=dialogo.recibido,
                descuento=descuento,
                cliente_id=dialogo.cliente_id if dialogo.metodo == MetodoPagoEnum.FIADO else None,
                usuario_id=obtener_usuario_id(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Error al cobrar", str(e))
            self._refrescar_carrito()
            return

        # Mensaje de éxito
        mensaje = f"Venta {venta.folio} registrada correctamente.\n\nTotal: {formatear_moneda(venta.total)}"
        if dialogo.metodo == MetodoPagoEnum.EFECTIVO and dialogo.cambio > 0:
            mensaje += f"\nCambio: {formatear_moneda(dialogo.cambio)}"
        elif dialogo.metodo == MetodoPagoEnum.FIADO:
            mensaje += "\n\nVenta registrada a crédito (fiado).\nSe creó un registro de deuda para el cliente."

        QMessageBox.information(self, "Venta completada", mensaje)

        # Reiniciar
        self._carrito = []
        self.descuento_spin.setValue(0)
        self._refrescar_carrito()
        self._buscar()
        self.search_edit.clear()
        self.search_edit.setFocus()

    def _cancelar_venta(self):
        """Abrir el diálogo de cancelación de una venta por folio (Fase 14)."""
        dialogo = CancelarVentaDialog(self)
        dialogo.exec()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QWidget#puntoVentaView {
                background-color: #f5f5f5;
            }

            #panelBusqueda, #panelCarrito {
                background-color: #f5f5f5;
            }

            #panelTitulo {
                color: #2c3e50;
                font-size: 17px;
                font-weight: 600;
                padding: 4px 0;
            }

            QLineEdit#posBusqueda {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                color: #2c3e50;
            }

            QLineEdit#posBusqueda:focus {
                border-color: #3498db;
            }

            QTableWidget#posTabla, QTableWidget#carritoTabla {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #dceaf7;
                selection-color: #1a252f;
            }

            QTableWidget#posTabla::item, QTableWidget#carritoTabla::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget#posTabla QHeaderView::section,
            QTableWidget#carritoTabla QHeaderView::section {
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

            #lblCampo {
                color: #2c3e50;
                font-size: 13px;
                font-weight: 500;
            }

            QDoubleSpinBox#cantidadSpin {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                min-height: 22px;
                color: #2c3e50;
            }

            QDoubleSpinBox#cantidadSpin:focus {
                border-color: #3498db;
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

            QPushButton#btnSecundario:disabled {
                background-color: #f5f5f5;
                color: #bdc3c7;
                border-color: #e0e0e0;
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

            QPushButton#btnIcono {
                background-color: #ffffff;
                color: #2c3e50;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                font-size: 16px;
                font-weight: 700;
            }

            QPushButton#btnIcono:hover {
                background-color: #ecf0f1;
                border-color: #95a5a6;
            }

            #posSeparador {
                border: none;
                background-color: #dee2e6;
                max-height: 1px;
            }

            #lblSubtotal {
                color: #7f8c8d;
                font-size: 14px;
                font-weight: 500;
            }

            #lblTotal {
                color: #2c3e50;
                font-size: 24px;
                font-weight: 700;
                padding: 2px 0 8px;
            }

            QPushButton#btnCobrar {
                background-color: #27ae60;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 700;
            }

            QPushButton#btnCobrar:hover {
                background-color: #219a52;
            }

            QPushButton#btnCobrar:disabled {
                background-color: #bdc3c7;
                color: #ecf0f1;
            }

            QPushButton#btnCancelarVenta {
                background-color: transparent;
                color: #c0392b;
                border: 1px solid #e5b8b1;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton#btnCancelarVenta:hover {
                background-color: #fdecea;
                border-color: #d98880;
            }
        """)