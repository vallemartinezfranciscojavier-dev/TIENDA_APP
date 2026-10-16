"""
Vista del módulo de Corte de Caja.
Muestra las ventas esperadas por método de pago, permite abrir la caja,
ingresar el dinero físico contado y guardar el corte con su diferencia.
"""

from decimal import Decimal, InvalidOperation

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFrame,
    QMessageBox,
)
from PySide6.QtCore import Qt

from services.cortes_caja_service import CortesCajaService
from utils.formatters import (
    formatear_moneda,
    formatear_numero,
    formatear_fecha_hora,
)
from utils.calculations import redondear_moneda


class CorteCajaView(QWidget):
    """Vista de control diario de caja."""

    METODOS_COLS = ["Método de pago", "Esperado"]
    HISTORIAL_COLS = ["Fecha", "Usuario", "Esperado", "Contado", "Diferencia"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("corteCajaView")
        self.cortes_service = CortesCajaService()
        self._corte_actual = None
        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        # --- Panel de estado de caja ---
        self.panel_caja = QFrame()
        self.panel_caja.setObjectName("panelCaja")
        panel_layout = QHBoxLayout(self.panel_caja)
        panel_layout.setContentsMargins(16, 12, 16, 12)
        panel_layout.setSpacing(16)

        self.estado_label = QLabel("Caja: Sin abrir")
        self.estado_label.setObjectName("estadoCaja")
        self.estado_label.setProperty("abierta", False)
        panel_layout.addWidget(self.estado_label)

        self.info_caja_label = QLabel("")
        self.info_caja_label.setObjectName("infoCajaLabel")
        panel_layout.addWidget(self.info_caja_label, 1)

        self.monto_inicial_edit = QLineEdit()
        self.monto_inicial_edit.setObjectName("campoCaja")
        self.monto_inicial_edit.setPlaceholderText("Monto inicial")
        self.monto_inicial_edit.setFixedWidth(130)
        self.monto_inicial_edit.setAlignment(Qt.AlignRight)
        panel_layout.addWidget(self.monto_inicial_edit)

        self.btn_abrir = QPushButton("Abrir Caja")
        self.btn_abrir.setObjectName("btnPrimario")
        self.btn_abrir.clicked.connect(self._on_abrir_caja)
        panel_layout.addWidget(self.btn_abrir)

        layout.addWidget(self.panel_caja)

        # --- Resumen esperado por método ---
        resumen_frame = QFrame()
        resumen_frame.setObjectName("resumenCaja")
        resumen_layout = QVBoxLayout(resumen_frame)
        resumen_layout.setContentsMargins(16, 14, 16, 16)
        resumen_layout.setSpacing(10)

        resumen_titulo = QLabel("Ventas del día (esperado)")
        resumen_titulo.setObjectName("tituloSeccion")
        resumen_layout.addWidget(resumen_titulo)

        self.tabla_resumen = QTableWidget(0, len(self.METODOS_COLS))
        self.tabla_resumen.setObjectName("tablaCaja")
        self.tabla_resumen.setHorizontalHeaderLabels(self.METODOS_COLS)
        self.tabla_resumen.verticalHeader().setVisible(False)
        self.tabla_resumen.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla_resumen.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_resumen.setAlternatingRowColors(True)
        self.tabla_resumen.setShowGrid(False)
        self.tabla_resumen.setMaximumHeight(190)
        hdr = self.tabla_resumen.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        resumen_layout.addWidget(self.tabla_resumen)

        total_row = QHBoxLayout()
        total_row.addStretch(1)
        total_etiqueta = QLabel("Total esperado:")
        total_etiqueta.setObjectName("totalEtiqueta")
        total_row.addWidget(total_etiqueta)
        self.total_label = QLabel(formatear_moneda(0))
        self.total_label.setObjectName("totalValor")
        total_row.addWidget(self.total_label)
        resumen_layout.addLayout(total_row)

        layout.addWidget(resumen_frame)

        # --- Panel de cierre ---
        self.panel_cierre = QFrame()
        self.panel_cierre.setObjectName("panelCierre")
        cierre_layout = QGridLayout(self.panel_cierre)
        cierre_layout.setContentsMargins(16, 12, 16, 12)
        cierre_layout.setSpacing(10)

        contado_label = QLabel("Dinero físico contado:")
        contado_label.setObjectName("campoEtiqueta")
        cierre_layout.addWidget(contado_label, 0, 0)

        self.contado_edit = QLineEdit()
        self.contado_edit.setObjectName("campoCaja")
        self.contado_edit.setPlaceholderText("0.00")
        self.contado_edit.setAlignment(Qt.AlignRight)
        self.contado_edit.setFixedWidth(160)
        cierre_layout.addWidget(self.contado_edit, 0, 1)

        self.btn_guardar = QPushButton("Guardar Corte")
        self.btn_guardar.setObjectName("btnPrimario")
        self.btn_guardar.clicked.connect(self._on_guardar_corte)
        cierre_layout.addWidget(self.btn_guardar, 0, 2)

        obs_label = QLabel("Observaciones:")
        obs_label.setObjectName("campoEtiqueta")
        cierre_layout.addWidget(obs_label, 1, 0)

        self.observaciones_edit = QTextEdit()
        self.observaciones_edit.setObjectName("obsCaja")
        self.observaciones_edit.setPlaceholderText("Notas opcionales del corte...")
        self.observaciones_edit.setFixedHeight(64)
        cierre_layout.addWidget(self.observaciones_edit, 1, 1, 1, 2)

        layout.addWidget(self.panel_cierre)

        # --- Historial de cortes ---
        historial_titulo = QLabel("Últimos cortes")
        historial_titulo.setObjectName("tituloSeccion")
        layout.addWidget(historial_titulo)

        self.tabla_historial = QTableWidget(0, len(self.HISTORIAL_COLS))
        self.tabla_historial.setObjectName("tablaCaja")
        self.tabla_historial.setHorizontalHeaderLabels(self.HISTORIAL_COLS)
        self.tabla_historial.verticalHeader().setVisible(False)
        self.tabla_historial.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla_historial.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_historial.setAlternatingRowColors(True)
        self.tabla_historial.setShowGrid(False)
        hhdr = self.tabla_historial.horizontalHeader()
        hhdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hhdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hhdr.setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tabla_historial, 1)

        self._estado_inicial_controles()

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._recargar()

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------

    def _recargar(self):
        self._corte_actual = self.cortes_service.obtener_corte_abierto()
        self._cargar_estado()
        self._cargar_resumen()
        self._cargar_historial()

    def _cargar_estado(self):
        corte = self._corte_actual
        if corte is not None:
            self.estado_label.setText("Caja: ABIERTA")
            self.estado_label.setProperty("abierta", True)
            apertura = formatear_fecha_hora(corte.fecha_apertura)
            self.info_caja_label.setText(
                f"Apertura: {apertura}  ·  Fondo inicial: "
                f"{formatear_moneda(corte.monto_inicial)}"
            )
            self.btn_abrir.setEnabled(False)
            self.monto_inicial_edit.setEnabled(False)
            self.btn_guardar.setEnabled(True)
            self.contado_edit.setEnabled(True)
            self.observaciones_edit.setEnabled(True)
            self.contado_edit.setText(
                formatear_numero(corte.monto_final_real or 0, 2)
            )
        else:
            self.estado_label.setText("Caja: Sin abrir")
            self.estado_label.setProperty("abierta", False)
            self.info_caja_label.setText("Abre la caja para iniciar el día.")
            self.btn_abrir.setEnabled(True)
            self.monto_inicial_edit.setEnabled(True)
            self.btn_guardar.setEnabled(False)
            self.contado_edit.setEnabled(False)
            self.observaciones_edit.setEnabled(False)
            self.contado_edit.setText("")
        # Refrescar estilos del indicador de estado
        self.estado_label.style().unpolish(self.estado_label)
        self.estado_label.style().polish(self.estado_label)

    def _cargar_resumen(self):
        resumen = self.cortes_service.obtener_resumen(self._corte_actual)
        total = self.cortes_service.total_esperado(resumen)

        self.tabla_resumen.setRowCount(0)
        for metodo, etiqueta in self.cortes_service.METODOS_CORTE:
            fila = self.tabla_resumen.rowCount()
            self.tabla_resumen.insertRow(fila)
            self.tabla_resumen.setItem(fila, 0, QTableWidgetItem(etiqueta))
            monto_item = QTableWidgetItem(formatear_moneda(resumen.get(metodo, 0)))
            monto_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tabla_resumen.setItem(fila, 1, monto_item)

        self.total_label.setText(formatear_moneda(total))

    def _cargar_historial(self):
        cortes = self.cortes_service.obtener_cortes(limite=10)

        self.tabla_historial.setRowCount(0)
        for c in cortes:
            fila = self.tabla_historial.rowCount()
            self.tabla_historial.insertRow(fila)

            usuario = c.usuario.nombre if c.usuario else "—"
            fecha_cierre = c.fecha_cierre or c.fecha_apertura
            diferencia = Decimal(str(c.diferencia or 0))

            valores = [
                formatear_fecha_hora(fecha_cierre),
                usuario,
                formatear_moneda(c.monto_final_sistema),
                formatear_moneda(c.monto_final_real),
                formatear_moneda(diferencia),
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col in (2, 3, 4):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col == 4:
                    if diferencia < 0:
                        item.setForeground(Qt.red)
                    elif diferencia > 0:
                        item.setForeground(Qt.darkGreen)
                self.tabla_historial.setItem(fila, col, item)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _parsear_monto(self, texto: str) -> Decimal:
        """Convertir el texto a Decimal (quita $, comas y espacios)."""
        limpio = (texto or "").strip().replace("$", "").replace(",", "").replace(" ", "")
        if not limpio:
            return Decimal("0")
        return Decimal(limpio)

    def _preguntar_duplicado(self) -> bool:
        """Si ya hay un corte cerrado hoy, pedir confirmación antes de continuar."""
        existe_hoy = False
        try:
            existe_hoy = self.cortes_service.existe_corte_cerrado_hoy()
        except Exception:
            existe_hoy = False
        if not existe_hoy:
            return True
        reply = QMessageBox.question(
            self,
            "Corte duplicado",
            "Ya existe un corte cerrado el día de hoy.\n"
            "¿Desea continuar de todas formas?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def _on_abrir_caja(self):
        try:
            monto_inicial = self._parsear_monto(self.monto_inicial_edit.text())
        except (InvalidOperation, ValueError):
            QMessageBox.warning(
                self, "Monto inválido", "Ingresa un monto inicial válido."
            )
            return

        if not self._preguntar_duplicado():
            return

        try:
            self.cortes_service.abrir_corte(monto_inicial)
            self.monto_inicial_edit.setText("")
            self._recargar()
        except ValueError as e:
            QMessageBox.warning(self, "No se pudo abrir la caja", str(e))

    def _on_guardar_corte(self):
        try:
            contado = self._parsear_monto(self.contado_edit.text())
        except (InvalidOperation, ValueError):
            QMessageBox.warning(
                self, "Monto inválido", "Ingresa el dinero contado de forma válida."
            )
            return

        if not self._preguntar_duplicado():
            return

        observaciones = self.observaciones_edit.toPlainText().strip() or None

        try:
            corte = self.cortes_service.cerrar_corte(
                contado,
                observaciones=observaciones,
            )
        except ValueError as e:
            QMessageBox.warning(self, "No se pudo guardar el corte", str(e))
            return

        self.observaciones_edit.clear()
        QMessageBox.information(
            self,
            "Corte guardado",
            "Corte registrado correctamente.\n\n"
            f"Esperado: {formatear_moneda(corte.monto_final_sistema)}\n"
            f"Contado: {formatear_moneda(corte.monto_final_real)}\n"
            f"Diferencia: {formatear_moneda(corte.diferencia)}",
        )
        self._recargar()

    # ------------------------------------------------------------------
    # Estado inicial de controles
    # ------------------------------------------------------------------

    def _estado_inicial_controles(self):
        self.btn_guardar.setEnabled(False)
        self.contado_edit.setEnabled(False)
        self.observaciones_edit.setEnabled(False)

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QWidget#corteCajaView {
                background-color: #f5f5f5;
            }

            QFrame#panelCaja {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }

            QLabel#estadoCaja {
                font-size: 15px;
                font-weight: 700;
                color: #7f8c8d;
            }

            QLabel#estadoCaja[abierta="true"] {
                color: #27ae60;
            }

            QLabel#infoCajaLabel {
                color: #7f8c8d;
                font-size: 13px;
            }

            QFrame#resumenCaja, QFrame#panelCierre {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }

            QLabel#tituloSeccion {
                color: #2c3e50;
                font-size: 14px;
                font-weight: 600;
            }

            QLabel#totalEtiqueta {
                color: #2c3e50;
                font-size: 14px;
                font-weight: 600;
            }

            QLabel#totalValor {
                color: #3498db;
                font-size: 18px;
                font-weight: 700;
            }

            QLabel#campoEtiqueta {
                color: #2c3e50;
                font-size: 13px;
            }

            QLineEdit#campoCaja {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 7px 10px;
                font-size: 13px;
                color: #2c3e50;
            }

            QLineEdit#campoCaja:focus {
                border-color: #3498db;
            }

            QLineEdit#campoCaja:disabled {
                background-color: #f1f3f5;
                color: #bdc3c7;
            }

            QTextEdit#obsCaja {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
                color: #2c3e50;
            }

            QTextEdit#obsCaja:focus {
                border-color: #3498db;
            }

            QTableWidget#tablaCaja {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #dceaf7;
                selection-color: #1a252f;
            }

            QTableWidget#tablaCaja::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget#tablaCaja QHeaderView::section {
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
        """)