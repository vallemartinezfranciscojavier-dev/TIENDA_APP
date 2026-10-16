"""
Vista principal del módulo de Proveedores.
Tabla, búsqueda, filtros, alta, edición y activar/desactivar.
"""

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

from PySide6.QtCore import Qt

from services.proveedores_service import ProveedoresService
from utils.formatters import truncar_texto
from views.proveedores.proveedor_form_dialog import ProveedorFormDialog


class ProveedoresView(QWidget):
    """Vista de administración de proveedores."""

    COLUMNAS = ["Nombre", "Contacto", "Teléfono", "Email", "RFC", "Dirección", "Estado"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("proveedoresView")
        self.service = ProveedoresService()
        self._proveedores = []
        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ---- Barra de herramientas ----
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.search_edit = QLineEdit(self)
        self.search_edit.setObjectName("proveedoresBusqueda")
        self.search_edit.setPlaceholderText("Buscar por nombre, contacto o teléfono...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(240)
        self.search_edit.textChanged.connect(self._recargar)
        toolbar.addWidget(self.search_edit, 1)

        self.estado_filtro = QComboBox(self)
        self.estado_filtro.setObjectName("proveedoresFiltro")
        self.estado_filtro.addItem("Todos", "todos")
        self.estado_filtro.addItem("Activos", "activos")
        self.estado_filtro.addItem("Inactivos", "inactivos")
        self.estado_filtro.setMinimumWidth(110)
        self.estado_filtro.currentIndexChanged.connect(self._recargar)
        toolbar.addWidget(self.estado_filtro)

        self.btn_nuevo = QPushButton("Nuevo Proveedor", self)
        self.btn_nuevo.setObjectName("btnPrimario")
        self.btn_nuevo.clicked.connect(self._on_nuevo)
        toolbar.addWidget(self.btn_nuevo)

        layout.addLayout(toolbar)

        # ---- Tabla ----
        self.tabla = QTableWidget(0, len(self.COLUMNAS), self)
        self.tabla.setObjectName("proveedoresTabla")
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
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        self.tabla.itemSelectionChanged.connect(self._actualizar_estado_botones)
        self.tabla.cellDoubleClicked.connect(lambda *_: self._on_editar())
        layout.addWidget(self.tabla, 1)

        # ---- Barra de acciones inferior ----
        acciones = QHBoxLayout()
        acciones.setSpacing(10)

        self.info_label = QLabel("")
        self.info_label.setObjectName("proveedoresInfo")
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
    # Ciclo de vida
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._recargar()

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    def _recargar(self):
        termino = self.search_edit.text()
        estado = self.estado_filtro.currentData() or "todos"

        todos = self.service.obtener_todos(incluir_inactivos=(estado != "activos"))
        self._proveedores = self._filtrar(todos, termino, estado)

        self.tabla.setRowCount(0)
        izq = Qt.AlignLeft | Qt.AlignVCenter
        centro = Qt.AlignCenter

        for prov in self._proveedores:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)

            valores = [
                prov.nombre,
                truncar_texto(prov.contacto, 40) if prov.contacto else "",
                prov.telefono or "",
                truncar_texto(prov.email, 35) if prov.email else "",
                prov.rfc or "",
                truncar_texto(prov.direccion, 40) if prov.direccion else "",
                "Activo" if prov.activo else "Inactivo",
            ]

            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col == 6:
                    item.setTextAlignment(centro)
                else:
                    item.setTextAlignment(izq)
                item.setData(Qt.UserRole, prov.id)
                self.tabla.setItem(fila, col, item)

        total = len(self._proveedores)
        self.info_label.setText(f"Mostrando {total} proveedor{'es' if total != 1 else ''}")
        self._actualizar_estado_botones()

    def _filtrar(self, proveedores, termino, estado):
        """Filtrar proveedores por término de búsqueda y estado."""
        resultado = proveedores
        termino = (termino or "").strip().lower()

        if termino:
            resultado = [
                p for p in resultado
                if termino in (p.nombre or "").lower()
                or termino in (p.contacto or "").lower()
                or termino in (p.telefono or "").lower()
            ]

        if estado == "activos":
            resultado = [p for p in resultado if p.activo]
        elif estado == "inactivos":
            resultado = [p for p in resultado if not p.activo]

        return resultado

    def _proveedor_seleccionado(self):
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._proveedores):
            return None
        return self._proveedores[fila]

    def _actualizar_estado_botones(self):
        prov = self._proveedor_seleccionado()
        tiene_seleccion = prov is not None
        self.btn_editar.setEnabled(tiene_seleccion)
        self.btn_toggle.setEnabled(tiene_seleccion)
        if prov is not None:
            self.btn_toggle.setText("Desactivar" if prov.activo else "Activar")

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _on_nuevo(self):
        dialogo = ProveedorFormDialog(self)
        if dialogo.exec():
            self._recargar()

    def _on_editar(self):
        prov = self._proveedor_seleccionado()
        if not prov:
            return
        dialogo = ProveedorFormDialog(self, proveedor=prov)
        if dialogo.exec():
            self._recargar()

    def _on_toggle(self):
        prov = self._proveedor_seleccionado()
        if not prov:
            return

        if prov.activo:
            respuesta = QMessageBox.question(
                self,
                "Desactivar proveedor",
                f"¿Deseas desactivar el proveedor '{prov.nombre}'?\n"
                "No se eliminará, solo se ocultará de las listas.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if respuesta == QMessageBox.Yes:
                self.service.desactivar(prov.id)
        else:
            respuesta = QMessageBox.question(
                self,
                "Activar proveedor",
                f"¿Deseas activar el proveedor '{prov.nombre}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if respuesta == QMessageBox.Yes:
                self.service.activar(prov.id)

        self._recargar()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QWidget#proveedoresView {
                background-color: #f5f5f5;
            }

            QLineEdit#proveedoresBusqueda {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 7px 10px;
                font-size: 13px;
                color: #2c3e50;
            }

            QLineEdit#proveedoresBusqueda:focus {
                border-color: #3498db;
            }

            QComboBox#proveedoresFiltro {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                color: #2c3e50;
            }

            QComboBox#proveedoresFiltro QAbstractItemView {
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

            QLabel#proveedoresInfo {
                color: #7f8c8d;
                font-size: 12px;
            }

            QTableWidget#proveedoresTabla {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #dceaf7;
                selection-color: #1a252f;
            }

            QTableWidget#proveedoresTabla::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget#proveedoresTabla QHeaderView::section {
                background-color: #2c3e50;
                color: #ffffff;
                padding: 8px 10px;
                border: none;
                font-size: 12px;
                font-weight: 600;
            }
        """)