"""
Diálogo para cancelar una venta (Fase 14).

Pide el folio de la venta, muestra su resumen y, tras confirmar con un
motivo opcional, llama a VentasService.cancelar_venta. La cancelación
reintegra el inventario, registra movimientos DEVOLUCION y marca la
venta como CANCELADA (queda excluida de reportes y cortes).
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QLabel,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt

from database.models import EstadoVentaEnum
from services.ventas_service import VentasService
from services.seguridad_service import PermisoDenegado
from utils.formatters import formatear_moneda, formatear_fecha


class CancelarVentaDialog(QDialog):
    """Diálogo de cancelación de una venta por folio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = VentasService()
        self._venta = None

        self.setWindowTitle("Cancelar Venta")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setObjectName("cancelarVentaDialog")

        self._setup_ui()
        self._aplicar_estilos()
        self._actualizar_estado()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 26, 26, 26)
        layout.setSpacing(16)

        aviso = QLabel(
            "Cancelar una venta repone el inventario y la excluye de "
            "reportes y cortes. Solo reversa ventas: no afecta abonos ya "
            "registrados en un crédito."
        )
        aviso.setObjectName("lblAvisoCancelar")
        aviso.setWordWrap(True)
        layout.addWidget(aviso)

        # --- Búsqueda por folio ---
        fila_busqueda = QHBoxLayout()
        fila_busqueda.setSpacing(8)
        self.folio_edit = QLineEdit()
        self.folio_edit.setPlaceholderText("Folio de la venta (ej: VTA-000001)")
        self.folio_edit.setObjectName("folioEdit")
        self.folio_edit.returnPressed.connect(self._buscar)
        fila_busqueda.addWidget(self.folio_edit, 1)

        self.btn_buscar = QPushButton("Buscar")
        self.btn_buscar.setObjectName("btnSecundario")
        self.btn_buscar.clicked.connect(self._buscar)
        fila_busqueda.addWidget(self.btn_buscar)
        layout.addLayout(fila_busqueda)

        # --- Resumen de la venta encontrada ---
        self.lbl_info = QLabel("Ingresa el folio y presiona Buscar.")
        self.lbl_info.setObjectName("lblInfoVenta")
        self.lbl_info.setWordWrap(True)
        layout.addWidget(self.lbl_info)

        form = QFormLayout()
        form.setSpacing(12)
        self.motivo_edit = QLineEdit()
        self.motivo_edit.setPlaceholderText("Motivo de la cancelación (opcional)")
        self.motivo_edit.setMaxLength(200)
        form.addRow("Motivo:", self.motivo_edit)
        layout.addLayout(form)

        botones = QHBoxLayout()
        botones.addStretch()
        btn_cancelar = QPushButton("Cerrar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.clicked.connect(self.reject)

        self.btn_confirmar = QPushButton("Cancelar Venta")
        self.btn_confirmar.setObjectName("btnPeligro")
        self.btn_confirmar.clicked.connect(self._confirmar)

        botones.addWidget(btn_cancelar)
        botones.addWidget(self.btn_confirmar)
        layout.addLayout(botones)

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------

    def _buscar(self):
        """Buscar la venta por folio y mostrar su resumen."""
        venta = self.service.buscar_por_folio(self.folio_edit.text())
        if not venta:
            self._venta = None
            self.lbl_info.setText("No se encontró una venta con ese folio.")
            QMessageBox.warning(self, "Venta no encontrada", "No se encontró una venta con ese folio.")
            self._actualizar_estado()
            return

        self._venta = venta
        estado = venta.estado.value if hasattr(venta.estado, "value") else venta.estado
        self.lbl_info.setText(
            "<b>Folio:</b> %s<br>"
            "<b>Fecha:</b> %s<br>"
            "<b>Total:</b> %s<br>"
            "<b>Método:</b> %s<br>"
            "<b>Estado:</b> %s"
            % (
                venta.folio,
                formatear_fecha(venta.fecha, "%d/%m/%Y %H:%M"),
                formatear_moneda(venta.total),
                (venta.metodo_pago.value if hasattr(venta.metodo_pago, "value") else venta.metodo_pago),
                estado,
            )
        )
        self._actualizar_estado()

    def _actualizar_estado(self):
        """Habilitar/deshabilitar el botón de confirmación según la venta."""
        venta = self._venta
        if venta is None:
            self.btn_confirmar.setEnabled(False)
            return
        ya_cancelada = venta.estado == EstadoVentaEnum.CANCELADA
        self.btn_confirmar.setEnabled(not ya_cancelada)
        if ya_cancelada:
            self.lbl_info.setText(
                self.lbl_info.text() + "<br><b>Esta venta ya fue cancelada.</b>"
            )

    def _confirmar(self):
        if self._venta is None:
            return
        motivo = self.motivo_edit.text().strip()
        respuesta = QMessageBox.question(
            self,
            "Confirmar cancelación",
            f"¿Cancelar la venta {self._venta.folio} por "
            f"{formatear_moneda(self._venta.total)}?\n"
            "El inventario de los productos se repondrá.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return

        try:
            self.service.cancelar_venta(self._venta.id, motivo=motivo)
        except PermisoDenegado as e:
            QMessageBox.warning(self, "Permiso denegado", str(e))
            return
        except ValueError as e:
            QMessageBox.warning(self, "No se pudo cancelar", str(e))
            return
        QMessageBox.information(
            self,
            "Venta cancelada",
            f"La venta {self._venta.folio} fue cancelada y el inventario se repuso.",
        )
        self.accept()

    # ------------------------------------------------------------------
    # Estilo
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet(
            """
            QDialog#cancelarVentaDialog {
                background-color: #F4F6F8;
            }
            QLabel#lblAvisoCancelar {
                color: #7F8C8D;
                font-size: 12px;
            }
            QLabel#lblInfoVenta {
                background-color: #FFFFFF;
                border: 1px solid #D0D5DB;
                border-radius: 8px;
                padding: 12px;
                color: #2C3E50;
                font-size: 13px;
            }
            QLineEdit {
                padding: 8px 10px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background: #FFFFFF;
                font-size: 13px;
            }
            QPushButton#btnPrimario, QPushButton#btnSecundario, QPushButton#btnPeligro {
                padding: 8px 18px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#btnPrimario {
                background: #2C7BE5; color: white;
            }
            QPushButton#btnPrimario:hover { background: #1E6FD9; }
            QPushButton#btnSecundario {
                background: #FFFFFF; color: #475569; border: 1px solid #CBD5E1;
            }
            QPushButton#btnSecundario:hover { background: #F1F5F9; }
            QPushButton#btnPeligro {
                background: #E74C3C; color: white;
            }
            QPushButton#btnPeligro:hover { background: #C0392B; }
            QPushButton#btnPeligro:disabled {
                background: #F3B8B2; color: #FFFFFF;
            }
            """
        )