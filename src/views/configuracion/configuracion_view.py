"""
Vista de Configuración (Fase 11 + 12 + 15).
Gestión de usuarios (roles, estado, contraseñas), consulta de la bitácora de
actividades (con filtros) y respaldos/restauración de la base de datos,
incluida la programación de respaldos cada N horas y la política de retención.
Solo visible para el rol Administrador.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QTabWidget,
    QMessageBox,
    QGroupBox,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QLineEdit,
    QDateEdit,
)
from PySide6.QtCore import Qt, QDate, Signal

from services.usuarios_service import UsuarioService
from services.bitacora_service import BitacoraService
from services.permisos_service import etiqueta_rol
from services.sesion_service import obtener_usuario_id
from services import respaldos_service
from services import respaldos_config_service
from utils.formatters import formatear_fecha_hora

from views.configuracion.usuario_dialog import UsuarioDialog
from views.configuracion.cambiar_password_dialog import CambiarPasswordDialog

USUARIOS_COLS = ["Nombre", "Usuario", "Rol", "Estado"]
BITACORA_COLS = ["Fecha", "Acción", "Usuario", "Detalle"]
RESPALDOS_COLS = ["Archivo", "Fecha", "Tamaño", "Estado"]

# Fecha inicial del filtro de bitácora: todo el historial hasta hoy.
FECHA_INICIO_FILTRO = QDate(2000, 1, 1)


def _formatear_tamano(bytes_: int) -> str:
    """Tamaño legible (KB/MB)."""
    if bytes_ >= 1024 * 1024:
        return f"{bytes_ / (1024 * 1024):.1f} MB"
    return f"{max(bytes_, 0) / 1024:.1f} KB"


class ConfiguracionView(QWidget):
    """Vista de configuración y gestión de usuarios."""

    # Señal para pedir a la ventana principal que reinicie la app y aplique
    # la restauración en el próximo arranque.
    restaurar_solicitada = Signal(str)

    # Señal para que la ventana principal rearme el QTimer del respaldo
    # programado (Fase 15) cuando cambia la configuración.
    config_respaldos_cambiada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("configuracionView")
        self.usuario_service = UsuarioService()
        self.bitacora_service = BitacoraService()
        self._setup_ui()
        self._aplicar_estilos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 18)
        layout.setSpacing(14)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("configTabs")

        tab_usuarios = QWidget()
        self._setup_tab_usuarios(tab_usuarios)
        self.tabs.addTab(tab_usuarios, "Usuarios")

        tab_bitacora = QWidget()
        self._setup_tab_bitacora(tab_bitacora)
        self.tabs.addTab(tab_bitacora, "Actividad reciente")

        tab_respaldos = QWidget()
        self._setup_tab_respaldos(tab_respaldos)
        self.tabs.addTab(tab_respaldos, "Respaldos")

        layout.addWidget(self.tabs)

    def _setup_tab_usuarios(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addStretch()

        self.btn_nuevo = QPushButton("Nuevo usuario")
        self.btn_nuevo.setObjectName("btnSecundario")
        self.btn_nuevo.clicked.connect(self._nuevo_usuario)
        toolbar.addWidget(self.btn_nuevo)

        self.btn_editar = QPushButton("Editar")
        self.btn_editar.setObjectName("btnSecundario")
        self.btn_editar.clicked.connect(self._editar_usuario)
        toolbar.addWidget(self.btn_editar)

        self.btn_password = QPushButton("Cambiar contraseña")
        self.btn_password.setObjectName("btnSecundario")
        self.btn_password.clicked.connect(self._cambiar_password)
        toolbar.addWidget(self.btn_password)

        self.btn_toggle = QPushButton("Activar / Desactivar")
        self.btn_toggle.setObjectName("btnSecundario")
        self.btn_toggle.clicked.connect(self._alternar_activo)
        toolbar.addWidget(self.btn_toggle)

        layout.addLayout(toolbar)

        self.tabla_usuarios = QTableWidget(0, len(USUARIOS_COLS))
        self.tabla_usuarios.setObjectName("tablaUsuarios")
        self.tabla_usuarios.setHorizontalHeaderLabels(USUARIOS_COLS)
        self.tabla_usuarios.verticalHeader().setVisible(False)
        self.tabla_usuarios.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_usuarios.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_usuarios.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_usuarios.setAlternatingRowColors(True)
        self.tabla_usuarios.setShowGrid(False)

        hdr = self.tabla_usuarios.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)

        self.tabla_usuarios.itemSelectionChanged.connect(self._actualizar_botones)
        self.tabla_usuarios.itemDoubleClicked.connect(lambda item: self._editar_usuario())
        layout.addWidget(self.tabla_usuarios, 1)

        self.lbl_ayuda = QLabel(
            "Los usuarios se desactivan, no se eliminan, para conservar el "
            "historial de ventas."
        )
        self.lbl_ayuda.setObjectName("lblAyuda")
        layout.addWidget(self.lbl_ayuda)

    def _setup_tab_bitacora(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)

        encabezado = QLabel("Últimas actividades registradas en el sistema")
        encabezado.setObjectName("tituloSeccion")
        layout.addWidget(encabezado)

        # --- Filtros (Fase 15) ---
        filtro_fila = QHBoxLayout()
        filtro_fila.setSpacing(8)

        filtro_fila.addWidget(QLabel("Acción:"))
        self.combo_filtro_accion = QComboBox()
        self.combo_filtro_accion.setObjectName("filtroBitacora")
        self.combo_filtro_accion.setMinimumWidth(150)
        filtro_fila.addWidget(self.combo_filtro_accion)

        filtro_fila.addWidget(QLabel("Usuario:"))
        self.txt_filtro_usuario = QLineEdit()
        self.txt_filtro_usuario.setObjectName("filtroBitacora")
        self.txt_filtro_usuario.setPlaceholderText("Nombre")
        self.txt_filtro_usuario.setMinimumWidth(140)
        filtro_fila.addWidget(self.txt_filtro_usuario)

        filtro_fila.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDisplayFormat("dd/MM/yyyy")
        filtro_fila.addWidget(self.date_desde)

        filtro_fila.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDisplayFormat("dd/MM/yyyy")
        filtro_fila.addWidget(self.date_hasta)

        self.btn_filtrar_bitacora = QPushButton("Filtrar")
        self.btn_filtrar_bitacora.setObjectName("btnSecundario")
        self.btn_filtrar_bitacora.clicked.connect(self._recargar_bitacora)
        filtro_fila.addWidget(self.btn_filtrar_bitacora)

        btn_limpiar = QPushButton("Limpiar")
        btn_limpiar.setObjectName("btnSecundario")
        btn_limpiar.clicked.connect(self._limpiar_filtros_bitacora)
        filtro_fila.addWidget(btn_limpiar)

        filtro_fila.addStretch()
        layout.addLayout(filtro_fila)

        # Por defecto se muestra todo el historial.
        self.date_desde.setDate(FECHA_INICIO_FILTRO)
        self.date_hasta.setDate(QDate.currentDate())
        self._poblar_filtro_accion()

        self.tabla_bitacora = QTableWidget(0, len(BITACORA_COLS))
        self.tabla_bitacora.setObjectName("tablaBitacora")
        self.tabla_bitacora.setHorizontalHeaderLabels(BITACORA_COLS)
        self.tabla_bitacora.verticalHeader().setVisible(False)
        self.tabla_bitacora.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla_bitacora.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_bitacora.setAlternatingRowColors(True)
        self.tabla_bitacora.setShowGrid(False)

        bh = self.tabla_bitacora.horizontalHeader()
        bh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        bh.setSectionResizeMode(QHeaderView.ResizeToContents)
        bh.setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.tabla_bitacora, 1)

    def _setup_tab_respaldos(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)

        encabezado = QLabel("Respaldo y restauración de la base de datos")
        encabezado.setObjectName("tituloSeccion")
        layout.addWidget(encabezado)

        # --- Respaldo programado (Fase 15) ---
        grupo_programado = QGroupBox("Respaldo programado")
        grupo_programado.setObjectName("grupoRespaldo")
        gp = QHBoxLayout(grupo_programado)
        gp.setSpacing(10)
        gp.setContentsMargins(12, 10, 12, 10)

        self.chk_programado = QCheckBox("Activar respaldo automático cada")
        self.chk_programado.setObjectName("chkProgramado")
        self.spin_horas = QSpinBox()
        self.spin_horas.setObjectName("spinRespaldo")
        self.spin_horas.setRange(1, 720)
        self.spin_horas.setSuffix(" horas")
        self.spin_horas.setMinimumWidth(130)

        label_programado = QLabel("mientras la app esté abierta")
        label_programado.setObjectName("lblAyuda")

        gp.addWidget(self.chk_programado)
        gp.addWidget(self.spin_horas)
        gp.addWidget(label_programado)
        gp.addStretch()
        layout.addWidget(grupo_programado)

        # --- Política de retención (Fase 15) ---
        grupo_retencion = QGroupBox("Política de retención")
        grupo_retencion.setObjectName("grupoRespaldo")
        gr = QHBoxLayout(grupo_retencion)
        gr.setSpacing(10)
        gr.setContentsMargins(12, 10, 12, 10)

        self.chk_retencion = QCheckBox("Conservar como máximo")
        self.chk_retencion.setObjectName("chkRetencion")
        self.spin_maximo = QSpinBox()
        self.spin_maximo.setObjectName("spinRespaldo")
        self.spin_maximo.setRange(1, 500)
        self.spin_maximo.setMinimumWidth(80)

        label_maximo = QLabel("respaldos (se eliminan los más viejos)")
        label_maximo.setObjectName("lblAyuda")

        gr.addWidget(self.chk_retencion)
        gr.addWidget(self.spin_maximo)
        gr.addWidget(label_maximo)
        gr.addStretch()
        layout.addWidget(grupo_retencion)

        # Cargar la configuración guardada y guardar automáticamente al cambiar.
        self._refrescar_config_respaldos()
        self.chk_programado.toggled.connect(self._guardar_config_respaldos)
        self.spin_horas.valueChanged.connect(self._guardar_config_respaldos)
        self.chk_retencion.toggled.connect(self._guardar_config_respaldos)
        self.spin_maximo.valueChanged.connect(self._guardar_config_respaldos)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addStretch()

        self.btn_crear_respaldo = QPushButton("Crear respaldo ahora")
        self.btn_crear_respaldo.setObjectName("btnSecundario")
        self.btn_crear_respaldo.clicked.connect(self._crear_respaldo)
        toolbar.addWidget(self.btn_crear_respaldo)

        self.btn_restaurar = QPushButton("Restaurar seleccionado")
        self.btn_restaurar.setObjectName("btnSecundario")
        self.btn_restaurar.clicked.connect(self._restaurar_respaldo)
        self.btn_restaurar.setEnabled(False)
        toolbar.addWidget(self.btn_restaurar)

        layout.addLayout(toolbar)

        self.tabla_respaldos = QTableWidget(0, len(RESPALDOS_COLS))
        self.tabla_respaldos.setObjectName("tablaRespaldos")
        self.tabla_respaldos.setHorizontalHeaderLabels(RESPALDOS_COLS)
        self.tabla_respaldos.verticalHeader().setVisible(False)
        self.tabla_respaldos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_respaldos.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_respaldos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_respaldos.setAlternatingRowColors(True)
        self.tabla_respaldos.setShowGrid(False)

        rh = self.tabla_respaldos.horizontalHeader()
        rh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        rh.setSectionResizeMode(QHeaderView.ResizeToContents)
        rh.setSectionResizeMode(0, QHeaderView.Stretch)

        self.tabla_respaldos.itemSelectionChanged.connect(self._actualizar_botones_respaldos)
        layout.addWidget(self.tabla_respaldos, 1)

        self.lbl_ayuda_respaldos = QLabel(
            "Al abrir la aplicación se crea un respaldo diario automático. "
            "Puedes programar respaldos adicionales cada N horas y limitar "
            "cuántos respaldos se conservan en backups/. Los respaldos "
            "preventivos de restauración nunca se eliminan. Al restaurar se "
            "genera un respaldo preventivo del estado actual y la aplicación se "
            "reinicia sola para aplicar la copia de forma segura."
        )
        self.lbl_ayuda_respaldos.setObjectName("lblAyuda")
        self.lbl_ayuda_respaldos.setWordWrap(True)
        layout.addWidget(self.lbl_ayuda_respaldos)

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._recargar()

    def _recargar(self):
        self._refrescar_config_respaldos()
        self._recargar_usuarios()
        self._recargar_bitacora()
        self._recargar_respaldos()

    def _recargar_usuarios(self):
        usuarios = self.usuario_service.listar()
        self.tabla_usuarios.setRowCount(0)

        for u in usuarios:
            fila = self.tabla_usuarios.rowCount()
            self.tabla_usuarios.insertRow(fila)

            item_nombre = QTableWidgetItem(u.nombre or "")
            self.tabla_usuarios.setItem(fila, 0, item_nombre)

            item_usuario = QTableWidgetItem(u.usuario or "")
            self.tabla_usuarios.setItem(fila, 1, item_usuario)

            item_rol = QTableWidgetItem(etiqueta_rol(u.rol))
            self.tabla_usuarios.setItem(fila, 2, item_rol)

            estado = "Activo" if u.activo else "Inactivo"
            item_estado = QTableWidgetItem(estado)
            item_estado.setForeground(Qt.darkGreen if u.activo else Qt.darkRed)
            self.tabla_usuarios.setItem(fila, 3, item_estado)

            # Guardar el id para acciones posteriores.
            item_nombre.setData(Qt.UserRole, u.id)

        self._actualizar_botones()

    def _recargar_bitacora(self):
        accion = self.combo_filtro_accion.currentText()
        accion = None if accion == "Todas" else accion
        texto_usuario = self.txt_filtro_usuario.text().strip() or None
        try:
            fecha_inicio = self.date_desde.date().toPython()
            fecha_fin = self.date_hasta.date().toPython()
        except Exception:
            fecha_inicio = fecha_fin = None

        registros = self.bitacora_service.obtener_recientes(
            limite=200,
            accion=accion,
            texto_usuario=texto_usuario,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        self.tabla_bitacora.setRowCount(0)

        for r in registros:
            fila = self.tabla_bitacora.rowCount()
            self.tabla_bitacora.insertRow(fila)

            valores = [
                formatear_fecha_hora(r.fecha),
                (r.accion or "").capitalize(),
                r.usuario_nombre or "—",
                r.detalle or "",
            ]
            for col, val in enumerate(valores):
                self.tabla_bitacora.setItem(fila, col, QTableWidgetItem(str(val)))

    def _recargar_respaldos(self):
        try:
            respaldos = respaldos_service.listar_respaldos()
        except Exception:
            respaldos = []
        self.tabla_respaldos.setRowCount(0)

        for r in respaldos:
            fila = self.tabla_respaldos.rowCount()
            self.tabla_respaldos.insertRow(fila)

            item_archivo = QTableWidgetItem(r["archivo"])
            self.tabla_respaldos.setItem(fila, 0, item_archivo)

            self.tabla_respaldos.setItem(
                fila, 1,
                QTableWidgetItem(formatear_fecha_hora(r["fecha"])),
            )

            self.tabla_respaldos.setItem(
                fila, 2,
                QTableWidgetItem(_formatear_tamano(r["tamano_bytes"])),
            )

            integridad = respaldos_service.verificar_integridad(r["ruta"])
            estado = "Íntegro" if integridad["exito"] else "Dañado"
            item_estado = QTableWidgetItem(estado)
            item_estado.setForeground(Qt.darkGreen if integridad["exito"] else Qt.darkRed)
            self.tabla_respaldos.setItem(fila, 3, item_estado)

            # Guardar el nombre del archivo para las acciones.
            item_archivo.setData(Qt.UserRole, r["archivo"])

        self._actualizar_botones_respaldos()

    # ------------------------------------------------------------------
    # Configuración de respaldos (Fase 15)
    # ------------------------------------------------------------------

    def _refrescar_config_respaldos(self):
        """Mostrar la configuración guardada en los controles, sin guardar."""
        if not hasattr(self, "chk_programado"):
            return
        cfg = respaldos_config_service.leer_config()
        for w in (self.chk_programado, self.spin_horas, self.chk_retencion, self.spin_maximo):
            w.blockSignals(True)
        self.chk_programado.setChecked(cfg["programado"]["activo"])
        self.spin_horas.setValue(cfg["programado"]["intervalo_horas"])
        self.chk_retencion.setChecked(cfg["retencion"]["activa"])
        self.spin_maximo.setValue(cfg["retencion"]["maximo_respaldos"])
        for w in (self.chk_programado, self.spin_horas, self.chk_retencion, self.spin_maximo):
            w.blockSignals(False)

    def _guardar_config_respaldos(self):
        """Guardar la configuración al cambiar cualquier control (Fase 15)."""
        if not hasattr(self, "chk_programado"):
            return

        resultado_prog = respaldos_config_service.guardar_programado(
            self.chk_programado.isChecked(),
            self.spin_horas.value(),
        )
        resultado_ret = respaldos_config_service.guardar_retencion(
            self.chk_retencion.isChecked(),
            self.spin_maximo.value(),
        )
        self.config_respaldos_cambiada.emit()

        if not (resultado_prog.get("exito") and resultado_ret.get("exito")):
            QMessageBox.warning(
                self, "Error",
                "No se pudo guardar la configuración de respaldos.",
            )
            return

        # Si se acaba de activar la retención, aplicarla de inmediato.
        if self.chk_retencion.isChecked():
            respaldos_service.aplicar_politica_retencion()
            self._recargar_respaldos()

        self._registrar(
            "config_respaldos",
            f"Programado: {'sí' if self.chk_programado.isChecked() else 'no'} cada "
            f"{self.spin_horas.value()}h | Retención: "
            f"{'sí' if self.chk_retencion.isChecked() else 'no'} máx "
            f"{self.spin_maximo.value()}",
        )

    # ------------------------------------------------------------------
    # Filtros de bitácora (Fase 15)
    # ------------------------------------------------------------------

    def _poblar_filtro_accion(self):
        acciones = self.bitacora_service.acciones_distintas()
        self.combo_filtro_accion.blockSignals(True)
        self.combo_filtro_accion.clear()
        self.combo_filtro_accion.addItem("Todas")
        self.combo_filtro_accion.addItems(acciones)
        self.combo_filtro_accion.blockSignals(False)
        self.combo_filtro_accion.setCurrentIndex(0)

    def _limpiar_filtros_bitacora(self):
        self.combo_filtro_accion.setCurrentIndex(0)
        self.txt_filtro_usuario.clear()
        self.date_desde.setDate(FECHA_INICIO_FILTRO)
        self.date_hasta.setDate(QDate.currentDate())
        self._recargar_bitacora()

    # ------------------------------------------------------------------
    # Respaldos
    # ------------------------------------------------------------------

    def _respaldo_seleccionado(self):
        fila = self.tabla_respaldos.currentRow()
        if fila < 0:
            return None
        item = self.tabla_respaldos.item(fila, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _actualizar_botones_respaldos(self):
        self.btn_restaurar.setEnabled(self._respaldo_seleccionado() is not None)

    def _crear_respaldo(self):
        try:
            resultado = respaldos_service.crear_respaldo_manual()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear el respaldo:\n{e}")
            return

        if not resultado["exito"]:
            QMessageBox.warning(self, "Error", resultado["mensaje"])
            return

        # El guardado en bitácora ya lo hace respaldos_service.
        self._recargar_bitacora()
        QMessageBox.information(self, "Respaldo creado", resultado["mensaje"])
        self._recargar_respaldos()

    def _restaurar_respaldo(self):
        nombre = self._respaldo_seleccionado()
        if nombre is None:
            QMessageBox.information(self, "Sin selección", "Selecciona un respaldo.")
            return

        # Advertir claramente que se reemplazará la base de datos actual.
        reply = QMessageBox.warning(
            self,
            "Restaurar respaldo",
            "Vas a reemplazar TODA la base de datos actual por el respaldo "
            f"'{nombre}'.\n\n"
            "Antes se creará un respaldo preventivo del estado actual y la "
            "aplicación se reiniciará sola.\n\n"
            "¿Deseas continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # El servicio registra en bitácora al programar la restauración.
        self.restaurar_solicitada.emit(nombre)

    # ------------------------------------------------------------------
    # Selección
    # ------------------------------------------------------------------

    def _usuario_seleccionado(self):
        fila = self.tabla_usuarios.currentRow()
        if fila < 0:
            return None
        item = self.tabla_usuarios.item(fila, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _actualizar_botones(self):
        tiene_seleccion = self._usuario_seleccionado() is not None
        for btn in (self.btn_editar, self.btn_password, self.btn_toggle):
            btn.setEnabled(tiene_seleccion)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _nuevo_usuario(self):
        dialog = UsuarioDialog(self)
        if dialog.exec():
            self._recargar_usuarios()
            self._registrar("crear_usuario", "Alta de usuario")

    def _editar_usuario(self):
        usuario_id = self._usuario_seleccionado()
        if usuario_id is None:
            QMessageBox.information(self, "Sin selección", "Selecciona un usuario.")
            return

        usuario = self.usuario_service.obtener_por_id(usuario_id)
        if not usuario:
            QMessageBox.warning(self, "Error", "El usuario ya no existe.")
            self._recargar_usuarios()
            return

        dialog = UsuarioDialog(self, usuario=usuario)
        if dialog.exec():
            self._recargar_usuarios()
            self._registrar("editar_usuario", f"Edición de usuario '{usuario.usuario}'")

    def _cambiar_password(self):
        usuario_id = self._usuario_seleccionado()
        if usuario_id is None:
            QMessageBox.information(self, "Sin selección", "Selecciona un usuario.")
            return

        usuario = self.usuario_service.obtener_por_id(usuario_id)
        if not usuario:
            QMessageBox.warning(self, "Error", "El usuario ya no existe.")
            self._recargar_usuarios()
            return

        dialog = CambiarPasswordDialog(self, usuario=usuario)
        if dialog.exec():
            self._registrar("cambiar_password", f"Cambio de contraseña de '{usuario.usuario}'")

    def _alternar_activo(self):
        usuario_id = self._usuario_seleccionado()
        if usuario_id is None:
            QMessageBox.information(self, "Sin selección", "Selecciona un usuario.")
            return

        usuario = self.usuario_service.obtener_por_id(usuario_id)
        if not usuario:
            QMessageBox.warning(self, "Error", "El usuario ya no existe.")
            self._recargar_usuarios()
            return

        accion = "desactivar" if usuario.activo else "activar"
        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Deseas {accion} al usuario '{usuario.nombre}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.usuario_service.alternar_activo(usuario_id)
        except ValueError as e:
            QMessageBox.warning(self, "No permitido", str(e))
            return

        self._recargar_usuarios()
        self._registrar("estado_usuario", f"Se {accion} al usuario '{usuario.nombre}'")

    # ------------------------------------------------------------------
    # Bitácora
    # ------------------------------------------------------------------

    def _registrar(self, accion: str, detalle: str):
        self.bitacora_service.registrar(
            usuario_id=obtener_usuario_id(),
            accion=accion,
            detalle=detalle,
        )
        self._recargar_bitacora()

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QWidget#configuracionView {
                background-color: #f5f5f5;
            }

            QLabel#tituloSeccion {
                color: #2c3e50;
                font-size: 14px;
                font-weight: 600;
            }

            QLabel#lblAyuda {
                color: #95a5a6;
                font-size: 12px;
            }

            QTabWidget#configTabs > QWidget {
                background-color: #f5f5f5;
            }

            QTableWidget#tablaUsuarios, QTableWidget#tablaBitacora,
            QTableWidget#tablaRespaldos {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #dceaf7;
                selection-color: #1a252f;
            }

            QTableWidget#tablaUsuarios::item, QTableWidget#tablaBitacora::item,
            QTableWidget#tablaRespaldos::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f3f5;
            }

            QTableWidget#tablaUsuarios QHeaderView::section,
            QTableWidget#tablaBitacora QHeaderView::section,
            QTableWidget#tablaRespaldos QHeaderView::section {
                background-color: #2c3e50;
                color: #ffffff;
                padding: 8px 10px;
                border: none;
                font-size: 12px;
                font-weight: 600;
            }

            QGroupBox#grupoRespaldo {
                border: 1px solid #d0d7e2;
                border-radius: 6px;
                margin-top: 10px;
                font-size: 13px;
                font-weight: 600;
                color: #2c3e50;
                background-color: #fbfcfd;
            }

            QGroupBox#grupoRespaldo::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                background-color: #f5f5f5;
            }

            QSpinBox#spinRespaldo, QComboBox#filtroBitacora,
            QLineEdit#filtroBitacora, QDateEdit {
                background-color: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 13px;
                color: #2c3e50;
            }

            QCheckBox#chkProgramado, QCheckBox#chkRetencion {
                font-size: 13px;
                color: #2c3e50;
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

            QPushButton#btnSecundario:disabled {
                color: #bdc3c7;
                background-color: #f8f9fa;
                border-color: #e5e8ec;
            }
        """)