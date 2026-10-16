"""
Vista del módulo de Reportes (Fase 13 — Sistema completo de reportes).

Ofrece 8 reportes seleccionables (ventas, productos vendidos, ganancias,
inventario, compras, clientes y fiado, caja y movimientos de inventario),
cada uno con filtros, tarjetas de resumen dinámicas y una tabla principal.
Permite exportar el reporte activo a Excel y PDF.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QDateEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFrame,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, QDate

from services.reportes_service import ReportesService
from services.proveedores_service import ProveedoresService
from services.exportacion_service import exportar_reporte_excel, exportar_reporte_pdf
from utils.formatters import formatear_moneda, formatear_fecha, formatear_fecha_hora, formatear_porcentaje


# ---- Configuración de periodos ----

PERIODOS = [
    ("Hoy", "hoy"),
    ("Ayer", "ayer"),
    ("Últimos 7 días", "semana"),
    ("Este mes", "mes"),
    ("Mes pasado", "mes_pasado"),
    ("Personalizado", "personalizado"),
]

# Reportes disponibles: (clave, etiqueta)
REPORTES = [
    ("ventas", "Ventas"),
    ("productos", "Productos vendidos"),
    ("ganancias", "Ganancias"),
    ("inventario", "Inventario"),
    ("compras", "Compras"),
    ("fiado", "Clientes y fiado"),
    ("caja", "Caja"),
    ("movimientos", "Movimientos de inventario"),
]

# Filtros secundarios por reporte: (etiqueta, valor)
FILTROS_POR_REPORTE = {
    "productos": [("Más vendido", "mas"), ("Menos vendido", "menos"), ("Mayor ingreso", "ingreso")],
    "compras": None,  # se completa con proveedores reales
    "movimientos": [
        ("Todos los movimientos", ""),
        ("Entradas", "entrada"),
        ("Salidas", "salida"),
        ("Ajustes", "ajuste"),
        ("Devoluciones", "devolucion"),
    ],
}

ETIQUETAS_FILTRO = {
    "productos": "Ordenar:",
    "compras": "Proveedor:",
    "movimientos": "Tipo:",
}


class ReportesView(QWidget):
    """Vista principal del módulo de Reportes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("reportesView")
        self.reportes_service = ReportesService()
        self.proveedores_service = ProveedoresService()
        self._datos = {}
        self._cargando = False
        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 18)
        layout.setSpacing(14)

        # --- Barra de filtros ---
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        lbl_reporte = QLabel("Reporte:")
        lbl_reporte.setObjectName("campoEtiqueta")
        toolbar.addWidget(lbl_reporte)

        self.reporte_combo = QComboBox()
        self.reporte_combo.setObjectName("reportesFiltro")
        self.reporte_combo.setMinimumWidth(220)
        for clave, texto in REPORTES:
            self.reporte_combo.addItem(texto, clave)
        self.reporte_combo.currentIndexChanged.connect(self._reporte_cambiado)
        toolbar.addWidget(self.reporte_combo)

        lbl_periodo = QLabel("Periodo:")
        lbl_periodo.setObjectName("campoEtiqueta")
        toolbar.addWidget(lbl_periodo)

        self.periodo_combo = QComboBox()
        self.periodo_combo.setObjectName("reportesFiltro")
        for texto, clave in PERIODOS:
            self.periodo_combo.addItem(texto, clave)
        self.periodo_combo.currentIndexChanged.connect(self._periodo_cambiado)
        toolbar.addWidget(self.periodo_combo)

        self.desde_edit = QDateEdit(calendarPopup=True)
        self.desde_edit.setObjectName("reportesFecha")
        self.desde_edit.setDisplayFormat("dd/MM/yyyy")
        self.desde_edit.setDate(QDate.currentDate().addDays(-7))
        self.desde_edit.setFixedWidth(120)
        self.desde_edit.setVisible(False)
        self.desde_edit.dateChanged.connect(self._personalizado_cambiado)
        toolbar.addWidget(self.desde_edit)

        separador_lbl = QLabel("hasta")
        separador_lbl.setObjectName("campoEtiqueta")
        separador_lbl.setVisible(False)
        self._separador = separador_lbl
        toolbar.addWidget(separador_lbl)

        self.hasta_edit = QDateEdit(calendarPopup=True)
        self.hasta_edit.setObjectName("reportesFecha")
        self.hasta_edit.setDisplayFormat("dd/MM/yyyy")
        self.hasta_edit.setDate(QDate.currentDate())
        self.hasta_edit.setFixedWidth(120)
        self.hasta_edit.setVisible(False)
        self.hasta_edit.dateChanged.connect(self._personalizado_cambiado)
        toolbar.addWidget(self.hasta_edit)

        # Filtro secundario (ordenar / proveedor / tipo) según el reporte
        self.filtro_lbl = QLabel("Ordenar:")
        self.filtro_lbl.setObjectName("campoEtiqueta")
        self.filtro_lbl.setVisible(False)
        toolbar.addWidget(self.filtro_lbl)

        self.filtro_combo = QComboBox()
        self.filtro_combo.setObjectName("reportesFiltro")
        self.filtro_combo.setMinimumWidth(170)
        self.filtro_combo.setVisible(False)
        self.filtro_combo.currentIndexChanged.connect(self._filtro_cambiado)
        toolbar.addWidget(self.filtro_combo)

        toolbar.addStretch()

        btn_excel = QPushButton("Exportar Excel")
        btn_excel.setObjectName("btnSecundario")
        btn_excel.clicked.connect(self._exportar_excel)
        toolbar.addWidget(btn_excel)

        btn_pdf = QPushButton("Exportar PDF")
        btn_pdf.setObjectName("btnSecundario")
        btn_pdf.clicked.connect(self._exportar_pdf)
        toolbar.addWidget(btn_pdf)

        layout.addLayout(toolbar)

        # --- Tarjetas de resumen ---
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(12)
        self._tarjetas = []
        for _ in range(4):
            card = self._crear_tarjeta("—", "—")
            self.cards_layout.addWidget(card)
            self._tarjetas.append(card)
        layout.addLayout(self.cards_layout)

        # --- Tabla principal ---
        self.tabla = QTableWidget()
        self.tabla.setObjectName("tablaReportes")
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        self.tabla.setColumnCount(1)
        self.tabla.setHorizontalHeaderLabels(["Dato"])
        hdr = self.tabla.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tabla, 1)

        self._cargando = False

    # ---- Tarjetas ----

    @staticmethod
    def _crear_tarjeta(titulo, valor) -> QFrame:
        frame = QFrame()
        frame.setObjectName("reportesCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setObjectName("cardTitulo")
        layout.addWidget(lbl_titulo)

        lbl_valor = QLabel(str(valor))
        lbl_valor.setObjectName("cardValor")
        lbl_valor.setWordWrap(True)
        layout.addWidget(lbl_valor)

        frame._lbl_titulo = lbl_titulo
        frame._lbl_valor = lbl_valor
        return frame

    @staticmethod
    def _configurar_tarjeta(card, titulo, valor, tipo="texto"):
        card._lbl_titulo.setText(str(titulo))
        if tipo == "moneda":
            card._lbl_valor.setText(formatear_moneda(valor))
        elif tipo == "numero":
            card._lbl_valor.setText(str(int(valor or 0)))
        elif tipo == "porcentaje":
            card._lbl_valor.setText(formatear_porcentaje(valor))
        elif tipo == "cantidad":
            card._lbl_valor.setText(ReportesView._formatear_cantidad(valor))
        else:
            card._lbl_valor.setText(str(valor))

    @staticmethod
    def _formatear_cantidad(valor) -> str:
        """Mostrar cantidades sin ceros a la derecha (7, 10.5, -1)."""
        try:
            d = Decimal(str(valor or 0))
        except Exception:
            return str(valor)
        s = format(d, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s if s else "0"

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._recargar()

    # ------------------------------------------------------------------
    # Selector de reporte y filtros
    # ------------------------------------------------------------------

    def _reporte_cambiado(self):
        self._poblar_filtro()
        self._recargar()

    def _periodo_cambiado(self):
        es_personalizado = self.periodo_combo.currentData() == "personalizado"
        self.desde_edit.setVisible(es_personalizado)
        self.hasta_edit.setVisible(es_personalizado)
        self._separador.setVisible(es_personalizado)
        self._recargar()

    def _personalizado_cambiado(self):
        if self.periodo_combo.currentData() == "personalizado":
            self._recargar()

    def _filtro_cambiado(self):
        self._recargar()

    def _poblar_filtro(self):
        """Cargar las opciones del filtro secundario según el reporte activo."""
        clave = self.reporte_combo.currentData()
        self._cargando = True
        try:
            self.filtro_combo.clear()

            if clave == "compras":
                proveedores = []
                try:
                    proveedores = [
                        (p.id, p.nombre) for p in self.proveedores_service.obtener_activos()
                    ]
                except Exception:
                    proveedores = []
                self.filtro_combo.addItem("Todos los proveedores", "")
                for pid, nombre in proveedores:
                    self.filtro_combo.addItem(nombre, pid)
                self.filtro_lbl.setText("Proveedor:")
            elif clave in FILTROS_POR_REPORTE:
                opciones = FILTROS_POR_REPORTE[clave] or []
                for texto, valor in opciones:
                    self.filtro_combo.addItem(texto, valor)
                self.filtro_lbl.setText(ETIQUETAS_FILTRO.get(clave, "Filtro:"))

            visible = clave in ("productos", "compras", "movimientos")
            self.filtro_lbl.setVisible(visible)
            self.filtro_combo.setVisible(visible)
        finally:
            self._cargando = False

    def _filtro_valor(self):
        """Valor actual del filtro secundario ("" o None si ninguno)."""
        return self.filtro_combo.currentData()

    def _rango_periodo(self):
        """Devolver (fecha_inicio, fecha_fin) como date."""
        clave = self.periodo_combo.currentData()
        hoy = date.today()

        if clave == "hoy":
            return hoy, hoy
        elif clave == "ayer":
            ayer = hoy - timedelta(days=1)
            return ayer, ayer
        elif clave == "semana":
            return hoy - timedelta(days=6), hoy
        elif clave == "mes":
            return hoy.replace(day=1), hoy
        elif clave == "mes_pasado":
            ultimo_dia_mes_anterior = hoy.replace(day=1) - timedelta(days=1)
            return ultimo_dia_mes_anterior.replace(day=1), ultimo_dia_mes_anterior
        else:
            desde = self.desde_edit.date().toPython()
            hasta = self.hasta_edit.date().toPython()
            return desde, hasta

    def _etiqueta_periodo(self) -> str:
        desde, hasta = self._rango_periodo()
        if desde == hasta:
            return f"del {desde.strftime('%d/%m/%Y')}"
        return f"del {desde.strftime('%d/%m/%Y')} al {hasta.strftime('%d/%m/%Y')}"

    # ------------------------------------------------------------------
    # Carga de datos por reporte
    # ------------------------------------------------------------------

    def _recargar(self):
        if self._cargando:
            return
        desde, hasta = self._rango_periodo()
        clave = self.reporte_combo.currentData()
        svc = self.reporte_service()

        if clave == "ventas":
            self._datos = self._cargar_ventas(svc, desde, hasta)
        elif clave == "productos":
            self._datos = self._cargar_productos(svc, desde, hasta)
        elif clave == "ganancias":
            self._datos = self._cargar_ganancias(svc, desde, hasta)
        elif clave == "inventario":
            self._datos = self._cargar_inventario(svc)
        elif clave == "compras":
            self._datos = self._cargar_compras(svc, desde, hasta)
        elif clave == "fiado":
            self._datos = self._cargar_fiado(svc)
        elif clave == "caja":
            self._datos = self._cargar_caja(svc, desde, hasta)
        elif clave == "movimientos":
            self._datos = self._cargar_movimientos(svc, desde, hasta)
        else:
            self._datos = {}

        self._aplicar_datos()

    def reporte_service(self):
        """Acceso al servicio (método separado para pruebas)."""
        return self.reportes_service

    # ---- Construcción de cada reporte ----

    def _titulo_reporte(self):
        return self.reporte_combo.currentText() or "Reporte"

    def _base_datos(self, resumen, tabla, tablas_extra=None):
        return {
            "reporte": self.reporte_combo.currentData(),
            "titulo": self._titulo_reporte(),
            "periodo_label": self._etiqueta_periodo(),
            "fecha_generacion": datetime.now(),
            "resumen": resumen,
            "tabla": tabla,
            "tablas_extra": tablas_extra or [],
        }

    def _cargar_ventas(self, svc, desde, hasta):
        resumen = svc.resumen_periodo(desde, hasta)
        descuentos = svc.descuentos_periodo(desde, hasta)
        por_metodo = svc.por_metodo_pago(desde, hasta)
        ventas = svc.ventas_periodo(desde, hasta, limite=300)

        tabla = {
            "encabezados": ["Folio", "Fecha", "Usuario", "Cliente", "Método", "Total"],
            "filas": [
                [
                    v["folio"],
                    formatear_fecha(v["fecha"], "%d/%m/%Y %H:%M"),
                    v["usuario"],
                    v["cliente"],
                    v["metodo"],
                    float(v["total"]),
                ]
                for v in ventas
            ],
            "columnas_moneda": [5],
            "columnas_cantidad": [],
            "columnas_enteros": [],
        }
        extra = [{
            "titulo": "Ventas por método de pago",
            "encabezados": ["Método", "Total"],
            "filas": [[m["etiqueta"], float(m["total"])] for m in por_metodo],
            "columnas_moneda": [1],
            "columnas_cantidad": [],
            "columnas_enteros": [],
        }]
        resumen_tarjetas = [
            ("Total vendido", resumen["total"], "moneda"),
            ("Tickets", resumen["tickets"], "numero"),
            ("Descuentos aplicados", descuentos["total"], "moneda"),
            ("Promedio / venta", resumen["promedio"], "moneda"),
        ]
        return self._base_datos(resumen_tarjetas, tabla, extra)

    def _cargar_productos(self, svc, desde, hasta):
        orden = self._filtro_valor()
        productos = svc.productos_vendidos_detalle(desde, hasta, orden=orden or "mas", limite=100)
        filas = [
            [
                i,
                p["nombre"],
                p["cantidad"],
                p["precio_promedio"],
                p["monto"],
            ]
            for i, p in enumerate(productos, start=1)
        ]
        tabla = {
            "encabezados": ["#", "Producto", "Cantidad", "Precio promedio", "Monto"],
            "filas": filas,
            "columnas_moneda": [3, 4],
            "columnas_cantidad": [2],
            "columnas_enteros": [0],
        }
        unidades = sum((p["cantidad"] for p in productos), Decimal("0"))
        monto_total = sum((p["monto"] for p in productos), Decimal("0"))
        precio_prom = (
            Decimal("0") if unidades == 0 else (monto_total / unidades).quantize(Decimal("0.01"))
        )
        resumen_tarjetas = [
            ("Productos distintos", len(productos), "numero"),
            ("Unidades vendidas", unidades, "cantidad"),
            ("Monto total", monto_total, "moneda"),
            ("Precio promedio", precio_prom, "moneda"),
        ]
        return self._base_datos(resumen_tarjetas, tabla)

    def _cargar_ganancias(self, svc, desde, hasta):
        resumen = svc.ganancias_resumen(desde, hasta)
        detalle = svc.ganancias_periodo(desde, hasta, limite=100)
        tabla = {
            "encabezados": ["#", "Producto", "Cantidad", "Ingreso", "Costo", "Ganancia", "Margen %"],
            "filas": [
                [
                    i,
                    p["nombre"],
                    p["cantidad"],
                    p["ingreso"],
                    p["costo"],
                    p["ganancia"],
                    float(p["margen"]),
                ]
                for i, p in enumerate(detalle, start=1)
            ],
            "columnas_moneda": [3, 4, 5],
            "columnas_cantidad": [2, 6],
            "columnas_enteros": [0],
        }
        resumen_tarjetas = [
            ("Ventas", resumen["ventas"], "moneda"),
            ("Costo de mercancía", resumen["costo"], "moneda"),
            ("Ganancia bruta", resumen["ganancia"], "moneda"),
            ("Margen", resumen["margen"], "porcentaje"),
        ]
        return self._base_datos(resumen_tarjetas, tabla)

    def _cargar_inventario(self, svc):
        estado = svc.inventario_estado()
        detalle = svc.inventario_detallado(limite=500)
        tabla = {
            "encabezados": [
                "Producto", "Categoría", "Existencias", "Unidad",
                "Costo", "Precio venta", "Valor inv.", "Stock mín.", "Estado",
            ],
            "filas": [
                [
                    p["nombre"],
                    p["categoria"],
                    p["existencia"],
                    p["unidad"],
                    p["costo"],
                    p["precio_venta"],
                    p["valor_inv"],
                    p["stock_minimo"],
                    p["estado"],
                ]
                for p in detalle
            ],
            "columnas_moneda": [4, 5, 6],
            "columnas_cantidad": [2, 7],
            "columnas_enteros": [],
        }
        resumen_tarjetas = [
            ("Valor a costo", estado["valor_costo"], "moneda"),
            ("Valor a venta", estado["valor_venta"], "moneda"),
            ("Sin stock", estado["sin_stock"], "numero"),
            ("Stock bajo", estado["bajo"], "numero"),
        ]
        return self._base_datos(resumen_tarjetas, tabla)

    def _cargar_compras(self, svc, desde, hasta):
        proveedor_id = self._filtro_valor()
        resumen = svc.compras_resumen(desde, hasta)
        compras = svc.compras_periodo(desde, hasta, proveedor_id=proveedor_id or None, limite=200)
        tabla = {
            "encabezados": ["Folio", "Fecha", "Proveedor", "Productos", "Total"],
            "filas": [
                [
                    c["folio"],
                    formatear_fecha(c["fecha"], "%d/%m/%Y %H:%M"),
                    c["proveedor"],
                    c["productos"],
                    float(c["total"]),
                ]
                for c in compras
            ],
            "columnas_moneda": [4],
            "columnas_cantidad": [3],
            "columnas_enteros": [],
        }
        unidades = sum((c["productos"] for c in compras), Decimal("0"))
        resumen_tarjetas = [
            ("Total comprado", resumen["total"], "moneda"),
            ("Órdenes", resumen["ordenes"], "numero"),
            ("Proveedor principal", resumen["proveedor_top"], "texto"),
            ("Unidades compradas", unidades, "cantidad"),
        ]
        return self._base_datos(resumen_tarjetas, tabla)

    def _cargar_fiado(self, svc):
        resumen = svc.clientes_resumen()
        clientes = svc.clientes_fiados()
        tabla = {
            "encabezados": ["Cliente", "Teléfono", "Total fiado", "Total abonado", "Pendiente"],
            "filas": [
                [
                    c["cliente"],
                    c["telefono"],
                    float(c["total_fiado"]),
                    float(c["total_abonado"]),
                    float(c["pendiente"]),
                ]
                for c in clientes
            ],
            "columnas_moneda": [2, 3, 4],
            "columnas_cantidad": [],
            "columnas_enteros": [],
        }
        resumen_tarjetas = [
            ("Pendiente total", resumen["total_pendiente"], "moneda"),
            ("Total fiado", resumen["total_fiado"], "moneda"),
            ("Total abonado", resumen["total_abonado"], "moneda"),
            ("Clientes con deuda", resumen["deudores"], "numero"),
        ]
        return self._base_datos(resumen_tarjetas, tabla)

    def _cargar_caja(self, svc, desde, hasta):
        resumen = svc.cortes_resumen(desde, hasta)
        cortes = svc.cortes_caja_periodo(desde, hasta, limite=200)
        tabla = {
            "encabezados": [
                "ID", "Apertura", "Cierre", "Inicial",
                "Esperado", "Contado", "Diferencia", "Ventas", "Corte",
            ],
            "filas": [
                [
                    c["id"],
                    formatear_fecha_hora(c["fecha_apertura"]),
                    formatear_fecha_hora(c["fecha_cierre"]) if c["fecha_cierre"] else "—",
                    float(c["monto_inicial"]),
                    float(c["esperado"]),
                    float(c["contado"]),
                    float(c["diferencia"]),
                    float(c["total_ventas"]),
                    "Cerrado" if c["cerrado"] else "Abierto",
                ]
                for c in cortes
            ],
            "columnas_moneda": [3, 4, 5, 6, 7],
            "columnas_cantidad": [],
            "columnas_enteros": [0],
        }
        resumen_tarjetas = [
            ("Cortes realizados", resumen["cortes"], "numero"),
            ("Efectivo contado", resumen["efectivo_contado"], "moneda"),
            ("Diferencia total", resumen["diferencia_total"], "moneda"),
            ("Ventas en cortes", resumen["ventas"], "moneda"),
        ]
        return self._base_datos(resumen_tarjetas, tabla)

    def _cargar_movimientos(self, svc, desde, hasta):
        tipo = self._filtro_valor()
        movimientos = svc.movimientos_periodo(desde, hasta, tipo=tipo or None, limite=300)
        resumen = svc.movimientos_resumen(desde, hasta)
        tabla = {
            "encabezados": ["Fecha", "Producto", "Tipo", "Cantidad", "Usuario", "Referencia"],
            "filas": [
                [
                    formatear_fecha_hora(m["fecha"]),
                    m["producto"],
                    m["tipo"].capitalize(),
                    float(m["cantidad"]),
                    m["usuario"],
                    m["referencia"],
                ]
                for m in movimientos
            ],
            "columnas_moneda": [],
            "columnas_cantidad": [3],
            "columnas_enteros": [],
        }
        resumen_tarjetas = [
            ("Total movimientos", resumen["total"], "numero"),
            ("Entradas", resumen["entradas"], "numero"),
            ("Salidas", resumen["salidas"], "numero"),
            ("Ajustes + devoluciones", resumen["ajustes"] + resumen["devoluciones"], "numero"),
        ]
        return self._base_datos(resumen_tarjetas, tabla)

    # ------------------------------------------------------------------
    # Pintado de tarjetas y tabla
    # ------------------------------------------------------------------

    def _aplicar_datos(self):
        datos = self._datos
        resumen = datos.get("resumen", [])
        for i, card in enumerate(self._tarjetas):
            if i < len(resumen):
                etiqueta, valor, tipo = resumen[i]
                ReportesView._configurar_tarjeta(card, etiqueta, valor, tipo)
            else:
                ReportesView._configurar_tarjeta(card, "—", "—")

        tabla = datos.get("tabla")
        if tabla:
            self._render_tabla(tabla)
        else:
            self.tabla.setRowCount(0)

    def _render_tabla(self, tabla):
        encabezados = tabla.get("encabezados", [])
        moneda = set(tabla.get("columnas_moneda", []))
        cantidad = set(tabla.get("columnas_cantidad", []))
        enteros = set(tabla.get("columnas_enteros", []))
        derecha = moneda | cantidad | enteros

        self.tabla.setColumnCount(len(encabezados))
        self.tabla.setHorizontalHeaderLabels(encabezados)
        self.tabla.setRowCount(0)

        for fila in tabla.get("filas", []):
            r = self.tabla.rowCount()
            self.tabla.insertRow(r)
            for c, valor in enumerate(fila):
                if c in moneda:
                    texto = formatear_moneda(valor)
                elif c in cantidad:
                    texto = ReportesView._formatear_cantidad(valor)
                elif c in enteros:
                    texto = str(int(valor or 0))
                else:
                    texto = str(valor)
                item = QTableWidgetItem(texto)
                if c in derecha:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabla.setItem(r, c, item)

    # ------------------------------------------------------------------
    # Exportación
    # ------------------------------------------------------------------

    def _exportar_excel(self):
        if not self._datos.get("tabla"):
            QMessageBox.information(self, "Sin datos", "Selecciona un reporte para exportar.")
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar reporte a Excel",
            f"reporte_{date.today().strftime('%Y%m%d')}.xlsx",
            "Archivos de Excel (*.xlsx)",
        )
        if not ruta:
            return
        try:
            exportar_reporte_excel(ruta, self._datos)
            QMessageBox.information(
                self, "Exportación exitosa", f"Reporte guardado en:\n{ruta}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Error al exportar", f"No se pudo generar el archivo:\n{e}")

    def _exportar_pdf(self):
        if not self._datos.get("tabla"):
            QMessageBox.information(self, "Sin datos", "Selecciona un reporte para exportar.")
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar reporte a PDF",
            f"reporte_{date.today().strftime('%Y%m%d')}.pdf",
            "Archivos PDF (*.pdf)",
        )
        if not ruta:
            return
        try:
            exportar_reporte_pdf(ruta, self._datos)
            QMessageBox.information(
                self, "Exportación exitosa", f"Reporte guardado en:\n{ruta}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Error al exportar", f"No se pudo generar el archivo:\n{e}")

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QWidget#reportesView {
                background-color: #f5f5f5;
            }

            QLabel#campoEtiqueta {
                color: #2c3e50;
                font-size: 13px;
                font-weight: 500;
            }

            QComboBox#reportesFiltro, QDateEdit#reportesFecha {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                color: #2c3e50;
            }

            QComboBox#reportesFiltro QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #3498db;
                selection-color: #ffffff;
            }

            QDateEdit#reportesFecha::drop-down {
                border: none;
                width: 24px;
            }

            QFrame#reportesCard {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                min-width: 140px;
                min-height: 70px;
            }

            QLabel#cardTitulo {
                color: #7f8c8d;
                font-size: 12px;
            }

            QLabel#cardValor {
                color: #2c3e50;
                font-size: 18px;
                font-weight: 700;
            }

            QTableWidget#tablaReportes {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #dceaf7;
                selection-color: #1a252f;
            }

            QTableWidget#tablaReportes::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget#tablaReportes QHeaderView::section {
                background-color: #2c3e50;
                color: #ffffff;
                padding: 8px 10px;
                border: none;
                font-size: 12px;
                font-weight: 600;
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
        """)