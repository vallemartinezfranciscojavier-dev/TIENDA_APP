"""
Genera capturas de pantalla de la aplicación para los manuales
Ejecuta la app en offscreen y captura cada vista principal
"""
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt, QSize

# Configurar paths
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# Importar vistas del sistema
from views.login_view import LoginView
from views.dashboard_view import DashboardView
from views.punto_venta_view import PuntoVentaView
from views.productos_view import ProductosView
from views.clientes_view import ClientesView
from views.reportes_view import ReportesView
from views.corte_caja_view import CorteCajaView
from views.configuracion_view import ConfiguracionView

OUTPUT_DIR = Path(__file__).parent / "assets/screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def capturar_widget(widget, nombre, tamaño=(1200, 800)):
    """Captura un widget y lo guarda como imagen"""
    widget.resize(*tamaño)
    widget.show()

    # Forzar renderizado
    QApplication.processEvents()

    # Crear pixmap
    pixmap = QPixmap(widget.size())
    widget.render(pixmap)

    # Guardar
    filepath = OUTPUT_DIR / f"{nombre}.png"
    pixmap.save(str(filepath), "PNG")
    print(f"  ✓ {nombre}.png ({filepath.stat().st_size/1024:.1f} KB)")
    widget.close()
    return filepath

def main():
    print("=" * 60)
    print("Generando capturas de pantalla para manuales")
    print("=" * 60)
    print()

    # Crear aplicación en modo offscreen
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    app = QApplication(sys.argv)

    capturas = [
        ("login", "Pantalla de Login", lambda: LoginView()),
        ("dashboard", "Dashboard Principal", lambda: DashboardView()),
        ("punto_venta", "Punto de Venta", lambda: PuntoVentaView()),
        ("productos", "Catálogo de Productos", lambda: ProductosView()),
        ("clientes", "Administración de Clientes", lambda: ClientesView()),
        ("reportes", "Sistema de Reportes", lambda: ReportesView()),
        ("corte_caja", "Corte de Caja", lambda: CorteCajaView()),
        ("configuracion", "Configuración", lambda: ConfiguracionView()),
    ]

    print(f"Generando {len(capturas)} capturas...")
    print()

    generados = []
    for nombre, desc, factory in capturas:
        try:
            print(f"Capturando: {desc}...")
            widget = factory()
            filepath = capturar_widget(widget, nombre)
            generados.append((nombre, desc, filepath))
        except Exception as e:
            print(f"  ✗ Error en {nombre}: {e}")

    print()
    print("=" * 60)
    print("RESULTADO")
    print("=" * 60)
    print(f"Capturas generadas: {len(generados)}/{len(capturas)}")
    print()
    print("Archivos:")
    for nombre, desc, filepath in generados:
        print(f"  {nombre}.png - {desc}")
    print()
    print(f"Ubicación: {OUTPUT_DIR}")

    app.quit()

if __name__ == "__main__":
    main()
