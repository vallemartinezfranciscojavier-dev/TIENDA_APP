# Manual de Usuario — Sistema de Gestión Comercial
## Tienda de Abarrotes y Chiles Secos

---

## 📑 Tabla de Contenidos

1. Introducción y requisitos
2. Pantalla de login
3. Dashboard (Inicio)
4. Punto de venta paso a paso
5. Gestión de productos
6. Ventas a crédito (fiado)
7. Corte de caja
8. Reportes
9. Preguntas frecuentes
10. Solución de problemas

---

## 1. Introducción

Este manual explica cómo usar el Sistema de Gestión Comercial en tu tienda. Es una herramienta completa para:

- **Vender rápido** (por pieza o por peso)
- **Controlar inventario** automáticamente
- **Llevar fiados** organizados
- **Ver ganancias reales** con reportes
- **Hacer corte de caja** sin errores

### ¿Qué necesitas?

- Computadora con Windows 10 o 11
- El archivo `Sistema de Gestion Comercial.exe`
- Permiso de usuario en la tienda (tu usuario + contraseña)

### Primeras cosas que debes saber

- **No necesitas Internet** para usar el sistema
- **Todo se guarda automáticamente** en la computadora
- **Los respaldos se hacen solos** cada día
- Si algo falla, existe un archivo de errores (`data/errores.log`)

---

## 2. Pantalla de Login

### Cómo abrir el sistema

1. Haz **doble clic** en el icono de la aplicación
   - Busca en el escritorio o en la carpeta donde lo instalaron
   - El icono se llama: `Sistema de Gestion Comercial.exe`

2. Espera a que cargue (tarda 5-10 segundos la primera vez)

3. Verás la pantalla de login

### Primera vez que se usa

**La primero vez el sistema te pedirá:**

```
┌────────────────────────────────┐
│  CREAR ADMINISTRADOR INICIAL   │
├────────────────────────────────┤
│ Usuario:     [                │
│ Nombre:      [                │
│ Contraseña:  [•••••••••••    │
│ Confirmar:   [•••••••••••    │
│              [CREAR]           │
└────────────────────────────────┘
```

**Qué poner:**
- **Usuario:** Algo corto (ej: `admin`, `gerente`, `dueño`)
- **Nombre:** Tu nombre completo
- **Contraseña:** Mínimo 8 caracteres, mezcla de letras y números

⚠️ **IMPORTANTE:** Guarda estas credenciales. Son ÚNICAS. Si las pierdes no se pueden recuperar sin acceso técnico.

### Login normal (después de la primera vez)

```
┌────────────────────────────────┐
│     INICIAR SESIÓN             │
├────────────────────────────────┤
│ Usuario:     [                │
│ Contraseña:  [•••••••••••    │
│              [ENTRAR]          │
└────────────────────────────────┘
```

Escribe tu usuario y contraseña, luego haz clic en **ENTRAR**.

---

## 3. Dashboard (Pantalla Principal)

Cuando entras, ves el **Dashboard** - un resumen de todo lo importante:

### Estructura de la pantalla

```
┌─────────────────────────────────────────────────────────┐
│  [Logo]  Sistema de Gestión Comercial    [Usuario ▼]   │
├─────────────────────────────────────────────────────────┤
│ 
│ [INICIO]           │  ┌─────────────────────────────────┐
│ [PUNTO DE VENTA]   │  │ VENTAS DEL DÍA: $2,350.50       │
│ [PRODUCTOS]        │  │ Número de tickets: 15           │
│ [INVENTARIO]       │  └─────────────────────────────────┘
│ [COMPRAS]          │
│ [CLIENTES]         │  ┌─────────────────────────────────┐
│ [REPORTES]         │  │ PRODUCTOS CON STOCK BAJO        │
│ [CORTE DE CAJA]    │  │ • Chile Guajillo: 1.5 kg        │
│ [CONFIGURACIÓN]    │  │ • Semillas de girasol: 3 pz     │
│                    │  └─────────────────────────────────┘
│
```

### Información en el Dashboard

| Elemento | Qué significa |
|----------|---------------|
| **Ventas del día** | Total vendido hoy |
| **Número de tickets** | Cuántas ventas hiciste |
| **Stock bajo** | Productos que se están acabando |
| **Más vendidos** | Productos que salen más |
| **Últimas ventas** | Las últimas 10 transacciones |

---

## 4. Punto de Venta - Guía Completa

El **Punto de Venta** es donde haces las ventas. Es lo más importante.

### Paso 1: Acceder a Punto de Venta

Haz clic en **PUNTO DE VENTA** en el menú lateral izquierdo.

Verás la pantalla dividida en dos:

```
┌─────────────────────────┬──────────────────┐
│  LADO IZQUIERDO         │  LADO DERECHO    │
├─────────────────────────┼──────────────────┤
│                         │                  │
│ Buscar: [              │ CARRITO DE COMPRA│
│         [Buscar]        │ ─────────────────│
│                         │ Producto Cant Subtotal
│ Resultados:             │ Chile Gua.. 0.25 kg  $30│
│ • Chile Guajillo        │ Coca Cola    2      $44│
│ • Chile Ancho           │ ─────────────────│
│ • Semillas de girasol    │ Subtotal: $74.00│
│                         │ Descuento: $ 0.00│
│                         │ TOTAL:    $74.00│
│                         │ [COBRAR] [VACIAR]
│                         │
└─────────────────────────┴──────────────────┘
```

### Paso 2: Buscar un producto

En el campo **Buscar** escribe:
- Nombre del producto: `chile` `coca` `leche`
- Código de barras: `7501234567890`
- Categoría: `chiles` `abarrotes`

**La búsqueda es instantánea** - aparecen resultados mientras escribes.

### Paso 3: Agregar producto al carrito

Haz **clic en el producto** que quieres vender.

Aparecerá en el carrito con cantidad 1.

### Paso 4: Ajustar cantidad

**Si vendes por PIEZA:**

```
Chile Guajillo (x kg)
Cantidad: [1] [ + ] [ - ]
Precio: $120/kg
```

- Haz clic en **+** para aumentar
- Haz clic en **-** para disminuir

**Si vendes por PESO:**

```
Chile Guajillo (x kg)
Peso: [0.250] kg
Precio: $120/kg
Subtotal: $30.00
```

- Borra el número y escribe el peso (ej: `0.250` para 250 gramos)
- El sistema calcula automáticamente: 0.250 × $120 = $30

### Paso 5: Agregar más productos

Repite los pasos 2-4 con todos los productos que el cliente compre.

**Ejemplo de carrito completo:**

```
CARRITO
━━━━━━━━━━━━━━━━━━━━━━━
Coca Cola 600ml    x2    $44.00
Chile Guajillo   0.25kg  $30.00
Semillas girasol   x1    $15.00
Leche descremada   x2    $48.00
━━━━━━━━━━━━━━━━━━━━━━━
Subtotal:              $137.00
Descuento:             $  0.00
━━━━━━━━━━━━━━━━━━━━━━━
TOTAL:                 $137.00
```

### Paso 6: Aplicar descuento (opcional)

Si le das descuento al cliente:

1. Haz clic en **Descuento**
2. Escribe el monto: `10` (para $10 de descuento)
3. El total se ajusta automáticamente

### Paso 7: Cobrar

Cuando el carrito esté completo, haz clic en **[COBRAR]**

Aparecerá la ventana de pago:

```
┌─────────────────────────┐
│   MÉTODO DE PAGO        │
├─────────────────────────┤
│ Total: $137.00          │
│                         │
│ (O) EFECTIVO            │
│ (O) TARJETA             │
│ (O) TRANSFERENCIA       │
│                         │
│ [PROCESAR] [CANCELAR]   │
└─────────────────────────┘
```

#### Si paga con EFECTIVO:

```
┌─────────────────────────┐
│   PAGO EN EFECTIVO      │
├─────────────────────────┤
│ Total: $137.00          │
│ Recibido: [            │
│           [CALCULAR]    │
│                         │
│ Cambio: $13.00          │
│ [CONFIRMAR] [CANCELAR]  │
└─────────────────────────┘
```

1. El cliente te da dinero
2. Escribe cuánto te dio: `150`
3. Haz clic en **CALCULAR** (el sistema calcula el cambio automáticamente)
4. Haz clic en **CONFIRMAR**

#### Si paga con TARJETA o TRANSFERENCIA:

Solo haz clic en **CONFIRMAR** sin escribir nada. El sistema lo registra.

### Paso 8: Venta completada

Después de confirmar:

- ✅ La venta se registra automáticamente
- ✅ El inventario se descuenta
- ✅ El carrito se vacía
- ✅ Puedes hacer la siguiente venta

---

## 5. Gestión de Productos

### Ver catálogo completo

Haz clic en **PRODUCTOS** en el menú.

Verás una tabla con todos los productos:

| Código | Nombre | Categoría | Tipo | Precio | Stock | Estado |
|--------|--------|-----------|------|--------|-------|--------|
| 001 | Chile Guajillo | Chiles | KG | $120 | 8.5 | ✓ Activo |
| 002 | Coca Cola 600ml | Bebidas | PZ | $22 | 45 | ✓ Activo |

### Buscar un producto

Escribe en el buscador el nombre o código. Los resultados aparecen inmediatamente.

### Ver detalles de un producto

Haz clic en un producto para ver:
- Nombre completo
- Precio de compra
- Precio de venta
- Stock actual y mínimo
- Categoría
- Código de barras

---

## 6. Ventas a Crédito (Fiado)

### Realizar una venta fiada

#### Paso 1: Agregar productos al carrito

Como una venta normal (ver sección 4).

#### Paso 2: En la ventana de pago, selecciona FIADO

```
┌─────────────────────────┐
│   MÉTODO DE PAGO        │
├─────────────────────────┤
│ Total: $137.00          │
│                         │
│ (O) EFECTIVO            │
│ (O) TARJETA             │
│ (O) TRANSFERENCIA       │
│ (O) FIADO ← AQUI        │
│                         │
│ [PROCESAR] [CANCELAR]   │
└─────────────────────────┘
```

#### Paso 3: Selecciona al cliente

```
┌─────────────────────────┐
│     VENTA A CRÉDITO     │
├─────────────────────────┤
│ Cliente: [Juan Pérez ▼] │
│          [Buscar...]    │
│          [Nuevo...]     │
│                         │
│ Total fiado: $137.00    │
│                         │
│ [GUARDAR] [CANCELAR]    │
└─────────────────────────┘
```

- Si el cliente ya existe, selecciónalo del dropdown
- Si es nuevo, haz clic en **[Nuevo...]** y llena los datos

#### Paso 4: Guardar

Haz clic en **[GUARDAR]**

✓ La venta se registra como fiado automáticamente.

### Consultar deuda de un cliente

#### Opción 1: Desde CLIENTES

1. Haz clic en **CLIENTES**
2. Busca al cliente
3. Haz clic en su nombre
4. Verás:

```
HISTORIAL DE JUAN PÉREZ
━━━━━━━━━━━━━━━━━━━━━━
Total fiado:    $1,500.00
Abonos:         $  800.00
Saldo pendiente: $  700.00

ÚLTIMAS COMPRAS:
━━━━━━━━━━━━━━━━━━━━━━
29/09 - $137.00 - FIADO
28/09 - $250.00 - PAGADO
27/09 - $300.00 - FIADO
```

### Registrar un abono (pago a crédito)

#### Cuando el cliente viene a pagar parte de su deuda:

1. Haz clic en **CLIENTES**
2. Busca y haz clic en el cliente
3. Haz clic en **[REGISTRAR ABONO]**

```
┌─────────────────────────┐
│   REGISTRAR ABONO       │
├─────────────────────────┤
│ Cliente: Juan Pérez     │
│ Saldo anterior: $700    │
│                         │
│ Monto a pagar: [       │
│                [GUARDAR]
│                         │
│ Nuevo saldo: $500      │
└─────────────────────────┘
```

4. Escribe cuánto paga: `200`
5. Haz clic en **[GUARDAR]**

✓ El sistema actualiza automáticamente el saldo.

---

## 7. Corte de Caja

Se hace **al final del día** para verificar que todo cuadre.

### Paso 1: Acceder a Corte de Caja

Haz clic en **CORTE DE CAJA** en el menú.

### Paso 2: Ver resumen del día

El sistema te muestra automáticamente:

```
CORTE DE CAJA - 29/09/2026
━━━━━━━━━━━━━━━━━━━━━━━━━━
VENTAS EN EFECTIVO:    $1,850.00
VENTAS EN TARJETA:     $  500.00
VENTAS POR TRANSFER:   $  200.00
━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL ESPERADO:        $2,550.00

EFECTIVO ESPERADO:     $1,850.00
EFECTIVO CONTADO:      [          ]
DIFERENCIA:            [          ]

OBSERVACIONES: [                  ]
               [GUARDAR CORTE]
```

### Paso 3: Contar dinero y escribir el monto

1. **Cuenta físicamente** el dinero en la caja
2. Escribe el monto que contaste: `1,800`
3. El sistema calcula automáticamente:

```
Esperado:    $1,850.00
Contado:     $1,800.00
────────────────────────
Diferencia:  -$50.00   ← FALTARON $50
```

### Paso 4: Escribir observaciones (opcional)

Si hay diferencia, anota por qué:
- "Cambio que no tenía"
- "Error en una venta"
- "Cliente devolvió un producto"

### Paso 5: Guardar el corte

Haz clic en **[GUARDAR CORTE]**

✓ El corte queda registrado para siempre.

---

## 8. Reportes

Los reportes te muestran información importante sobre ventas y ganancias.

### Acceder a Reportes

Haz clic en **REPORTES** en el menú.

### Tipos de reportes disponibles

#### 1. Reporte de Ventas

**Qué muestra:** Total vendido en un período

```
REPORTE DE VENTAS - SEPTIEMBRE 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total vendido:      $58,350.00
Número de tickets:  245
Promedio/ticket:    $238.16

DESGLOSE POR MÉTODO:
• Efectivo:         $45,000.00
• Tarjeta:          $10,000.00
• Transferencia:    $ 3,350.00
```

**Cómo usarlo:**
- Selecciona: Hoy / Semana / Mes / Personalizado
- Ves el total vendido rápidamente

#### 2. Productos Más Vendidos

**Qué muestra:** Qué vende más

```
PRODUCTOS MÁS VENDIDOS - SEPTIEMBRE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Chile Guajillo    → 120 kg    → $14,400
2. Coca Cola 600ml   → 450 pz    → $ 9,900
3. Leche descremada  → 380 lts   → $ 6,080
4. Semillas girasol  → 95 kg     → $ 3,800
```

**Para qué sirve:** Sabes qué reabastecer primero.

#### 3. Reporte de Ganancias

**Qué muestra:** Ganancia real (NO solo ventas)

```
GANANCIAS - SEPTIEMBRE 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━
Ventas totales:      $58,350.00
Costo de mercancía:  $41,000.00
─────────────────────────────────
Ganancia bruta:      $17,350.00
Margen:              29.7%
```

**Importante:** No confundas ventas con ganancias. La ganancia es lo que realmente ganas.

#### 4. Inventario

**Qué muestra:** Qué tienes en stock y su valor

```
INVENTARIO - 29/09/2026
━━━━━━━━━━━━━━━━━━━━━━━━
Chile Guajillo    →  8.5 kg   → Valor: $1,020.00
Coca Cola 600ml   → 45 pz     → Valor:   $990.00
Leche descremada  → 12 lts    → Valor:   $192.00
Semillas girasol  →  5 kg     → Valor:   $250.00
─────────────────────────────────────────────
VALOR TOTAL DEL INVENTARIO: $2,452.00
```

#### 5. Reporte de Compras

**Qué muestra:** Qué compraste a proveedores

```
COMPRAS - ÚLTIMOS 30 DÍAS
━━━━━━━━━━━━━━━━━━━━━━━━━
25/09 | Proveedor A | Chile Guajillo x50kg | $4,000
23/09 | Proveedor B | Coca Cola x100 cajas | $2,200
20/09 | Proveedor A | Leche x80 lts       | $1,600
```

### Exportar reportes

Todos los reportes se pueden descargar:

- **PDF** - Para imprimir o enviar por correo
- **Excel** - Para editar o analizar en Excel

Haz clic en **[EXPORTAR PDF]** o **[EXPORTAR EXCEL]**

---

## 9. Preguntas Frecuentes

### ¿Se pierden las ventas si se va la luz?

**No, si ya hiciste clic en COBRAR.** El sistema las guarda inmediatamente.

Si se va antes de hacer clic en COBRAR, la venta NO se guarda.

**Recomendación:** Usa un No Break (UPS) para proteger la computadora.

### ¿Puedo cancelar una venta que ya hice?

Sí. Ve a **REPORTES → Ventas**, encuentra la venta y haz clic en **[CANCELAR]**.

⚠️ Solo administradores pueden cancelar.

### ¿Qué hago si me equivoco al escribir el peso?

Si aún no hiciste clic en COBRAR:
1. Haz clic en la **X** del producto
2. Vuélvelo a agregar con el peso correcto

Si ya cobraste, necesitas cancelar la venta (solo admin).

### ¿Cómo cambio mi contraseña?

Pídele al administrador que la cambie desde **CONFIGURACIÓN → USUARIOS**.

O si eres administrador, hazlo tú mismo.

### ¿El sistema funciona sin Internet?

**SÍ, completamente.** Todo se guarda en la computadora local.

### ¿Dónde veo las ventas de días anteriores?

Ve a **REPORTES** y selecciona el rango de fechas que quieras consultar.

---

## 10. Solución de Problemas

### La aplicación no abre

**Problema:** Doble clic y no pasa nada.

**Solución:**
1. Revisa si la aplicación está en la carpeta correcta
2. Si está corrompida, pide reinstalarla

### "Stock insuficiente" pero hay stock

**Problema:** El sistema dice que no hay pero sí hay.

**Solución:**
1. Ve a **INVENTARIO**
2. Busca el producto
3. Revisa en **MOVIMIENTOS** para ver qué pasó
4. Puede ser que haya otro usuario vendiendo simultáneamente

### La venta se quedó "colgada"

**Problema:** La pantalla no responde durante una venta.

**Solución:**
1. Espera 30 segundos
2. Si no responde, cierra la aplicación (Alt+F4)
3. Abre de nuevo y vuelve a intentar

### No veo algunos productos

**Problema:** Un producto que existe no aparece en la búsqueda.

**Soluciones:**
1. Revisa si está **desactivado** (estado inactivo)
2. Busca por código de barras en lugar de nombre
3. Consulta con admin si fue desactivado a propósito

### Diferencia en el corte de caja

**Problema:** Faltan o sobran pesos en el corte.

**Qué revisar:**
1. ¿Diste mal el cambio a un cliente?
2. ¿Cobraste un fiado que no está registrado?
3. ¿Hay una devolución no registrada?

Anotalo en **Observaciones** del corte. El admin puede investigar en los reportes.

---

**FIN DEL MANUAL DE USUARIO**

---

## Contacto y Soporte

Si tienes dudas que no vienen en este manual:

1. Consulta al administrador de tu tienda
2. Revisa si hay un archivo de errores: `data/errores.log`
3. En última instancia, solicita soporte técnico

**Recuerda:** Cuanto mejor uses el sistema, más ganancias verás en tu tienda. ✓
