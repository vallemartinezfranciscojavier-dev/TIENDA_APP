# TIENDA_APP — Sistema de Gestión Comercial

## Estado
- **Fases completadas**: 1-15 (100%)
- **Última actualización**: 2026-09-16
- **Versión ejecutable**: Reempaquetado con PyInstaller, verificado arranque 6/6

## Descripción
Sistema de gestión comercial con:
- Gestión de inventario y productos
- Auditoría con filtros avanzados
- Respaldos programados por horas (retención configurable)
- Generación de códigos de barras (Code128, EAN13)
- Reportes integrados

## Estructura
```
src/
  main.py              # Punto de entrada
  components/          # Componentes UI
  utils/              # Utilidades
  views/              # Vistas principales
  services/           # Lógica de negocio
database/             # Esquema y migraciones
tests/                # Suite de pruebas (36/36 pasando)
docs/                 # Documentación
config/               # Configuraciones
```

## Pruebas
```bash
python -m pytest tests/
```

## Compilación (Windows)
```bash
pyinstaller "Sistema de Gestion Comercial.spec"
```

## Notas de desarrollo
- Tests: 36/36 pasando
- Arranque: 16/16 configuraciones validadas
- Auditoría: filtros por fecha, usuario, tipo de operación
- Respaldos: automáticos cada hora con compresión

## Próximas mejoras
- Integración con APIs externas
- Dashboard de análisis
- Reportes exportables a Excel/PDF
