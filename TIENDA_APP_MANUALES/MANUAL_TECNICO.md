# Manual Técnico — Sistema de Gestión Comercial
## Implementación, Instalación y Mantenimiento

---

## 📑 Índice

1. Requisitos del sistema
2. Instalación desde cero
3. Instalación del ejecutable
4. Primera configuración
5. Estructura del proyecto
6. Base de datos
7. Sistema de respaldos
8. Roles y permisos
9. Mantenimiento preventivo
10. Resolución de problemas
11. Recuperación de desastres
12. Especificaciones técnicas

---

## 1. Requisitos del Sistema

### Hardware mínimo

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| Procesador | Intel Core i3 / AMD Ryzen 3 | Intel Core i5 / AMD Ryzen 5 |
| Memoria RAM | 4 GB | 8 GB |
| Disco duro | 500 MB libres | 1 GB libres |
| Resolución | 1366x768 | 1920x1080 |
| Puerto USB | Para lector de códigos | - |

### Software

| Componente | Versión | Notas |
|------------|---------|-------|
| Windows | 10/11 (64 bits) | Funciona en Linux/macOS también |
| Python | 3.10+ | Solo si usas código fuente |
| Memoriagraphics | OpenGL 2.0+ | Integrado en cualquier GPU moderna |

### Recomendaciones de hardware adicional

- **Lector de código de barras USB** - Emula teclado, funciona plug & play
- **Báscula electrónica** - Opcional, conexión serial/USB
- **Impresora de tickets** - Opcional, genera PDF para imprimir
- **No Break (UPS)** - Protege contra cortes de luz

---

## 2. Instalación Desde Código Fuente

(Uso para desarrollo o personalización)

### 2.1 Instalar Python

1. Descarga Python 3.10+ desde: https://www.python.org/downloads/
2. **Importante:** Durante la instalación, marca: **"Add python.exe to PATH"**
3. Verifica en CMD:
   ```cmd
   python --version
   ```
   Debe mostrar: `Python 3.10.x` o superior

### 2.2 Preparar el proyecto

```cmd
# Abrir terminal en la carpeta del proyecto
cd C:\Tienda\SistemaGestionComercial

# Crear entorno virtual
python -m venv venv

# Activar entorno
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2.3 Estructura de requirements.txt

```
PySide6>=6.5.0        # Interfaz gráfica
SQLAlchemy>=2.0.0    # Base de datos ORM
bcrypt>=4.0.0        # Contraseñas hasheadas
openpyxl>=3.1.0      # Exportar Excel
reportlab>=4.0.0     # Generar PDFs
```

### 2.4 Ejecutar el sistema

```cmd
python main.py
```

### 2.5 Generar ejecutable .exe

```cmd
python -m PyInstaller --noconfirm "Sistema de Gestion Comercial.spec"
```

El ejecutable se genera en: `dist\Sistema de Gestion Comercial\`

---

## 3. Instalación del Ejecutable (Producción)

### 3.1 Instalación básica

1. **Copia la carpeta completa** `dist\Sistema de Gestion Comercial\`
   a la computadora de la tienda

2. Ubicación recomendada:
   ```
   C:\Tienda\Sistema de Gestion Comercial\
   ```

3. **Estructura de la carpeta:**
   ```
   Sistema de Gestion Comercial/
   ├── Sistema de Gestion Comercial.exe  ← Ejecutable
   ├── _internal/                         ← Librerías
   ├── data/                              ← Se crea al iniciar
   └── backups/                           ← Se crea al iniciar
   ```

### 3.2 Crear acceso directo

1. Clic derecho en `Sistema de Gestion Comercial.exe`
2. "Enviar a" → "Escritorio (crear acceso directo)"
3. O bien: "Crear acceso directo" y mover al escritorio

### 3.3 Verificar instalación

1. Doble clic en el ejecutable
2. La aplicación debe abrir en 5-10 segundos
3. Se crearán carpetas `data/` y `backups/` automáticamente

---

## 4. Primera Configuración

### 4.1 Crear administrador inicial

Al abrir por primera vez, el sistema muestra:

```
┌─────────────────────────────────────────┐
│  BIENVENIDO AL SISTEMA                  │
│                                         │
│  No hay usuarios registrados.           │
│  Crea el administrador inicial:         │
│                                         │
│  Usuario:     [admin              ]    │
│  Nombre:      [Administrador      ]    │
│  Contraseña:  [•••••••••••        ]    │
│  Confirmar:   [•••••••••••        ]    │
│                                         │
│           [CREAR ADMINISTRADOR]         │
└─────────────────────────────────────────┘
```

**Recomendaciones:**
- Usuario: `admin` o `gerente` (sin acentos)
- Contraseña: Mínimo 8 caracteres, mezcla letras+números+caracteres especiales

⚠️ **NO EXISTEN CREDENCIALES POR DEFECTO.** Si pierdes esta contraseña, el sistema NO se puede recuperar sin acceso directo a la base de datos.

### 4.2 Configuración inicial recomendada

Después de crear el admin, configura:

#### A) Categorías de productos

Ve a: **PRODUCTOS → Categorías → Nueva**

Crea las categorías de tu tienda:
- Chiles secos
- Abarrotes
- Bebidas
- Dulces
- Semillas
- Lácteos
- Otros

#### B) Proveedores

Ve a: **PROVEEDORES → Nuevo**

Datos necesarios:
- Nombre del proveedor
- Teléfono
- Dirección
- Contacto (nombre de la persona)

#### C) Productos iniciales

Ve a: **PRODUCTOS → Nuevo producto**

Para cada producto:
- Nombre
- Código de barras (opcional, para lectores)
- Categoría
- Tipo de venta:
  - `PIEZA` / `UNIDAD` - Por ejemplo: bebidas, galletas
  - `KILOGRAMO` / `GRAMO` - Por peso: chiles, semillas
  - `BOLSA` - Por bolsa
- Precio de compra
- Precio de venta
- Stock inicial
- Stock mínimo (para alertas)

#### D) Usuarios

Ve a: **CONFIGURACIÓN → Usuarios → Nuevo**

Crea usuarios para cada persona que trabaja en la tienda:

| Rol | Funciones | Recomendado para |
|-----|-----------|------------------|
| Administrador | Todo | Dueño, gerente |
| Empleado | Solo ventas | Vendedor básico |
| Cajero | Ventas + corte | Cajero |
| Almacén | Productos, inventario, compras | Encargado de bodega |

### 4.3 Prueba de funcionamiento

Antes de abrir al público, haz estas pruebas:

1. **Crea una categoría y un producto**
2. **Haz una venta de prueba** (por pieza)
3. **Haz una venta de prueba** (por peso, ej: 0.250 kg)
4. **Haz un corte de caja**
5. **Consulta un reporte**
6. **Crea un respaldo manual**

Si todo funciona, ¡listo para usar!

---

## 5. Estructura del Proyecto

```
TIENDA_APP/
├── main.py                     # Punto de entrada
├── requirements.txt            # Dependencias Python
├── Sistema de Gestion Comercial.spec  # Config PyInstaller
│
├── config/
│   └── settings.py             # Configuración centralizada
│
├── database/
│   ├── connection.py           # Conexión SQLite
│   ├── models.py               # Modelos (tablas)
│   └── repositories/           # Acceso a datos
│       ├── producto_repository.py
│       ├── venta_repository.py
│       ├── cliente_repository.py
│       └── ...
│
├── services/                   # Lógica de negocio
│   ├── auth_service.py         # Autenticación
│   ├── venta_service.py        # Ventas
│   ├── inventario_service.py   # Inventario
│   ├── reporte_service.py      # Reportes
│   ├── respaldo_service.py     # Backups
│   └── ...
│
├── views/                      # Interfaz gráfica (PySide6)
│   ├── login_view.py
│   ├── dashboard_view.py
│   ├── punto_venta_view.py
│   ├── reportes_view.py
│   └── ...
│
├── components/                 # Componentes reutilizables
│   ├── sidebar.py              # Menú lateral
│   ├── navbar.py               # Barra superior
│   └── widgets/
│
├── utils/                      # Utilidades
│   ├── validators.py
│   ├── formatters.py
│   └── security.py             # Hashing bcrypt
│
├── data/                       # Generado automáticamente
│   ├── tienda.db               # Base de datos SQLite
│   ├── errores.log             # Log de errores
│   └── configuracion_respaldos.json
│
└── backups/                    # Respaldos automáticos
    ├── backup_2026_09_29.db
    ├── backup_2026_09_30.db
    └── ...
```

---

## 6. Base de Datos

### 6.1 Ubicación

- **Archivo:** `data/tienda.db`
- **Tipo:** SQLite (embebido, sin servidor)
- **Tamaño típico:** Crece con el uso (1MB por cada ~10,000 ventas)

### 6.2 Esquema de tablas

#### Tabla: usuarios
```sql
usuarios (
  id INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL,
  usuario TEXT UNIQUE NOT NULL,
  contraseña_hash TEXT NOT NULL,  -- bcrypt
  rol TEXT NOT NULL,               -- Administrador/Empleado/Cajero/Almacén
  activo INTEGER DEFAULT 1,
  fecha_creacion TEXT
)
```

#### Tabla: productos
```sql
productos (
  id INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL,
  codigo_barras TEXT,
  categoria_id INTEGER REFERENCES categorias(id),
  tipo_venta TEXT NOT NULL,       -- PIEZA/KILOGRAMO/GRAMO/BOLSA/UNIDAD
  precio_compra REAL NOT NULL,
  precio_venta REAL NOT NULL,
  stock_actual REAL DEFAULT 0,
  stock_minimo REAL DEFAULT 0,
  activo INTEGER DEFAULT 1,
  fecha_creacion TEXT
)
```

#### Tabla: ventas
```sql
ventas (
  id INTEGER PRIMARY KEY,
  fecha TEXT NOT NULL,
  usuario_id INTEGER REFERENCES usuarios(id),
  cliente_id INTEGER REFERENCES clientes(id),  -- NULL si no es fiado
  subtotal REAL NOT NULL,
  descuento REAL DEFAULT 0,
  total REAL NOT NULL,
  metodo_pago TEXT NOT NULL,      -- EFECTIVO/TARJETA/TRANSFERENCIA
  estado TEXT DEFAULT 'COMPLETADA'  -- COMPLETADA/CANCELADA
)
```

#### Tabla: detalle_ventas
```sql
detalle_ventas (
  id INTEGER PRIMARY KEY,
  venta_id INTEGER REFERENCES ventas(id),
  producto_id INTEGER REFERENCES productos(id),
  cantidad REAL NOT NULL,         -- Puede ser decimal (para peso)
  precio_unitario REAL NOT NULL,
  subtotal REAL NOT NULL
)
```

#### Tabla: clientes
```sql
clientes (
  id INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL,
  telefono TEXT,
  direccion TEXT,
  saldo_pendiente REAL DEFAULT 0,
  activo INTEGER DEFAULT 1
)
```

#### Tabla: movimientos_inventario
```sql
movimientos_inventario (
  id INTEGER PRIMARY KEY,
  producto_id INTEGER REFERENCES productos(id),
  tipo_movimiento TEXT NOT NULL,  -- ENTRADA/SALIDA/AJUSTE/COMPRA/VENTA
  cantidad REAL NOT NULL,
  fecha TEXT NOT NULL,
  referencia TEXT,
  usuario_id INTEGER REFERENCES usuarios(id)
)
```

### 6.3 Consultas útiles

#### Ver ventas de hoy
```sql
SELECT * FROM ventas 
WHERE DATE(fecha) = DATE('now', 'localtime');
```

#### Ver productos con stock bajo
```sql
SELECT nombre, stock_actual, stock_minimo 
FROM productos 
WHERE stock_actual <= stock_minimo AND activo = 1;
```

#### Total vendido hoy
```sql
SELECT SUM(total) as total_hoy 
FROM ventas 
WHERE DATE(fecha) = DATE('now', 'localtime') 
AND estado = 'COMPLETADA';
```

#### Clientes con deuda
```sql
SELECT nombre, saldo_pendiente 
FROM clientes 
WHERE saldo_pendiente > 0 AND activo = 1;
```

### 6.4 Mantenimiento de base de datos

#### Compactar (reducir tamaño)
```cmd
sqlite3 data/tienda.db "VACUUM;"
```
**Ejecutar con la aplicación cerrada.**

#### Respaldar manualmente
```cmd
copy data\tienda.db backups\backup_manual_%date%.db
```

---

## 7. Sistema de Respaldos

### 7.1 Tipos de respaldo

| Tipo | Cuándo | Formato |
|------|--------|---------|
| Automático diario | Al abrir app | `backup_2026_09_29.db` |
| Manual | Botón en UI | `backup_2026_09_29_14_30.db` |
| Programado | Cada N horas (configurable) | `backup_programado_2026_09_29_10_00.db` |
| Preventivo | Antes de restaurar | `backup_pre_restauracion_2026_09_29_14_25.db` |

### 7.2 Configurar respaldos programados

Ve a: **CONFIGURACIÓN → Respaldos**

Opciones:
- ✅ Respaldo automático al iniciar (ya viene activo)
- ☐ Respaldo cada ___ horas (configurable: 1, 2, 4, 6, 12, 24)
- ☐ Eliminar respaldos antiguos (conservar últimos ___)

### 7.3 Política de retención recomendada

| Tamaño de tienda | Respaldos a conservar |
|------------------|----------------------|
| Chica (<100 productos) | 30 |
| Mediana (100-500) | 60 |
| Grande (>500) | 90 |

### 7.4 Restaurar respaldo

**Desde la interfaz:**
1. Ve a **CONFIGURACIÓN → Respaldos**
2. Selecciona el respaldo
3. Clic en **[RESTAURAR]**
4. Confirma la advertencia
5. El sistema se reinicia automáticamente

**Manualmente (emergencia):**
1. Cierra la aplicación completamente
2. Copia el respaldo: `copy backups\backup_2026_09_28.db data\tienda.db`
3. Abre la aplicación

### 7.5 Respaldos externos (IMPORTANTE)

**NUNCA solo dependas de los respaldos locales.**

Copia la carpeta `backups/` periódicamente a:
- USB externo
- Disco duro externo
- Nube (Google Drive, OneDrive)

**Script para copia automática (Windows):**

```batch
@echo off
REM Copiar respaldos a USB diario a las 23:00
xcopy "C:\Tienda\Sistema de Gestion Comercial\backups\*.*" "E:\RespaldosTienda\" /D /Y /I
```

Programar en **Programador de tareas de Windows** para ejecutarse diariamente.

---

## 8. Roles y Permisos

### 8.1 Roles disponibles

| Rol | Descripción |
|-----|-------------|
| Administrador | Acceso completo a todo |
| Empleado | Solo ventas y consulta de productos |
| Cajero | Ventas + corte de caja |
| Almacén | Productos, inventario, compras, precios |

### 8.2 Permisos granulares

El sistema verifica 13 permisos específicos:

| Permiso | Función |
|---------|---------|
| realizar_ventas | Crear nuevas ventas |
| cancelar_ventas | Anular ventas existentes |
| modificar_productos | Editar productos (no precios) |
| modificar_precios | Cambiar precios de compra/venta |
| ajustar_inventario | Ajustes manuales de stock |
| registrar_compras | Registrar mercancía de proveedores |
| consultar_reportes | Ver reportes y estadísticas |
| administrar_clientes | Crear/editar clientes |
| administrar_fiados | Ventas a crédito y abonos |
| realizar_cortes | Hacer corte de caja |
| administrar_usuarios | Crear/editar usuarios |
| configurar_sistema | Acceso a configuración |
| restaurar_respaldos | Restaurar base de datos |

### 8.3 Matriz de permisos

| Permiso | Admin | Empleado | Cajero | Almacén |
|---------|-------|----------|--------|---------|
| realizar_ventas | ✓ | ✓ | ✓ | ✗ |
| cancelar_ventas | ✓ | ✗ | ✗ | ✗ |
| modificar_productos | ✓ | ✗ | ✗ | ✓ |
| modificar_precios | ✓ | ✗ | ✗ | ✓ |
| ajustar_inventario | ✓ | ✗ | ✗ | ✓ |
| registrar_compras | ✓ | ✗ | ✗ | ✓ |
| consultar_reportes | ✓ | ✗ | ✗ | ✗ |
| administrar_clientes | ✓ | ✗ | ✗ | ✗ |
| administrar_fiados | ✓ | ✗ | ✗ | ✗ |
| realizar_cortes | ✓ | ✗ | ✓ | ✗ |
| administrar_usuarios | ✓ | ✗ | ✗ | ✗ |
| configurar_sistema | ✓ | ✗ | ✗ | ✗ |
| restaurar_respaldos | ✓ | ✗ | ✗ | ✗ |

### 8.4 Cómo funciona

Los permisos se verifican **a nivel de código**, no solo ocultando botones:

```python
# Ejemplo en el código
@requiere_permiso("cancelar_ventas")
def cancelar_venta(self, venta_id):
    # Lógica para cancelar
    ...
```

Si un empleado intenta cancelar una venta desde código, el sistema lo bloquea.

### 8.5 Crear usuario

1. Ve a **CONFIGURACIÓN → Usuarios**
2. Clic en **[NUEVO USUARIO]**
3. Llena los datos:
   - Nombre completo
   - Nombre de usuario (único)
   - Contraseña
   - Rol
4. Clic en **[GUARDAR]**

### 8.6 Cambiar contraseña de usuario

1. **Usuario normal:** Pide al administrador
2. **Administrador:** En **CONFIGURACIÓN → Usuarios**, selecciona el usuario y **[CAMBIAR CONTRASEÑA]**

### 8.7 Recuperar contraseña de administrador (EMERGENCIA)

Si olvidaste la contraseña del admin y no hay otro admin:

```cmd
# Abrir base de datos
sqlite3 data/tienda.db

# Ver usuarios admin
SELECT id, usuario, nombre FROM usuarios WHERE rol = 'Administrador';

# Resetear contraseña (hash de "admin123")
UPDATE usuarios 
SET contraseña_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5eDzVE8FHp2Sy'
WHERE id = 1;
```

⚠️ **Después de usar esto, cambia la contraseña inmediatamente desde la interfaz.**

---

## 9. Mantenimiento Preventivo

### 9.1 Tareas diarias

- ✅ Al abrir: Verificar dashboard (productos con stock bajo)
- ✅ Al cerrar: Hacer corte de caja
- ✅ Verificar que se creó respaldo automático

### 9.2 Tareas semanales

- ✅ Revisar carpeta de respaldos (que haya respaldos recientes)
- ✅ Consultar reporte de ventas semanal
- ✅ Revisar clientes con deuda pendiente
- ✅ Verificar que no haya errores en `data/errores.log`

### 9.3 Tareas mensuales

- ✅ Copiar respaldos a USB/externo
- ✅ Ejecutar `VACUUM` en la base de datos
- ✅ Revisar tamaño de `data/tienda.db`
- ✅ Generar reporte mensual de ganancias
- ✅ Revisar usuarios activos/inactivos

### 9.4 Limpieza de respaldos antiguos

Si la carpeta `backups/` tiene muchos archivos:

1. Abre la carpeta
2. Ordena por fecha
3. Elimina los más antiguos (deja al menos 30)
4. **Nunca elimines** los que empiezan con `backup_pre_restauracion_`

---

## 10. Resolución de Problemas

### 10.1 La aplicación no abre

**Síntoma:** Doble clic y no pasa nada.

**Causas posibles:**
1. Error en la base de datos
2. Falta algún archivo
3. Problema con Python/dependencias

**Solución:**
1. Revisa `data/errores.log`
2. Busca líneas con "ERROR" o "Traceback"
3. Si el error menciona la base de datos, restaura un respaldo
4. Si el error menciona librerías, reinstala el sistema

### 10.2 "Base de datos en uso"

**Síntoma:** "database is locked" o similar.

**Causa:** Otra instancia de la aplicación está abierta.

**Solución:**
1. Cierra todas las instancias de la aplicación
2. En Administrador de tareas, busca `Sistema de Gestion Comercial.exe`
3. Termina el proceso si está activo
4. Vuelve a abrir

### 10.3 Error al iniciar sesión

**Síntoma:** Usuario y contraseña correctos pero no entra.

**Causas:**
1. Usuario está desactivado
2. Contraseña incorrecta

**Solución:**
1. Verifica con admin que el usuario esté activo
2. Pide que te cambien la contraseña
3. Si eres admin, usa el método de emergencia de la sección 8.7

### 10.4 Stock incorrecto

**Síntoma:** El inventario no cuadra con la realidad.

**Causas:**
1. Venta cancelada que no restituyó stock
2. Ajuste mal hecho
3. Error de sistema (raro)

**Solución:**
1. Ve a **INVENTARIO → Movimientos** del producto
2. Revisa el historial
3. Si encuentra discrepancia, haz un **AJUSTE** para corregir
4. Registra el motivo del ajuste

### 10.5 La aplicación va lenta

**Causas:**
1. Base de datos muy grande
2. Muchos productos (miles)
3. Poca RAM

**Solución:**
1. Ejecuta `VACUUM` en la base de datos
2. Cierra otras aplicaciones
3. Considera aumentar RAM a 8GB

### 10.6 Reporte no muestra datos

**Causa:** Período incorrecto seleccionado.

**Solución:**
1. Verifica el rango de fechas
2. Prueba con "Hoy" primero
3. Si aún no hay datos, significa que realmente no hay ventas en ese período

---

## 11. Recuperación de Desastres

### 11.1 La base de datos está corrupta

**Síntomas:**
- La aplicación no abre
- Errores strange al operar
- `data/errores.log` muestra errores SQLite

**Pasos para recuperación:**

1. **Intentar respaldo automático más reciente:**
   ```cmd
   copy backups\backup_2026_09_25.db data\tienda.db
   ```

2. **Si no funciona, probar con más antiguo:**
   ```cmd
   copy backups\backup_2026_09_20.db data\tienda.db
   ```

3. **Si ningún respaldo funciona:**
   - Crear una base de datos nueva (borrar `tienda.db`)
   - El sistema creará una vacía
   - Perderás todos los datos históricos

### 11.2 La computadora se dañó

**Si la PC ya no enciende:**

1. Retira el disco duro (si es HDD) o copia el SSD
2. Conecta el disco a otra PC
3. Copia la carpeta `data/` y `backups/`
4. Instala el sistema en la PC nueva
5. Copia los datos a las carpetas correspondientes

### 11.3 Restauración completa

**Pasos para reinstall desde cero:**

1. Borra las carpetas `data/` y `backups/`
2. Copia el ejecutable a la PC nueva
3. Ejecuta y crea el admin inicial
4. Restaura el respaldo más reciente:
   - Copia `backups\backup_XXXX.db` a `data\tienda.db`
5. Verifica que los datos aparezcan

---

## 12. Especificaciones Técnicas

### 12.1 Tecnologías usadas

| Tecnología | Propósito | Versión |
|------------|-----------|---------|
| Python | Lenguaje | 3.10+ |
| PySide6 | Interfaz gráfica | 6.5+ |
| SQLAlchemy | ORM base de datos | 2.0+ |
| SQLite | Base de datos | 3.x |
| bcrypt | Hashing contraseñas | 4.0+ |
| openpyxl | Excel export | 3.1+ |
| reportlab | PDF generation | 4.0+ |
| PyInstaller | Empaquetado .exe | 5.13+ |

### 12.2 Conexiones y puertos

- **No usa red** - Todo es local
- **No requiere puertos** - Sin servidor
- **No requiere Internet** - Funciona offline

### 12.3 Tamaños recomendados

| Dato | Recomendación |
|------|---------------|
| Productos | Hasta 10,000 sin problemas |
| Ventas | Hasta 100,000 registros |
| Usuarios | Sin límite |
| Adjuntos | No hay (solo texto) |

### 12.4 Compatibilidad

- **Windows 10/11** (64 bits) ✅
- **Linux** (con Python) ✅
- **macOS** (con Python) ✅

---

## Anexo: Comandos Rápidos

```cmd
# Iniciar el sistema (desde código fuente)
python main.py

# Generar ejecutable
python -m PyInstaller --noconfirm "Sistema de Gestion Comercial.spec"

# Compactar base de datos
sqlite3 data/tienda.db "VACUUM;"

# Respaldar manualmente
copy data\tienda.db backups\backup_manual_%date%.db

# Ver tamaño de BD
dir data\tienda.db

# Ver últimos errores
type data\errores.log
```

---

**FIN DEL MANUAL TÉCNICO**

---

## Notas de Implementación

Este sistema fue diseñado para tiendas de abarrotes pequeñas a medianas que buscan una solución simple, sin mensualidades y sin依赖 de Internet.

**Fases implementadas:** 1-15
**Estado:** Producción lista
**Última actualización:** 29/09/2026

Para soporte técnico o preguntas sobre este manual, contactar al desarrollador.