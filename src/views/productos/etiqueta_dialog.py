"""
Diálogo para imprimir etiquetas de precios con código de barras.

Permite elegir productos y cantidades y genera un PDF con etiquetas de
40 x 25 mm (servicio etiquetas_service).
"""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QStandardPaths
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
    QFileDialog,
)

from services.etiquetas_service import generar_etiquetas
from utils.formatters import formatear_moneda


class EtiquetaDialog(QDialog):
    """Selección de productos y cantidades para imprimir etiquetas."""

    COLS = ["Producto", "Código", "Precio", "Cantidad"]

    def __init__(self, productos, parent=None):
        super().__init__(parent)
        self._productos = list(productos or [])
        self._seleccion = []  # lista de dicts: {"producto", "cantidad"}

        self.setObjectName("etiquetaDialog")
        self.setWindowTitle("Generar etiquetas de precios")
        self.setModal(True)
        self.setMinimumWidth(600)

        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        intro = QLabel(
            "Elige productos y cantidades para imprimir etiquetas de 40x25 mm\n"
            "con nombre, precio y código de barras EAN-13."
        )
        intro.setObjectName("introLabel")
        layout.addWidget(intro)

        # --- Fila para agregar ---
        fila_agregar = QHBoxLayout()
        fila_agregar.setSpacing(8)

        self.combo_producto = QComboBox()
        self.combo_producto.setMinimumWidth(260)
        for p in self._productos:
            codigo = (p.codigo_barras or "").strip()
            texto = p.nombre
            if codigo:
                texto += f"  [{codigo}]"
            else:
                texto += "  (sin código)"
            self.combo_producto.addItem(texto, p)
        if not self._productos:
            self.combo_producto.addItem("(sin productos)", None)
        fila_agregar.addWidget(self.combo_producto, 1)

        self.cantidad_spin = QSpinBox()
        self.cantidad_spin.setRange(1, 999)
        self.cantidad_spin.setValue(1)
        self.cantidad_spin.setPrefix("x ")
        self.cantidad_spin.setToolTip("Cantidad de etiquetas a imprimir por producto")
        fila_agregar.addWidget(self.cantidad_spin)

        self.btn_agregar = QPushButton("Agregar")
        self.btn_agregar.setObjectName("btnSecundario")
        self.btn_agregar.clicked.connect(self._on_agregar)
        fila_agregar.addWidget(self.btn_agregar)

        layout.addLayout(fila_agregar)

        # --- Tabla de selección ---
        self.tabla = QTableWidget(0, len(self.COLS))
        self.tabla.setObjectName("etiquetaTabla")
        self.tabla.setHorizontalHeaderLabels(self.COLS)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        header = self.tabla.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tabla, 1)

        # --- Barra inferior ---
        fila_inferior = QHBoxLayout()

        self.lbl_total = QLabel("0 etiquetas.")
        self.lbl_total.setObjectName("totalLabel")
        fila_inferior.addWidget(self.lbl_total)

        fila_inferior.addStretch()

        self.btn_quitar = QPushButton("Quitar seleccionado")
        self.btn_quitar.setObjectName("btnSecundario")
        self.btn_quitar.setEnabled(False)
        self.btn_quitar.clicked.connect(self._on_quitar)
        fila_inferior.addWidget(self.btn_quitar)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnSecundario")
        self.btn_cancelar.clicked.connect(self.reject)
        fila_inferior.addWidget(self.btn_cancelar)

        self.btn_generar = QPushButton("Generar PDF")
        self.btn_generar.setObjectName("btnPrimario")
        self.btn_generar.clicked.connect(self._on_generar)
        fila_inferior.addWidget(self.btn_generar)

        layout.addLayout(fila_inferior)

        self._refresh_tabla()

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _on_agregar(self):
        """Agregar a la lista el producto y cantidad elegidos."""
        producto = self.combo_producto.currentData()
        if producto is None:
            return
        self._seleccion.append({
            "producto": producto,
            "cantidad": self.cantidad_spin.value(),
        })
        self._refresh_tabla()

    def _on_quitar(self):
        """Quitar la fila seleccionada."""
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._seleccion):
            QMessageBox.information(
                self, "Selecciona una fila",
                "Selecciona una etiqueta de la lista para quitarla.",
            )
            return
        del self._seleccion[fila]
        self._refresh_tabla()

    def _on_generar(self):
        """Validar y generar el PDF de etiquetas."""
        if not self._seleccion:
            QMessageBox.information(
                self, "Sin etiquetas",
                "Agrega al menos un producto y su cantidad.",
            )
            return

        # Expandir cantidades y omitir productos sin código de barras.
        entradas = []
        omitidos = []
        for item in self._seleccion:
            prod = item["producto"]
            codigo = (prod.codigo_barras or "").strip()
            if not codigo:
                omitidos.append(prod.nombre)
                continue
            por = {
                "nombre": prod.nombre,
                "codigo": codigo,
                "precio": formatear_moneda(prod.precio_venta),
            }
            entradas.extend([por] * item["cantidad"])

        if not entradas:
            QMessageBox.warning(
                self,
                "Sin códigos de barras",
                "Ningún producto seleccionado tiene código de barras.\n\n"
                "Edita el producto y usa el botón 'Generar código' para "
                "asignarle un EAN-13.",
            )
            return

        if omitidos:
            fila = "\n".join(omitidos[:8])
            if len(omitidos) > 8:
                fila += "\n..."
            QMessageBox.information(
                self,
                "Productos omitidos",
                "Se omitieron productos sin código de barras:\n\n" + fila,
            )

        ruta = self._pedir_ruta()
        if ruta is None:
            return

        resultado = generar_etiquetas(entradas, ruta)
        if resultado["exito"]:
            QMessageBox.information(
                self,
                "Etiquetas generadas",
                f"Listo: {resultado['total']} etiqueta(s) generadas.\n"
                f"Ocupan {resultado['hojas']} hoja(s) A4.\n\n"
                f"Archivo: {resultado['ruta']}",
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Error al generar",
                "No se pudieron generar las etiquetas:\n"
                + resultado.get("mensaje", "Error desconocido"),
            )

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _pedir_ruta(self):
        """Pedir la ruta del PDF a guardar (devuelve None si se cancela)."""
        dir_docs = (
            QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
            or str(Path.home())
        )
        nombre = f"etiquetas_{datetime.now():%Y-%m-%d}.pdf"
        ruta, _filtro = QFileDialog.getSaveFileName(
            self,
            "Guardar etiquetas",
            str(Path(dir_docs) / nombre),
            "Documento PDF (*.pdf)",
        )
        if not ruta:
            return None
        if not ruta.lower().endswith(".pdf"):
            ruta += ".pdf"
        return ruta

    def _refresh_tabla(self):
        """Recargar la tabla con la selección actual."""
        self.tabla.setRowCount(0)
        for item in self._seleccion:
            p = item["producto"]
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            codigo = (p.codigo_barras or "").strip() or "—"
            valores = [
                p.nombre,
                codigo,
                formatear_moneda(p.precio_venta),
                str(item["cantidad"]),
            ]
            for col, valor in enumerate(valores):
                celda = QTableWidgetItem(str(valor))
                if col in (1, 2, 3):
                    celda.setTextAlignment(Qt.AlignCenter)
                self.tabla.setItem(fila, col, celda)

        subtotal = sum(i["cantidad"] for i in self._seleccion)
        self.lbl_total.setText(
            f"{len(self._seleccion)} producto(s) · {subtotal} etiqueta(s)."
        )
        self.btn_quitar.setEnabled(bool(self._seleccion))

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog#etiquetaDialog {
                background-color: #f5f5f5;
            }

            QLabel {
                color: #2c3e50;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QLabel#introLabel {
                color: #7f8c8d;
                font-size: 12px;
            }

            QLabel#totalLabel {
                color: #7f8c8d;
                font-size: 12px;
            }

            QComboBox, QSpinBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 13px;
                min-height: 20px;
                color: #2c3e50;
            }

            QComboBox QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #3498db;
                selection-color: #ffffff;
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
                padding: 8px 16px;
                font-size: 13px;
            }

            QPushButton#btnSecundario:hover {
                background-color: #f1f3f5;
                border-color: #95a5a6;
            }

            QTableWidget#etiquetaTabla {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #dceaf7;
                selection-color: #1a252f;
            }

            QTableWidget#etiquetaTabla::item {
                padding: 5px 8px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget#etiquetaTabla QHeaderView::section {
                background-color: #2c3e50;
                color: #ffffff;
                padding: 7px 10px;
                border: none;
                font-size: 12px;
                font-weight: 600;
            }
        """)