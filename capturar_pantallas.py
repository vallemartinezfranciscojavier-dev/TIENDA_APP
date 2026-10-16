"""
Script para capturar pantallas de la aplicación y guardarlas como imágenes
para usar en los manuales
"""
import os
import sys
import time
import subprocess
from pathlib import Path

# Configurar Qt para offscreen
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Rutas
APP_DIR = Path("ProyectosEspeciales (SALIDA)/TIENDA_APP")
EXE = APP_DIR / "dist/Sistema de Gestion Comercial/Sistema de Gestion Comercial.exe"
OUTPUT_DIR = APP_DIR / "TIENDA_APP_MANUALES/assets/screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Captura de pantallas del sistema")
print("=" * 60)
print()
print(f"Ejecutable: {EXE}")
print(f"Salida: {OUTPUT_DIR}")
print()

if not EXE.exists():
    print(f"ERROR: No existe el ejecutable: {EXE}")
    sys.exit(1)

# Verificar dependencias para captura
try:
    import pyautogui
    print("[OK] pyautogui disponible")
except ImportError:
    print("[INFO] Instalando pyautogui...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyautogui", "pillow"], check=True)
    import pyautogui

try:
    import PIL
    print("[OK] PIL disponible")
except ImportError:
    print("[INFO] Instalando PIL...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], check=True)

print()
print("NOTA: Este script ejecutará la aplicación para capturar pantallas.")
print("Asegúrate de que la pantalla principal esté visible.")
print()
print("Presiona ENTER cuando estés listo para comenzar...")
input()

# Lista de capturas a realizar
capturas = [
    ("login", "Pantalla de inicio de sesión"),
    ("dashboard", "Dashboard / Pantalla principal"),
    ("punto_venta", "Punto de venta"),
    ("productos", "Catálogo de productos"),
    ("inventario", "Inventario y movimientos"),
    ("clientes", "Administración de clientes"),
    ("reportes", "Sistema de reportes"),
    ("corte_caja", "Corte de caja"),
    ("configuracion", "Configuración y respaldos"),
]

print()
print("Capturas a realizar:")
for i, (nombre, desc) in enumerate(capturas, 1):
    print(f"  {i}. {nombre} - {desc}")
print()

# Ejecutar la aplicación
print("Ejecutando aplicación...")
proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent))

print("Esperando que cargue (20 segundos)...")
time.sleep(20)

print()
print("=" * 60)
print("INSTRUCCIONES DE CAPTURA")
print("=" * 60)
print()
print("El script intentará capturar las ventanas automáticamente.")
print("Si no funcionan las capturas automáticas,:")
print("1. Navega manualmente por cada pantalla")
print("2. Presiona ENTER para capturar")
print("3. El script guardará la pantalla")
print()
print("Navega a cada pantalla y presiona ENTER para capturar:")
print("  1. Login (la app debería estar aquí)")
print("  2. Dashboard")
print("  3. Punto de Venta")
print("  4. Productos")
print("  5. Inventario")
print("  6. Clientes")
print("  7. Reportes")
print("  8. Corte de Caja")
print("  9. Configuración")
print()
print("Presiona ENTER para comenzar a capturar...")
input()

def capturar(nombre_archivo):
    """Captura la pantalla y guarda"""
    try:
        screenshot = pyautogui.screenshot()
        filepath = OUTPUT_DIR / f"{nombre_archivo}.png"
        screenshot.save(filepath)
        print(f"  [CAPTURADO] {nombre_archivo}.png")
        return True
    except Exception as e:
        print(f"  [ERROR] No se pudo capturar {nombre_archivo}: {e}")
        return False

# Capturar cada pantalla
capturados = []
for nombre, desc in capturas:
    print(f"\nCapturando: {desc}")
    print("  (Navega a esta pantalla, luego presiona ENTER)")
    input()
    if capturar(nombre):
        capturados.append(nombre)

# Cerrar la aplicación
print("\nCerrando aplicación...")
proc.terminate()
try:
    proc.wait(timeout=10)
except subprocess.TimeoutExpired:
    proc.kill()

# Reporte final
print()
print("=" * 60)
print("RESULTADO DE CAPTURAS")
print("=" * 60)
print()
print(f"Capturadas: {len(capturados)}/{len(capturas)}")
print()
print("Archivos guardados:")
for c in capturados:
    fp = OUTPUT_DIR / f"{c}.png"
    if fp.exists():
        size = fp.stat().st_size
        print(f"  ✓ {c}.png ({size/1024:.1f} KB)")
print()
print(f"Ubicación: {OUTPUT_DIR}")
print()
print("=" * 60)
print("SIGUIENTE PASO:")
print("=" * 60)
print("Ahora你需要 integrar estas imágenes en los")
print("manuales usando la sintaxis de imágenes en Markdown.")
print()
print("Para PDFs, el script de generación soporta")
print("insertar imágenes si existen en assets/screenshots/")