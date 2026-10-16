"""
Vista del Dashboard principal.
Muestra indicadores del negocio: ventas del día, productos con stock bajo,
productos más vendidos, últimas ventas y gráficas.
"""

from decimal import Decimal

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QBarSeries,
    QBarSet,
    QBarCategoryAxis,
    QValueAxis,
)

from database.models import MetodoPagoEnum
from services.dashboard_service import DashboardService
from utils.calculations import redondear_moneda
from utils.formatters import formatear_moneda, formatear_numero, formatear_hora

# Etiquetas de método de pago
ETIQUETA_METODO = {
    MetodoPagoEnum.EFECTIVO: "Efectivo",
    MetodoPagoEnum.TARJETA: "Tarjeta",
    MetodoPagoEnum.TRANSFERENCIA: "Transferencia",
    MetodoPagoEnum.FIADO: "Fiado",
}

# Colores de la paleta profesional
COLOR_PRIMARIO = "#3498db"
COLOR_VERDE = "#27ae60"
COLOR_MORADO = "#9b59b6"
COLOR_ROJO = "#e74c3c"


class DashboardView(QWidget):
    """Vista principal del Dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardView")
        self.service = DashboardService()
        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Encabezado
        titulo = QLabel("Dashboard")
        titulo.setObjectName("dashboardTitulo")
        layout.addWidget(titulo)

        # Fila de tarjetas de estadísticas
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(16)
        self._card_ventas = self._crear_tarjeta("Ventas de Hoy", "$0.00", COLOR_VERDE)
        self._card_tickets = self._crear_tarjeta("Tickets Hoy", "0", COLOR_PRIMARIO)
        self._card_stock = self._crear_tarjeta("Stock Bajo", "0", COLOR_ROJO)
        self._card_productos = self._crear_tarjeta("Productos Activos", "0", COLOR_MORADO)
        self.cards_layout.addWidget(self._card_ventas)
        self.cards_layout.addWidget(self._card_tickets)
        self.cards_layout.addWidget(self._card_stock)
        self.cards_layout.addWidget(self._card_productos)
        layout.addLayout(self.cards_layout)

        # Fila de gráficas
        graficas = QHBoxLayout()
        graficas.setSpacing(16)

        self.grafica_ventas = self._crear_panel_grafica("Ventas - Últimos 7 días")
        self.grafica_mas_vendidos = self._crear_panel_grafica("Productos Más Vendidos")

        graficas.addWidget(self.grafica_ventas)
        graficas.addWidget(self.grafica_mas_vendidos)
        layout.addLayout(graficas)

        # Fila de paneles inferiores
        paneles = QHBoxLayout()
        paneles.setSpacing(16)

        self.panel_stock = self._crear_panel_lista("Productos con Inventario Bajo")
        self.panel_ventas = self._crear_panel_ultimas_ventas()

        paneles.addWidget(self.panel_stock)
        paneles.addWidget(self.panel_ventas, 2)
        layout.addLayout(paneles, 1)

    # ------------------------------------------------------------------
    # Componentes
    # ------------------------------------------------------------------

    def _crear_tarjeta(self, titulo: str, valor: str, color: str) -> QFrame:
        """Crear tarjeta de estadística."""
        tarjeta = QFrame()
        tarjeta.setObjectName("statCard")
        tarjeta.setFixedHeight(104)

        layout = QVBoxLayout(tarjeta)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setObjectName("statTitulo")
        layout.addWidget(lbl_titulo)

        lbl_valor = QLabel(valor)
        lbl_valor.setObjectName("statValor")
        lbl_valor.setStyleSheet(f"color: {color};")
        layout.addWidget(lbl_valor)

        layout.addStretch()

        tarjeta.lbl_valor = lbl_valor  # type: ignore
        return tarjeta

    def _crear_panel_grafica(self, titulo: str) -> QFrame:
        """Contenedor para una gráfica con título."""
        panel = QFrame()
        panel.setObjectName("panelDash")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        lbl = QLabel(titulo)
        lbl.setObjectName("panelTitulo")
        layout.addWidget(lbl)

        chart_view = QChartView()
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setMinimumHeight(180)
        layout.addWidget(chart_view, 1)

        panel.chart_view = chart_view  # type: ignore
        return panel

    def _crear_panel_lista(self, titulo: str) -> QFrame:
        """Panel con lista de texto (productos con stock bajo)."""
        panel = QFrame()
        panel.setObjectName("panelDash")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        lbl = QLabel(titulo)
        lbl.setObjectName("panelTitulo")
        layout.addWidget(lbl)

        self.lista_stock = QTableWidget(0, 3)
        self.lista_stock.setObjectName("dashTabla")
        self.lista_stock.setHorizontalHeaderLabels(["Producto", "Stock", "Mínimo"])
        self.lista_stock.verticalHeader().setVisible(False)
        self.lista_stock.setSelectionMode(QAbstractItemView.NoSelection)
        self.lista_stock.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lista_stock.setShowGrid(False)
        hdr = self.lista_stock.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.lista_stock, 1)

        return panel

    def _crear_panel_ultimas_ventas(self) -> QFrame:
        """Panel con tabla de últimas ventas."""
        panel = QFrame()
        panel.setObjectName("panelDash")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        lbl = QLabel("Últimas Ventas")
        lbl.setObjectName("panelTitulo")
        layout.addWidget(lbl)

        self.tabla_ventas = QTableWidget(0, 3)
        self.tabla_ventas.setObjectName("dashTabla")
        self.tabla_ventas.setHorizontalHeaderLabels(["Hora", "Total", "Método"])
        self.tabla_ventas.verticalHeader().setVisible(False)
        self.tabla_ventas.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla_ventas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_ventas.setShowGrid(False)
        hdr = self.tabla_ventas.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tabla_ventas, 1)

        return panel

    # ------------------------------------------------------------------
    # Gráficas
    # ------------------------------------------------------------------

    def _cargar_grafica_barras(self, panel, categorias: list, valores: list, color: str):
        """Llenar una gráfica de barras del panel."""
        chart = QChart()
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().hide()

        serie_datos = QBarSet("Valores")
        serie_datos.setColor(color)
        for v in valores:
            serie_datos.append(float(v))
        serie = QBarSeries()
        serie.append(serie_datos)
        serie.setLabelsVisible(False)
        chart.addSeries(serie)

        eje_x = QBarCategoryAxis()
        eje_x.append([str(c) for c in categorias])
        chart.addAxis(eje_x, Qt.AlignBottom)
        serie.attachAxis(eje_x)

        eje_y = QValueAxis()
        eje_y.setLabelFormat("%d")
        chart.addAxis(eje_y, Qt.AlignLeft)
        serie.attachAxis(eje_y)

        chart_view = panel.chart_view
        chart_view.setChart(chart)

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    def _cargar_datos(self):
        # --- Ventas del día ---
        resumen = self.service.resumen_ventas_hoy()
        self._card_ventas.lbl_valor.setText(formatear_moneda(resumen["total_hoy"]))
        self._card_tickets.lbl_valor.setText(str(resumen["tickets_hoy"]))
        self._card_productos.lbl_valor.setText(str(self.service.productos_activos()))
        self._card_stock.lbl_valor.setText(str(self.service.productos_stock_bajo_count()))

        # --- Productos con stock bajo ---
        stock_bajo = self.service.productos_stock_bajo()
        self.lista_stock.setRowCount(0)
        for p in stock_bajo:
            fila = self.lista_stock.rowCount()
            self.lista_stock.insertRow(fila)
            stock = Decimal(str(p.inventario.cantidad)) if p.inventario is not None else Decimal("0")
            minimo = Decimal(str(p.stock_minimo or 0))
            valores = [p.nombre, formatear_numero(stock, 3), formatear_numero(minimo, 3)]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col in (1, 2):
                    item.setTextAlignment(Qt.AlignCenter)
                self.lista_stock.setItem(fila, col, item)
        if not stock_bajo:
            fila = self.lista_stock.rowCount()
            self.lista_stock.insertRow(fila)
            item = QTableWidgetItem("Sin productos con stock bajo")
            item.setTextAlignment(Qt.AlignCenter)
            self.lista_stock.setItem(fila, 0, item)
            self.lista_stock.setSpan(fila, 0, 1, 3)

        # --- Últimas ventas ---
        ultimas = self.service.ultimas_ventas(10)
        self.tabla_ventas.setRowCount(0)
        for v in ultimas:
            fila = self.tabla_ventas.rowCount()
            self.tabla_ventas.insertRow(fila)
            metodo = ETIQUETA_METODO.get(v.metodo_pago, str(v.metodo_pago))
            valores = [
                formatear_hora(v.fecha),
                formatear_moneda(v.total),
                metodo,
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                if col == 1:
                    item.setTextAlignment(Qt.AlignCenter)
                self.tabla_ventas.setItem(fila, col, item)

        # --- Gráfica: ventas últimos 7 días ---
        dias = self.service.ventas_ultimos_7_dias()
        categorias = [d["fecha"].strftime("%a").capitalize() for d in dias]
        valores = [d["total"] for d in dias]
        self._cargar_grafica_barras(self.grafica_ventas, categorias, valores, COLOR_PRIMARIO)

        # --- Gráfica: productos más vendidos ---
        mas_vendidos = self.service.productos_mas_vendidos(5)
        if mas_vendidos:
            categorias = [truncar(p["nombre"], 12) for p in mas_vendidos]
            valores = [p["cantidad"] for p in mas_vendidos]
        else:
            categorias = ["Sin datos"]
            valores = [0]
        self._cargar_grafica_barras(self.grafica_mas_vendidos, categorias, valores, COLOR_VERDE)

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def showEvent(self, event):
        """Recargar los datos cada vez que se muestra el dashboard."""
        super().showEvent(event)
        self._cargar_datos()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QWidget#dashboardView {
                background-color: #f5f5f5;
            }

            #dashboardTitulo {
                color: #2c3e50;
                font-size: 22px;
                font-weight: 700;
            }

            #statCard {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }

            #statTitulo {
                color: #7f8c8d;
                font-size: 13px;
                font-weight: 500;
            }

            #statValor {
                font-size: 26px;
                font-weight: 700;
            }

            #panelDash {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }

            #panelTitulo {
                color: #2c3e50;
                font-size: 14px;
                font-weight: 600;
            }

            QTableWidget#dashTabla {
                background-color: transparent;
                border: none;
                gridline-color: transparent;
                font-size: 12px;
                color: #2c3e50;
            }

            QTableWidget#dashTabla::item {
                padding: 5px 6px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget#dashTabla QHeaderView::section {
                background-color: #ecf0f1;
                color: #2c3e50;
                padding: 6px 8px;
                border: none;
                font-size: 11px;
                font-weight: 600;
            }
        """)


def truncar(texto: str, max_len: int) -> str:
    """Truncar texto con puntos suspensivos."""
    texto = str(texto)
    if len(texto) <= max_len:
        return texto
    return texto[: max_len - 3] + "..."
