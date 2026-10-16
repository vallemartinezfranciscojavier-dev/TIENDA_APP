#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Punto de entrada principal de la aplicación.
Sistema de Gestión Comercial para Tienda de Abarrotes y Chiles Secos.
"""

import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QMainWindow, QDialog
from PySide6.QtCore import Qt, QTimer, QProcess, Signal
from PySide6.QtGui import QIcon, QFont

from config.settings import (
    APP_NAME,
    APP_VERSION,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
)
from database.connection import init_db
from components.sidebar import Sidebar
from components.navbar import Navbar
from services.sesion_service import (
    obtener_nombre,
    obtener_rol,
    obtener_usuario_id,
    cerrar_sesion,
)
from services.permisos_service import modulos_permitidos, etiqueta_rol, hay_permiso_actual
from services.usuarios_service import UsuarioService
from services.bitacora_service import BitacoraService
from views.dashboard import DashboardView
from views.productos import ProductosView
from views.punto_venta import PuntoVentaView
from views.compras import ComprasView
from views.inventario import InventarioView
from views.clientes import ClientesView
from views.corte_caja import CorteCajaView
from views.proveedores import ProveedoresView
from views.reportes import ReportesView
from views.configuracion import ConfiguracionView
from views.login import LoginDialog, PrimerAdminDialog


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación."""

    sesion_cerrada = Signal()

    def __init__(self):
        super().__init__()
        self._cerrando_por_logout = False
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # Inicializar base de datos (y migraciones de tablas nuevas)
        init_db()

        # Respaldo automático diario (Fase 12): uno por día al abrir la app.
        # Si falla, no debe impedir usar la aplicación.
        self._respaldo_diario_automatico()

        # Respaldo programado (Fase 15): QTimer según la configuración guardada.
        self._inicializar_respaldo_programado()

        # Permisos del rol en sesión (se usan al cargar vistas y sidebar)
        self._modulos_permitidos = modulos_permitidos(obtener_rol())

        # Configurar UI
        self._setup_ui()
        self._apply_styles()

        # Mostrar el usuario de la sesión en la navbar
        self.navbar.establecer_usuario(obtener_nombre(), etiqueta_rol(obtener_rol()))

    def _respaldo_diario_automatico(self):
        """
        Crear el respaldo diario automático (solo si no existe uno para hoy).
        Es "best-effort": un fallo de respaldo nunca debe impedir usar la app.
        """
        try:
            from services.respaldos_service import crear_respaldo_diario
            resultado = crear_respaldo_diario()
            if resultado.get("exito") and not resultado.get("ya_existia"):
                BitacoraService().registrar(
                    usuario_id=obtener_usuario_id(),
                    accion="respaldo_auto",
                    detalle=resultado.get("mensaje", "Respaldo diario automático"),
                    usuario_nombre=obtener_nombre(),
                )
                print(f"[APP] {resultado.get('mensaje')}", file=sys.stderr, flush=True)
        except Exception as exc:
            # No interrumpir el arranque por un problema de respaldo.
            print(f"[APP] respaldo automático omitido: {exc}", file=sys.stderr, flush=True)

    def _inicializar_respaldo_programado(self):
        """
        Respaldo programado (Fase 15): rearma el temporizador según la
        configuración guardada en data/configuracion_respaldos.json.

        Si la programación está activa, un QTimer crea un respaldo cada N horas
        (best-effort: un fallo nunca interrumpe la app). Si el usuario cambia la
        configuración (intervalo o activación), se vuelve a llamar a este método
        para detener el temporizador anterior y rearmarlo con los nuevos datos.
        """
        from PySide6.QtCore import QTimer
        from services import respaldos_config_service
        from services.respaldos_service import crear_respaldo_programado

        # Detener cualquier temporizador previo (reconfiguración).
        timer_previo = getattr(self, "_timer_respaldo_programado", None)
        if timer_previo is not None:
            timer_previo.stop()

        cfg = respaldos_config_service.leer_config()
        programado = cfg["programado"]
        if not programado["activo"]:
            return

        intervalo_horas = programado["intervalo_horas"]
        self._timer_respaldo_programado = QTimer(self)
        self._timer_respaldo_programado.setInterval(int(intervalo_horas) * 3600 * 1000)

        def _ejecutar():
            try:
                resultado = crear_respaldo_programado(intervalo_horas)
                if resultado.get("exito"):
                    archivo = resultado.get("archivo") or "respaldo de hoy"
                    print(f"[APP] respaldo programado: {archivo}", file=sys.stderr, flush=True)
            except Exception as exc:
                # Best-effort: no interrumpir por un fallo de respaldo.
                print(f"[APP] respaldo programado falló: {exc}", file=sys.stderr, flush=True)

        self._timer_respaldo_programado.timeout.connect(_ejecutar)
        self._timer_respaldo_programado.start()
        print(
            f"[APP] respaldo programado activo cada {intervalo_horas}h",
            file=sys.stderr,
            flush=True,
        )

    def _setup_ui(self):
        """Configurar la interfaz principal."""
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget

        # Widget central
        central = QWidget()
        self.setCentralWidget(central)

        # Layout principal horizontal
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar (ya filtrada por permisos del rol)
        self.sidebar = Sidebar()
        self.sidebar.navegacion_cambiada.connect(self._cambiar_vista)
        main_layout.addWidget(self.sidebar)

        # Área de contenido (Navbar + Vista actual)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Navbar
        self.navbar = Navbar()
        self.navbar.logout_solicitado.connect(self._cerrar_sesion)
        content_layout.addWidget(self.navbar)

        # Stack de vistas
        self.stack_vistas = QStackedWidget()
        content_layout.addWidget(self.stack_vistas)

        main_layout.addWidget(content_widget, 1)

        # Cargar vistas
        self._cargar_vistas()

    def _cargar_vistas(self):
        """Cargar todas las vistas en el stack."""
        self.vistas = {}

        # Dashboard
        self.vistas["dashboard"] = DashboardView()
        self.stack_vistas.addWidget(self.vistas["dashboard"])

        # Módulo de productos (Fase 4)
        self.vistas["productos"] = ProductosView()
        self.stack_vistas.addWidget(self.vistas["productos"])

        # Modo consulta para roles sin permiso de catálogo (Fase 14: se alinea
        # con el permiso real modificar_productos; ALMACÉN puede editar, VENDEDOR no).
        self.vistas["productos"].set_modo_lectura(
            not hay_permiso_actual("modificar_productos")
        )

        # Módulo de punto de venta (Fase 5)
        self.vistas["punto_venta"] = PuntoVentaView()
        self.stack_vistas.addWidget(self.vistas["punto_venta"])

        # Módulo de compras (Fase 7)
        self.vistas["compras"] = ComprasView()
        self.stack_vistas.addWidget(self.vistas["compras"])

        # Módulo de inventario (Fase 7)
        self.vistas["inventario"] = InventarioView()
        self.stack_vistas.addWidget(self.vistas["inventario"])

        # Módulo de clientes y fiado (Fase 8)
        self.vistas["clientes"] = ClientesView()
        self.stack_vistas.addWidget(self.vistas["clientes"])

        # Módulo de corte de caja (Fase 9)
        self.vistas["corte_caja"] = CorteCajaView()
        self.stack_vistas.addWidget(self.vistas["corte_caja"])

        # Módulo de proveedores
        self.vistas["proveedores"] = ProveedoresView()
        self.stack_vistas.addWidget(self.vistas["proveedores"])

        # Módulo de reportes (Fase 10)
        self.vistas["reportes"] = ReportesView()
        self.stack_vistas.addWidget(self.vistas["reportes"])

        # Módulo de configuración / seguridad (Fase 11) y respaldos (Fase 12)
        self.vistas["configuracion"] = ConfiguracionView()
        self.vistas["configuracion"].restaurar_solicitada.connect(
            self._ejecutar_restauracion
        )
        # Si el usuario cambia la programación de respaldos, rearmar el QTimer.
        self.vistas["configuracion"].config_respaldos_cambiada.connect(
            self._inicializar_respaldo_programado
        )
        self.stack_vistas.addWidget(self.vistas["configuracion"])

        # Filtrar la sidebar según el rol del usuario en sesión
        self.sidebar.aplicar_permisos(
            set(self._modulos_permitidos)
            & set(self.vistas.keys())
        )

    def _cambiar_vista(self, key: str):
        """Cambiar a la vista seleccionada."""
        if key in self.vistas:
            self.stack_vistas.setCurrentWidget(self.vistas[key])
            # Actualizar título en navbar
            titulos = {
                "dashboard": "Dashboard",
                "punto_venta": "Punto de Venta",
                "productos": "Productos",
                "inventario": "Inventario",
                "clientes": "Clientes",
                "proveedores": "Proveedores",
                "compras": "Compras",
                "reportes": "Reportes",
                "corte_caja": "Corte de Caja",
                "configuracion": "Configuración",
            }
            self.navbar.establecer_titulo(titulos.get(key, key.title()))

    def closeEvent(self, event):
        """
        Al cerrar la ventana por cualquier vía (incluido el botón X) se
        regresa al inicio de sesión, igual que un cierre de sesión.
        La app no se termina por cerrar su última ventana.
        """
        if self._cerrando_por_logout:
            # Ya pasó por _cerrar_sesion; no repetir confirmación.
            print("[APP] MainWindow cerrada por cierre de sesión", file=sys.stderr, flush=True)
            event.accept()
            return
        print("[APP] MainWindow cerrada por el usuario (X)", file=sys.stderr, flush=True)
        self._cerrar_sesion(preguntar=True)
        event.ignore()  # Se cierra solo si el usuario confirmó.

    def _cerrar_sesion(self, preguntar=True):
        """Manejar cierre de sesión: confirmar, registrar y salir."""
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.Yes
        if preguntar:
            reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Está seguro que desea cerrar sesión?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        usuario_id = obtener_usuario_id()
        BitacoraService().registrar(
            usuario_id=usuario_id,
            accion="logout",
            detalle="Cierre de sesión",
            usuario_nombre=obtener_nombre(),
        )
        cerrar_sesion()
        # Marcar para que closeEvent no vuelva a pedir confirmación.
        self._cerrando_por_logout = True
        self.close()
        self.sesion_cerrada.emit()

    def _ejecutar_restauracion(self, nombre_respaldo: str):
        """
        Programar la restauración de un respaldo (Fase 12) y relanzar la
        aplicación: al reabrir, se aplica la copia ANTES de conectar la BD.
        """
        from PySide6.QtWidgets import QMessageBox
        from services.respaldos_service import crear_flag_restauracion

        resultado = crear_flag_restauracion(nombre_respaldo)
        if not resultado["exito"]:
            QMessageBox.warning(self, "No se pudo restaurar", resultado["mensaje"])
            return

        QMessageBox.information(
            self,
            "Restaurar respaldo",
            resultado["mensaje"] + "\n\n"
            "La aplicación se cerrará y se reabrirá sola para aplicar la copia.",
        )

        # Relanzar en un proceso nuevo. (startDetached devuelve (bool, pid).)
        lanzado, _pid = QProcess.startDetached(sys.executable, [str(PROJECT_ROOT / "main.py")])
        if not lanzado:
            QMessageBox.critical(
                self,
                "Error",
                "No se pudo relanzar la aplicación. Reiníciala manualmente.",
            )
            return

        # Liberar el archivo de base de datos antes de salir para que el nuevo
        # proceso pueda sobrescribirlo sin conflictos de archivo en uso.
        try:
            from database.connection import engine
            engine.dispose()
        except Exception:
            pass

        self._cerrando_por_logout = True
        self.close()
        QApplication.instance().quit()

    def _apply_styles(self):
        """Aplicar estilos globales."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }

            #sidebar {
                background-color: #2c3e50;
                border-right: 1px solid #34495e;
            }

            #logoFrame {
                background-color: #1a252f;
                border-bottom: 1px solid #34495e;
            }

            #logoLabel {
                color: #ecf0f1;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            #separator {
                background-color: #34495e;
                max-height: 1px;
                border: none;
            }

            #navButton {
                background-color: transparent;
                color: #bdc3c7;
                border: none;
                padding: 14px 16px;
                text-align: left;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: 500;
            }

            #navButton:hover {
                background-color: #34495e;
                color: #ecf0f1;
            }

            #navButton:checked {
                background-color: #3498db;
                color: #ffffff;
                border-left: 3px solid #2980b9;
            }

            #versionLabel {
                color: #7f8c8d;
                font-size: 11px;
                padding-bottom: 16px;
            }

            #navbar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
            }

            #tituloLabel {
                color: #2c3e50;
                font-size: 18px;
                font-weight: 600;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            #usuarioLabel {
                color: #7f8c8d;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            #logoutButton {
                background-color: #e74c3c;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            #logoutButton:hover {
                background-color: #c0392b;
            }

            #placeholderLabel {
                color: #95a5a6;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            QStackedWidget {
                background-color: #f5f5f5;
            }
        """)


def _configurar_captura_errores():
    """
    Registrar en data/errores.log cualquier error no manejado, incluidos
    los tracebacks que PySide6 imprime en stderr (los que normalmente se
    perderían al ejecutar la app sin consola visible). Así, si la app se
    vuelve a cerrar o falla durante el uso, el motivo real queda guardado
    en un archivo para poder diagnosticarlo.
    """
    import sys
    import faulthandler
    from config.settings import BASE_DIR

    try:
        archivo = open(BASE_DIR / "data" / "errores.log", "a", encoding="utf-8", errors="replace")
    except OSError:
        return

    stderr_original = sys.stderr

    def _escribir(mensaje: str):
        try:
            stderr_original.write(mensaje)
            stderr_original.flush()
        except Exception:
            pass
        try:
            archivo.write(mensaje)
            archivo.flush()
        except Exception:
            pass

    class _Tee:
        """Escribe a la vez a la consola y al archivo de errores."""
        def write(self, mensaje: str) -> int:
            _escribir(mensaje)
            return len(mensaje)

        def flush(self) -> None:
            try:
                stderr_original.flush()
            except Exception:
                pass
            try:
                archivo.flush()
            except Exception:
                pass

    sys.stderr = _Tee()

    def _excepthook(tipo, valor, tb):
        import traceback
        try:
            archivo.write("\n=== Excepción no capturada ===\n")
            traceback.print_exception(tipo, valor, tb, file=archivo)
            archivo.flush()
        except Exception:
            pass
        traceback.print_exception(tipo, valor, tb)

    sys.excepthook = _excepthook

    try:
        faulthandler.enable(file=archivo, all_threads=True)
    except Exception:
        pass


def main():
    """Función principal."""
    # Registrar cualquier error futuro en data/errores.log.
    _configurar_captura_errores()

    def _log_app(mensaje: str):
        print(f"[APP] {mensaje}", file=sys.stderr, flush=True)

    # RESTAURACIÓN PENDIENTE (Fase 12): si existe una restauración programada,
    # aplicarla AHORA, ANTES de que la aplicación conecte la base de datos.
    resultado_restauracion = None
    from services.respaldos_service import (
        hay_restauracion_pendiente,
        aplicar_restauracion_pendiente,
    )
    try:
        if hay_restauracion_pendiente():
            resultado_restauracion = aplicar_restauracion_pendiente()
            _log_app(f"restauración pendiente: {resultado_restauracion.get('mensaje')}")
    except Exception:
        import traceback
        traceback.print_exc()
        resultado_restauracion = {
            "exito": False,
            "mensaje": "No se pudo aplicar la restauración pendiente. "
                       "El detalle quedó en data/errores.log.",
        }

    # Configurar aplicación
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # Configurar fuente por defecto
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    # La app solo se cierra de forma explícita (cerrar sesión o cancelar el
    # login), nunca por cerrarse la última ventana por accidente.
    app.setQuitOnLastWindowClosed(False)

    # Qt 6 ya escala por High DPI por defecto; configurar esos atributos
    # (AA_EnableHighDpiScaling / AA_UseHighDpiPixmaps) es un no-op y genera
    # DeprecationWarning. Se omiten a propósito.
    app.aboutToQuit.connect(lambda: _log_app("la app está saliendo del bucle (aboutToQuit)"))

    # Asegurar migraciones (crear tablas nuevas en bases existentes).
    init_db()

    # Avisar el resultado de la restauración (si hubo una pendiente).
    if resultado_restauracion:
        from PySide6.QtWidgets import QMessageBox
        if resultado_restauracion["exito"]:
            QMessageBox.information(
                None, "Restauración completada", resultado_restauracion["mensaje"]
            )
        else:
            QMessageBox.warning(
                None, "Restauración", resultado_restauracion["mensaje"]
            )

    def mostrar_login():
        """Flujo de autenticación: primer admin o inicio de sesión."""
        import traceback
        from PySide6.QtWidgets import QMessageBox
        _log_app("mostrando pantalla de inicio de sesión")

        # El sistema no tiene usuarios registrados: alta segura del primer admin.
        try:
            hay_usuarios = UsuarioService().existe_usuario()
        except Exception:
            # Un error transitorio de BD no debe tirar la app: se reintenta.
            traceback.print_exc()
            hay_usuarios = False

        if not hay_usuarios:
            if PrimerAdminDialog().exec() != QDialog.Accepted:
                _log_app("primer admin cancelado -> app.quit()")
                app.quit()
                return
            _log_app("primer admin aceptado, abriendo ventana principal")
        else:
            dialog = LoginDialog()
            if dialog.exec() != QDialog.Accepted:
                _log_app("login cancelado/rechazado -> app.quit()")
                app.quit()
                return
            _log_app("login aceptado, abriendo ventana principal")

        # Ya hay sesión activa: abrir la ventana principal.
        try:
            window = MainWindow()
        except Exception:
            # Un error al montar la interfaz no debe cerrar la app: se avisa
            # al usuario y se regresa al inicio de sesión.
            traceback.print_exc()
            cerrar_sesion()
            QMessageBox.critical(
                None,
                "Error al iniciar",
                "Ocurrió un error al preparar la aplicación.\n"
                "El detalle quedó en data/errores.log.",
            )
            QTimer.singleShot(0, mostrar_login)
            return

        _log_app("ventana principal construida")
        window.sesion_cerrada.connect(mostrar_login)
        # La ventana DEBE quedar referenciada de forma persistente: PySide6
        # destruye los QWidget sin referencia cuando el recolector corre, y la
        # ventana principal se cerraria al salir de esta funcion (el proceso
        # seguiria vivo pero sin panel visible). Se guarda en la aplicacion y
        # se reemplaza en cada inicio de sesion.
        app._ventana_actual = window
        window.show()
        _log_app("ventana principal mostrada")

    # Se lanza dentro del bucle de eventos para poder mostrar diálogos.
    QTimer.singleShot(0, mostrar_login)

    rc = app.exec()
    _log_app(f"app.exec() terminó con código {rc}")
    sys.exit(rc)


if __name__ == "__main__":
    main()