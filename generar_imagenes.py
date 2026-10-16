"""
Script para capturar pantallas de la aplicación para los manuales.
Ejecuta la app y captura cada vista principal como imagen PNG.
"""
import sys
import os
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor
from PySide6.QtCore import Qt, QSize

# Configurar plataforma offscreen
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Agregar path del proyecto
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "TIENDA_APP_MANUALES/assets/screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def crear_imagen_texto(titulo, subtitulo, contenido, nombre_archivo, color_fondo="#2c3e50"):
    """Crea una imagen PNG con contenido de texto para representar una pantalla"""
    ancho, alto = 1200, 800

    # Crear pixmap
    pixmap = QPixmap(ancho, alto)
    painter = QPainter(pixmap)

    # Fondo
    painter.fillRect(0, 0, ancho, alto, QColor(color_fondo))

    # Barra superior
    painter.fillRect(0, 0, ancho, 60, QColor("#3498db"))

    # Título
    font_grande = QFont("Arial", 24, QFont.Bold)
    painter.setFont(font_grande)
    painter.setPen(QColor("white"))
    painter.drawText(30, 42, titulo)

    # Subtítulo
    font_chica = QFont("Arial", 14)
    painter.setFont(font_chica)
    painter.drawText(ancho - 200, 42, subtitulo)

    # Contenido
    painter.setPen(QColor("white"))
    y = 120
    for linea in contenido:
        if linea.startswith("="):
            painter.drawLine(30, y, ancho-30, y)
            y += 20
        elif linea.startswith("  -"):
            font = QFont("Arial", 12)
            painter.setFont(font)
            painter.drawText(50, y, linea[4:])
            y += 25
            font = QFont("Arial", 11)
            painter.setFont(font)
        elif linea.startswith("    ["):
            painter.setPen(QColor("#f39c12"))
            painter.drawText(70, y, linea)
            painter.setPen(QColor("white"))
            y += 25
        elif linea.strip():
            font = QFont("Arial", 12)
            painter.setFont(font)
            painter.drawText(30, y, linea)
            y += 25

    painter.end()

    filepath = OUTPUT_DIR / f"{nombre_archivo}.png"
    pixmap.save(str(filepath), "PNG")
    size_kb = filepath.stat().st_size / 1024
    print(f"  ✓ {nombre_archivo}.png ({size_kb:.1f} KB)")
    return filepath

def crear_mockup_login():
    """Crea imagen representando la pantalla de login"""
    contenido = [
        "Bienvenido al Sistema de Gestión Comercial",
        "",
        "┌─────────────────────────────────────────────┐",
        "│           INICIAR SESIÓN                    │",
        "├─────────────────────────────────────────────┤",
        "│                                             │",
        "│   Usuario:     [ admin           ]          │",
        "│   Contraseña:  [ **********      ]          │",
        "│                                             │",
        "│              [ ENTRAR ]                     │",
        "│                                             │",
        "└─────────────────────────────────────────────┘",
        "",
        "Primera vez? Contacta al administrador",
    ]
    return crear_imagen_texto(
        "Login", "v1.0 - 29/09/2026",
        contenido,
        "login"
    )

def crear_mockup_dashboard():
    """Crea imagen representando el dashboard"""
    contenido = [
        "SISTEMA DE GESTIÓN COMERCIAL",
        "──────────────────────────────────────────────",
        "",
        "┌─────────────────────┬─────────────────────┐",
        "│ VENTAS DEL DÍA      │ ÚLTIMAS VENTAS      │",
        "│                     │                     │",
        "│     $2,350.50       │ 14:30  $150.00 ✓   │",
        "│     15 tickets      │ 14:15  $ 85.50 ✓   │",
        "│                     │ 13:50  $320.00 ✓   │",
        "├─────────────────────┴─────────────────────┤",
        "│ PRODUCTOS CON STOCK BAJO                   │",
        "│                                             │",
        "│   ⚠ Chile Guajillo      1.5 kg remaining  │",
        "│   ⚠ Semillas de girasol  3 pz remaining    │",
        "│   ⚠ Pimienta negra       0.8 kg remaining  │",
        "│                                             │",
        "├─────────────────────────────────────────────┤",
        "│ [INICIO] [PUNTO DE VENTA] [PRODUCTOS] ...  │",
        "└─────────────────────────────────────────────┘",
    ]
    return crear_imagen_texto(
        "Dashboard", "Francisco Javier Valle",
        contenido,
        "dashboard",
        "#1a1a2e"
    )

def crear_mockup_punto_venta():
    """Crea imagen representando el punto de venta"""
    contenido = [
        "PUNTO DE VENTA - Nueva Venta",
        "──────────────────────────────────────────────",
        "",
        "┌───────────────────────────────┬──────────────┐",
        "│ BUSCAR PRODUCTO               │ CARRITO      │",
        "│ [ chile     🔍 ]              │              │",
        "│                               ├──────────────┤",
        "│ RESULTADOS:                   │ Chile Guaj.  │",
        "│ • Chile Guajillo   $120/kg    │   0.25 kg    │",
        "│ • Chile Ancho      $110/kg    │   $ 30.00    │",
        "│ • Chile de Árbol   $95/kg     │              │",
        "│                               │ Coca Cola    │",
        "│                               │   2 pz       │",
        "│                               │   $ 44.00    │",
        "│                               ├──────────────┤",
        "│                               │ Subtotal: $74│",
        "│                               │ TOTAL:   $74 │",
        "│                               │ [COBRAR]     │",
        "└───────────────────────────────┴──────────────┘",
        "",
        "Métodos: Efectivo | Tarjeta | Transferencia | Fiado",
    ]
    return crear_imagen_texto(
        "Punto de Venta", "Caja 1",
        contenido,
        "punto_venta"
    )

def crear_mockup_productos():
    """Crea imagen representando el catálogo de productos"""
    contenido = [
        "CATÁLOGO DE PRODUCTOS",
        "──────────────────────────────────────────────",
        "  [ + Nuevo Producto ]  [ 🔍 Buscar... ]",
        "",
        "┌────────┬─────────────────┬────────┬─────────┬──────────┐",
        "│ CÓDIGO │ NOMBRE          │ TIPO   │ PRECIO  │ STOCK    │",
        "├────────┼─────────────────┼────────┼─────────┼──────────┤",
        "│ 001    │ Chile Guajillo  │ KG     │ $120.00 │  8.5 kg  │",
        "│ 002    │ Chile Ancho     │ KG     │ $110.00 │ 15.2 kg  │",
        "│ 003    │ Coca Cola 600ml │ PZ     │  $22.00 │   45 pz  │",
        "│ 004    │ Semillas gira.  │ KG     │  $80.00 │   5.0 kg │",
        "│ 005    │ Leche descrem.  │ LT     │  $32.00 │   12 lt  │",
        "│ 006    │ Pimienta negra  │ KG     │ $250.00 │   0.8 kg │",
        "│ 007    │ Azúcar glass    │ KG     │  $45.00 │   8.0 kg │",
        "│ 008    │ Vainilla        │ LT     │ $180.00 │   3.0 lt │",
        "└────────┴─────────────────┴────────┴─────────┴──────────┘",
        "",
        "Mostrando 8 de 156 productos",
    ]
    return crear_imagen_texto(
        "Productos", "156 items - 8 activos",
        contenido,
        "productos"
    )

def crear_mockup_inventario():
    """Crea imagen representando el inventario"""
    contenido = [
        "INVENTARIO Y MOVIMIENTOS",
        "──────────────────────────────────────────────",
        "",
        "┌─────────────────────────────────────────────┐",
        "│ FILTROS: [Todos ▼] [ stock bajo ▼] [ Buscar ]│",
        "├─────────────────────────────────────────────┤",
        "│ PRODUCTO          │ ACTUAL │ MÍNIMO │ ESTADO │",
        "├─────────────────────────────────────────────┤",
        "│ Chile Guajillo    │  8.5kg │  2 kg  │ ✓ OK   │",
        "│ Chile Ancho       │ 15.2kg │  3 kg  │ ✓ OK   │",
        "│ Semillas gira.    │  5.0kg │  2 kg  │ ✓ OK   │",
        "│ Pimienta negra    │  0.8kg │  1 kg  │ ⚠ BAJO │",
        "└─────────────────────────────────────────────┘",
        "",
        "MOVIMIENTOS RECIENTES:",
        "──────────────────────────────────────────────",
        "  - [10:30] VENTA #145 - Chile Guajillo -0.25 kg",
        "  - [09:15] COMPRA #23 - Chile Guajillo +50 kg",
        "  - [08:45] AJUSTE - Pimienta negra (robo sospechoso)",
    ]
    return crear_imagen_texto(
        "Inventario", "Movimientos del día",
        contenido,
        "inventario"
    )

def crear_mockup_clientes():
    """Crea imagen representando clientes"""
    contenido = [
        "ADMINISTRACIÓN DE CLIENTES (FIADO)",
        "──────────────────────────────────────────────",
        "  [ + Nuevo Cliente ]",
        "",
        "┌────────┬─────────────────┬─────────────┬───────────┐",
        "│ ID     │ NOMBRE          │ TELÉFONO    │ SALDO     │",
        "├────────┼─────────────────┼─────────────┼───────────┤",
        "│ 001    │ Juan Pérez      │ 449-XXX-XX  │ $ 700.00  │",
        "│ 002    │ María García    │ 449-XXX-XX  │ $   0.00  │",
        "│ 003    │ Roberto López   │ 449-XXX-XX  │ $1,250.00 │",
        "│ 004    │ Ana Martínez    │ 449-XXX-XX  │ $  85.50  │",
        "└────────┴─────────────────┴─────────────┴───────────┘",
        "",
        "CLIENTES CON DEUDA: $2,035.50 total",
        "",
        "ACCIONES: [Ver historial] [Registrar abono] [Nueva venta]",
    ]
    return crear_imagen_texto(
        "Clientes", "4 registrados - 3 con deuda",
        contenido,
        "clientes"
    )

def crear_mockup_reportes():
    """Crea imagen representando reportes"""
    contenido = [
        "REPORTES Y ESTADÍSTICAS",
        "──────────────────────────────────────────────",
        "",
        "SELECCIONAR REPORTE:",
        "",
        "  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐",
        "  │   Ventas     │ │   Ganancias  │ │  Inventario  │",
        "  └──────────────┘ └──────────────┘ └──────────────┘",
        "",
        "  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐",
        "  │  Productos   │ │  Clientes    │ │    Caja      │",
        "  └──────────────┘ └──────────────┘ └──────────────┘",
        "",
        "──────────────────────────────────────────────",
        "PERÍODO: [Hoy ▼] [ 29/09/2026 ] [ 29/09/2026 ]",
        "",
        "EXPORTAR: [PDF] [Excel]",
    ]
    return crear_imagen_texto(
        "Reportes", "Seleccionar tipo de reporte",
        contenido,
        "reportes"
    )

def crear_mockup_corte_caja():
    """Crea imagen representando corte de caja"""
    contenido = [
        "CORTE DE CAJA",
        "──────────────────────────────────────────────",
        "",
        "Fecha: 29/09/2026 | Usuario: Francisco",
        "",
        "┌─────────────────────────────────────────────┐",
        "│ RESUMEN DEL DÍA                             │",
        "├─────────────────────────────────────────────┤",
        "│ Efectivo esperado:     $1,850.00            │",
        "│ Tarjeta:               $  500.00             │",
        "│ Transferencia:         $  200.00             │",
        "│ ─────────────────────────────────────────   │",
        "│ TOTAL VENDIDO:        $2,550.00             │",
        "└─────────────────────────────────────────────┘",
        "",
        "CONTEO DE CAJA:",
        "  Efectivo en caja:  [ 1,800.00         ]",
        "  Diferencia:        [   -50.00 ❌      ]",
        "",
        "  Observaciones: [Faltante de la venta #142  ]",
        "",
        "                    [ GUARDAR CORTE ]",
    ]
    return crear_imagen_texto(
        "Corte de Caja", "29/09/2026",
        contenido,
        "corte_caja"
    )

def crear_mockup_configuracion():
    """Crea imagen representando configuración"""
    contenido = [
        "CONFIGURACIÓN DEL SISTEMA",
        "──────────────────────────────────────────────",
        "",
        "┌─────────────────────────────────────────────┐",
        "│ USUARIOS        │ RESPALDOS    │ EMPRESA     │",
        "├─────────────────────────────────────────────┤",
        "│ 👤 Admin        │ 💾 Backup    │ 🏪 Tienda   │",
        "│ 👤 Cajero 1     │ 📥 Restore   │ 📋 Datos    │",
        "│ 👤 Almacén      │ ⏰ Programar │             │",
        "│ 👤 Vendedor     │ 🗑️ Limpiar   │             │",
        "└─────────────────────────────────────────────┘",
        "",
        "RESPALDOS:",
        "  ┌──────────────────────────────────────────┐",
        "  │ backup_2026_09_29.db       (Hoy)     OK  │",
        "  │ backup_2026_09_28.db       (Ayer)    OK  │",
        "  │ backup_2026_09_27.db       (Antier)  OK  │",
        "  └──────────────────────────────────────────┘",
        "",
        "  [CREAR BACKUP AHORA]  [CONFIGURAR RETENCIÓN]",
    ]
    return crear_imagen_texto(
        "Configuración", "Sistema completo",
        contenido,
        "configuracion"
    )

def main():
    print("=" * 60)
    print("Generando imágenes para manuales")
    print("=" * 60)
    print()
    print(f" Carpeta de salida: {OUTPUT_DIR}")
    print()

    funciones = [
        ("Login", crear_mockup_login),
        ("Dashboard", crear_mockup_dashboard),
        ("Punto de Venta", crear_mockup_punto_venta),
        ("Productos", crear_mockup_productos),
        ("Inventario", crear_mockup_inventario),
        ("Clientes", crear_mockup_clientes),
        ("Reportes", crear_mockup_reportes),
        ("Corte de Caja", crear_mockup_corte_caja),
        ("Configuración", crear_mockup_configuracion),
    ]

    generados = []
    for nombre, func in funciones:
        print(f"Generando: {nombre}...")
        try:
            path = func()
            generados.append(nombre)
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print()
    print("=" * 60)
    print("RESULTADO")
    print("=" * 60)
    print(f"Imágenes generadas: {len(generados)}/{len(funciones)}")
    print()
    print("Archivos:")
    for g in generados:
        print(f"  ✓ {g}.png")
    print()
    print(f"Ubicación: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()