# Sistema de Gestión Comercial — Tienda de Abarrotes y Chiles Secos

Aplicación de escritorio profesional para administrar una tienda de abarrotes
y venta de chiles secos. Funciona completamente **sin conexión a Internet**.

Incluye punto de venta (pieza y peso), inventario, compras, proveedores,
clientes, sistema de fiado, corte de caja, reportes, usuarios con roles,
respaldo y restauración de la base de datos.

## Requisitos

- **Windows 10 / 11** (también funciona en Linux/macOS)
- **Python 3.10 o superior** (64 bits)
- Sin conexión a Internet necesaria para su uso

## Instalación en una computadora nueva

1. Instala Python 3.10+ (marca *"Add python.exe to PATH"* al instalarlo).
2. Abre una terminal en la carpeta del proyecto (donde está `main.py`).
3. Crea y activa un entorno virtual (recomendado):

   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

4. Instala las dependencias:

   ```cmd
   pip install -r requirements.txt
   ```

## Cómo ejecutar

Con el entorno virtual activado:

```cmd
python main.py
```

### Opción sin Python: ejecutable (.exe)

Si la computadora no tiene Python instalado, usa la versión empaquetada:

- Carpeta: `dist\Sistema de Gestion Comercial\`
- Ejecutable: `Sistema de Gestion Comercial.exe` (doble clic)

La base de datos (`data\`), los respaldos (`backups\`) y el log de errores se
crean **junto al ejecutable** en esa misma carpeta. Copia toda la carpeta a la
PC donde la usarás. Para regenerar el ejecutable tras cambios, ejecuta:

```cmd
python -m PyInstaller --noconfirm "Sistema de Gestion Comercial.spec"
```

El ejecutable **incluye las fases 1-15** (reportes completos, roles y
permisos, cancelación de ventas, respaldos **y auditoría con respaldos
programados**). Se regeneró por última vez el **2026-09-16**.

### Primer arranque

En la primera ejecución la aplicación pide **crear el administrador inicial**
(usuario, nombre y contraseña segura). Guarda esas credenciales: son las que
usarás para iniciar sesión. No existen credenciales universales.

## Roles de usuario

| Rol            | Acceso                                                                 |
|----------------|------------------------------------------------------------------------|
| Administrador  | Acceso completo, incluyendo usuarios, respaldos y restauración          |
| Empleado       | Punto de venta, consulta de productos y dashboard                        |
| Cajero         | Punto de venta y corte de caja                                          |
| Almacén        | Productos, precios, inventario y compras                                 |

Los usuarios se crean desde **Configuración → Usuarios** (solo Administrador).

## Módulos

- **Dashboard** — ventas del día, más vendidos, inventario bajo, últimas ventas
- **Punto de Venta** — venta por pieza y por peso (kg/gramos), efectivo con
  cambio, tarjeta y transferencia
- **Productos** — catálogo con tipos de venta, precios y stock mínimo
- **Inventario** — stock, movimientos y ajustes con motivo
- **Compras** — registro de mercancía que aumenta inventario
- **Proveedores** y **Clientes**
- **Fiado** — ventas a crédito, abonos e historial de deuda
- **Corte de Caja** — totales por método de pago y diferencia
- **Reportes** — sistema completo de 8 reportes (ventas, productos vendidos,
  ganancias, inventario, compras, fiados, caja y movimientos) con exportación
  a Excel/PDF (Fase 13)
- **Configuración** — usuarios, contraseñas, bitácora y **respaldos**

## Respaldos y restauración (Fase 12)

### Respaldo automático

Al abrir la aplicación se crea un respaldo diario automático (solo uno por
día, no se duplica). Se guarda en la carpeta `backups/` con el nombre:

```
backup_AAAA_MM_DD.db          ← diario automático
backup_AAAA_MM_DD_HH_mm.db    ← manual ("Crear respaldo ahora")
```

### Respaldo manual

En **Configuración → Respaldos → Crear respaldo ahora**. Muestra todos los
respaldos disponibles con fecha, tamaño y estado de integridad.

### Restauración

1. En **Configuración → Respaldos**, selecciona un respaldo y pulsa
   **Restaurar seleccionado**.
2. Confirma la advertencia. El sistema:
   - crea un **respaldo preventivo** del estado actual,
   - cierra y **reinicia la aplicación sola**, y
   - al reabrir, copia el respaldo seleccionado sobre la base de datos
     (antes de conectarla) y te avisa del resultado.

> La restauración reemplaza **toda** la base de datos actual por la del
> respaldo. Asegúrate de elegir el correcto; el respaldo preventivo queda en
> `backups/` por si necesitas revertir.

### Respaldo programado y retención (Fase 15)

En **Configuración → Respaldos** puedes:

- **Respaldo programado**: activar un respaldo automático cada N horas
  mientras la aplicación esté abierta (`backup_programado_AAAA_MM_DD_HH_mm.db`).
  No duplica si ya existe uno reciente dentro de la ventana del intervalo.
- **Política de retención**: limitar cuántos respaldos se conservan. Por
  defecto está **desactivada**: nada se borra automáticamente. Al activarla se
  conservan los N más recientes y se eliminan los más viejos. Los respaldos
  preventivos de restauración (`backup_pre_restauracion_*`) **nunca** se
  eliminan.

La configuración se persiste en `data/configuracion_respaldos.json` y se
guarda automáticamente al cambiar cada control.

### Auditoría (Fase 15)

La pestaña **Actividad reciente** ahora permite **filtrar** por acción, por
usuario y por rango de fechas. Además de ventas y usuarios, quedan registradas
en la bitácora las operaciones críticas: alta/edición y **cambio de precio**,
activar/desactivar producto, **ajuste de inventario**, compras, abonos (fiado),
apertura/cierre de corte y respaldos (manual, diario, programado, retención y
restauración).

## Roles y permisos (Fase 14)

El login usa contraseñas hasheadas (bcrypt) y aplica los permisos **en la
lógica de negocio** (decorador `requiere_permiso` en los servicios), no solo
ocultando botones: una operación queda bloqueada aunque se fuerce desde fuera.

Catálogo de 13 acciones (cada una verificada dentro del servicio):

`realizar_ventas` · `cancelar_ventas` · `modificar_productos` ·
`modificar_precios` · `ajustar_inventario` · `registrar_compras` ·
`consultar_reportes` · `administrar_clientes` · `administrar_fiados` ·
`realizar_cortes` · `administrar_usuarios` · `configurar_sistema` ·
`restaurar_respaldos`

Matriz por rol:

| Rol | Acciones permitidas |
|-----|---------------------|
| **Administrador** | Todas (acceso completo) |
| **Empleado (Vendedor)** | Solo `realizar_ventas` |
| **Cajero** | `realizar_ventas`, `realizar_cortes` |
| **Almacén** | `registrar_compras`, `modificar_productos`, `modificar_precios`, `ajustar_inventario` |

Notas:

- **Cambiar un precio** exige además `modificar_precios` (permiso fino sobre
  `modificar_productos`).
- `configurar_sistema` está **reservado** (solo Administrador): hoy no existe
  un módulo de ajustes de tienda; la pestaña Configuración ya es de solo
  administrador y sus acciones usan permisos propios
  (`administrar_usuarios`, `restaurar_respaldos`).
- Los usuarios nunca se eliminan físicamente: se desactivan para conservar el
  historial, y el sistema protege al **último administrador activo**.

## Backups y datos

- Base de datos: `data/tienda.db`
- Respaldos: `backups/`
- Bitácora de errores: `data/errores.log` (revisar si algo falla)

## Solución de problemas

- **La aplicación no abre**: revisa `data/errores.log`.
- **Al restaurar la BD el archivo está en uso**: cierra cualquier otra
  instancia de la aplicación antes de abrir de nuevo.

## Estructura del proyecto

```
TIENDA_APP/
├── main.py            # Punto de entrada
├── requirements.txt
├── config/            # Configuración centralizada
├── database/          # Conexión, modelos y repositorios
├── services/          # Lógica de negocio (ventas, inventario, respaldos...)
├── views/             # Vistas (login, dashboard, punto_venta, reportes...)
├── components/        # Sidebar, navbar y widgets reutilizables
├── utils/             # Validadores, formateadores, seguridad
├── data/              # Base de datos y logs
└── backups/           # Respaldos de la base de datos
```

## Fases implementadas

1. Inicialización del proyecto · 2. Base de datos · 3. Interfaz · 4. Productos
· 5. Punto de venta · 6. Dashboard · 7. Compras e inventario · 8. Clientes y
fiado · 9. Corte de caja · 10. Reportes · 11. Usuarios y seguridad ·
12. Respaldos y preparación final · **13. Sistema completo de reportes** ·
**14. Usuarios, roles y seguridad** · **15. Auditoría y respaldos** ✔