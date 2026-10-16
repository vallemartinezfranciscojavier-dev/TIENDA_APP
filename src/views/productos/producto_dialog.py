"""
Diálogo para crear o editar un producto.
"""

from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QCheckBox,
    QLabel,
    QPushButton,
    QMessageBox,
    QFrame,
)
from PySide6.QtCore import Qt

from database.models import TipoVentaEnum
from services.productos_service import ProductosService
from utils.barcode import generar_ean13
from utils.formatters import formatear_numero


# Tipos de venta disponibles (texto visible, valor del enum)
TIPOS_VENTA_DIALOGO = [
    ("Por pieza", TipoVentaEnum.PIEZA),
    ("Por kilogramo", TipoVentaEnum.KILOGRAMO),
    ("Por gramos", TipoVentaEnum.GRAMOS),
    ("Por bolsa", TipoVentaEnum.BOLSA),
    ("Por unidad", TipoVentaEnum.UNIDAD_PERSONALIZADA),
]


def etiqueta_tipo_venta(tipo_venta) -> str:
    """Obtener la etiqueta legible de un tipo de venta."""
    for etiqueta, valor in TIPOS_VENTA_DIALOGO:
        if valor == tipo_venta:
            return etiqueta
    return str(tipo_venta)


class ProductoDialog(QDialog):
    """Diálogo para crear o editar un producto."""

    def __init__(self, parent=None, producto=None):
        super().__init__(parent)
        self.producto = producto
        self.es_edicion = producto is not None
        self.service = ProductosService()

        self.setObjectName("productoDialog")
        self.setWindowTitle("Editar Producto" if self.es_edicion else "Nuevo Producto")
        self.setModal(True)
        self.setMinimumWidth(480)

        self._setup_ui()
        self._aplicar_estilos()
        self._cargar_datos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _crear_spin(self, decimales: int = 2, minimo: float = 0, maximo: float = 99999999.999):
        """Crear un QDoubleSpinBox configurado."""
        spin = QDoubleSpinBox(self)
        spin.setDecimals(decimales)
        spin.setRange(minimo, maximo)
        spin.setSingleStep(1 if decimales == 0 else 0.1 ** decimales)
        spin.setGroupSeparatorShown(True)
        return spin

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Formulario
        form = QFormLayout()
        form.setSpacing(10)

        self.nombre_edit = QLineEdit(self)
        self.nombre_edit.setPlaceholderText("Ej: Chile Guajillo")
        self.nombre_edit.setMaxLength(200)
        form.addRow("Nombre *:", self.nombre_edit)

        # Código de barras con botón para generar un EAN-13 automáticamente.
        fila_barras = QHBoxLayout()
        fila_barras.setSpacing(6)
        self.barras_edit = QLineEdit(self)
        self.barras_edit.setPlaceholderText("Opcional - Ej: 7501234567890")
        self.barras_edit.setMaxLength(13)
        fila_barras.addWidget(self.barras_edit, 1)
        self.btn_generar_codigo = QPushButton("Generar código", self)
        self.btn_generar_codigo.setObjectName("btnSecundario")
        self.btn_generar_codigo.setToolTip(
            "Generar un código de barras EAN-13 válido con prefijo 750 (México)."
        )
        self.btn_generar_codigo.clicked.connect(self._generar_codigo_barras)
        fila_barras.addWidget(self.btn_generar_codigo)
        form.addRow("Código de barras:", fila_barras)

        self.categoria_combo = QComboBox(self)
        self._cargar_categorias()
        form.addRow("Categoría *:", self.categoria_combo)

        self.tipo_venta_combo = QComboBox(self)
        for etiqueta, valor in TIPOS_VENTA_DIALOGO:
            self.tipo_venta_combo.addItem(etiqueta, valor)
        form.addRow("Tipo de venta *:", self.tipo_venta_combo)

        self.precio_compra_spin = self._crear_spin(decimales=2)
        self.precio_compra_spin.setPrefix("$ ")
        form.addRow("Precio de compra:", self.precio_compra_spin)

        self.precio_venta_spin = self._crear_spin(decimales=2)
        self.precio_venta_spin.setPrefix("$ ")
        form.addRow("Precio de venta *:", self.precio_venta_spin)

        # Bloque de stock (cambia según modo)
        self.stock_spin = self._crear_spin(decimales=3)

        if self.es_edicion:
            self.stock_actual_label = QLabel("Stock actual: --")
            self.stock_actual_label.setObjectName("stockActualLabel")
            self.stock_spin.setToolTip(
                "Si cambias este valor se registrará un movimiento de inventario (ajuste)."
            )

            self.stock_frame = QFrame(self)
            stock_layout = QVBoxLayout(self.stock_frame)
            stock_layout.setContentsMargins(0, 0, 0, 0)
            stock_layout.setSpacing(4)
            stock_layout.addWidget(self.stock_actual_label)
            stock_layout.addWidget(self.stock_spin)

            form.addRow("Ajustar stock a (ajuste):", self.stock_frame)
        else:
            form.addRow("Stock inicial:", self.stock_spin)

        self.stock_minimo_spin = self._crear_spin(decimales=3)
        form.addRow("Stock mínimo:", self.stock_minimo_spin)

        self.activo_check = QCheckBox("Producto activo", self)
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

    def _cargar_categorias(self):
        """Cargar categorías en el combo desde el servicio."""
        self.categoria_combo.clear()
        self._categorias = self.service.obtener_categorias()
        for cat in self._categorias:
            self.categoria_combo.addItem(cat.nombre, cat.id)
        if self._categorias:
            self.categoria_combo.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    def _cargar_datos(self):
        """Rellenar el formulario con los valores del producto (edición)."""
        if not self.es_edicion:
            return

        p = self.producto
        self.nombre_edit.setText(p.nombre)
        self.barras_edit.setText(p.codigo_barras or "")

        # Categoría
        idx_cat = self.categoria_combo.findData(p.categoria_id)
        if idx_cat >= 0:
            self.categoria_combo.setCurrentIndex(idx_cat)

        # Tipo de venta
        idx_tipo = self.tipo_venta_combo.findData(p.tipo_venta)
        if idx_tipo >= 0:
            self.tipo_venta_combo.setCurrentIndex(idx_tipo)

        precio_compra = float(p.precio_compra) if p.precio_compra is not None else 0.0
        self.precio_compra_spin.setValue(precio_compra)
        self.precio_venta_spin.setValue(float(p.precio_venta or 0))
        self.stock_minimo_spin.setValue(float(p.stock_minimo or 0))
        self.activo_check.setChecked(bool(p.activo))

        # Stock actual y ajuste
        stock_actual = Decimal(str(p.inventario.cantidad)) if p.inventario is not None else Decimal("0")
        self.stock_actual_label.setText(
            f"Stock actual: {formatear_numero(stock_actual, 3)}"
        )
        self.stock_spin.setValue(float(stock_actual))

    # ------------------------------------------------------------------
    # Código de barras
    # ------------------------------------------------------------------

    def _generar_codigo_barras(self):
        """Generar un EAN-13 válido con prefijo 750 (México) y rellenarlo."""
        import random

        base = "750" + "".join(str(random.randint(0, 9)) for _ in range(9))
        self.barras_edit.setText(generar_ean13(base))
        self.barras_edit.setFocus()

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------

    def _guardar(self):
        """Validar y guardar el producto."""
        # Validaciones previas
        nombre = self.nombre_edit.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Datos inválidos", "El nombre del producto es obligatorio.")
            self.nombre_edit.setFocus()
            return

        if not self.categoria_combo.currentData():
            QMessageBox.warning(self, "Datos inválidos", "Selecciona una categoría.")
            return

        if self.precio_venta_spin.value() <= 0:
            QMessageBox.warning(self, "Datos inválidos", "El precio de venta debe ser mayor a cero.")
            self.precio_venta_spin.setFocus()
            return

        datos = {
            "nombre": nombre,
            "codigo_barras": self.barras_edit.text().strip(),
            "categoria_id": self.categoria_combo.currentData(),
            "tipo_venta": self.tipo_venta_combo.currentData(),
            "precio_venta": self.precio_venta_spin.value(),
            "precio_compra": self.precio_compra_spin.value(),
            "stock_minimo": self.stock_minimo_spin.value(),
            "activo": self.activo_check.isChecked(),
        }

        try:
            if self.es_edicion:
                # Ajuste de stock manual: solo si el valor cambió
                nuevo_stock = None
                stock_actual = (
                    Decimal(str(self.producto.inventario.cantidad))
                    if self.producto.inventario is not None
                    else Decimal("0")
                )
                if Decimal(str(self.stock_spin.value())) != stock_actual:
                    nuevo_stock = self.stock_spin.value()
                self.service.actualizar(self.producto.id, datos, nuevo_stock=nuevo_stock)
            else:
                datos["stock_inicial"] = self.stock_spin.value()
                self.service.crear(datos)
        except ValueError as e:
            QMessageBox.warning(self, "Datos inválidos", str(e))
            return

        self.accept()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        """Estilos del diálogo (profesionales, consistentes con la app)."""
        self.setStyleSheet("""
            QDialog#productoDialog {
                background-color: #f5f5f5;
            }

            QLabel {
                color: #2c3e50;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QLabel#stockActualLabel {
                color: #7f8c8d;
                font-size: 12px;
                font-style: italic;
            }

            QLineEdit, QComboBox, QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                min-height: 22px;
                color: #2c3e50;
            }

            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {
                border-color: #3498db;
            }

            QComboBox::drop-down {
                border: none;
                width: 24px;
            }

            QComboBox QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #3498db;
                selection-color: #ffffff;
                border: 1px solid #cbd5e0;
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

            QCheckBox {
                color: #2c3e50;
                font-size: 13px;
            }
        """)