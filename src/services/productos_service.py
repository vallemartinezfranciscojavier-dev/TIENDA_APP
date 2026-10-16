"""
Servicio de productos.
Gestiona el CRUD de productos con validaciones, búsqueda y movimientos de inventario.
"""

from database.connection import get_db
from database.models import (
    Producto,
    Categoria,
    Inventario,
    MovimientoInventario,
    TipoVentaEnum,
    TipoMovimientoEnum,
)
from utils.validators import validar_codigo_barras
from services.bitacora_service import BitacoraService
from services.seguridad_service import requiere_permiso, PermisoDenegado
from services.permisos_service import tiene_permiso
from services.sesion_service import obtener_rol, obtener_usuario_id
from utils.barcode import generar_ean13, normalizar_codigo_barras
from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload
from decimal import Decimal


# Unidad de medida sugerida según el tipo de venta
UNIDAD_POR_TIPO_VENTA = {
    TipoVentaEnum.PIEZA: "pza",
    TipoVentaEnum.KILOGRAMO: "kg",
    TipoVentaEnum.GRAMOS: "g",
    TipoVentaEnum.BOLSA: "bolsa",
    TipoVentaEnum.UNIDAD_PERSONALIZADA: "unidad",
}


class ProductosService:
    def __init__(self):
        pass

    def _generar_codigo_interno(self, db) -> str:
        """Generar un código interno único de tipo P-0001."""
        total = db.query(func.count(Producto.id)).scalar() or 0
        # Buscar el siguiente número disponible
        for i in range(total + 1, total + 10000):
            codigo = f"P-{i:04d}"
            existe = db.query(Producto).filter(Producto.codigo == codigo).first()
            if not existe:
                return codigo
        raise ValueError("No se pudo generar un código interno disponible.")

    def _preparar_codigo_barras(self, db, codigo_barras: str, exclude_id: int = None) -> str:
        """
        Normalizar el código de barras o generar uno (EAN-13) si viene vacío.
        Levanta ValueError si el código está duplicado o no se puede normalizar.
        """
        codigo = (codigo_barras or "").strip()

        if codigo:
            normalizado = normalizar_codigo_barras(codigo)
            if not normalizado or not validar_codigo_barras(normalizado):
                raise ValueError("El código de barras no es válido.")
            duplicado = db.query(Producto).filter(
                Producto.codigo_barras == normalizado
            ).first()
            if duplicado and duplicado.id != exclude_id:
                raise ValueError("El código de barras ya está registrado en otro producto.")
            return normalizado

        # Sin código de barras: generar un EAN-13 único
        for _ in range(20):
            codigo = generar_ean13()
            duplicado = db.query(Producto).filter(
                or_(
                    Producto.codigo == codigo,
                    Producto.codigo_barras == codigo,
                )
            ).first()
            if not duplicado:
                return codigo
        raise ValueError("No se pudo generar un código de barras disponible.")

    def _validar_nombre(self, db, nombre: str, exclude_id: int = None):
        """Validar que el nombre no esté vacío ni duplicado."""
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre del producto es obligatorio.")
        duplicado = db.query(Producto).filter(
            func.lower(Producto.nombre) == nombre.lower()
        ).first()
        if duplicado and duplicado.id != exclude_id:
            raise ValueError("Ya existe un producto con ese nombre.")

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def obtener_todos(self, incluir_inactivos: bool = False):
        """Obtener todos los productos."""
        db = next(get_db())
        try:
            q = db.query(Producto).options(
                joinedload(Producto.categoria),
                joinedload(Producto.inventario),
            )
            if not incluir_inactivos:
                q = q.filter(Producto.activo == True)
            return q.order_by(Producto.nombre).all()
        finally:
            db.close()

    def obtener_por_id(self, producto_id: int):
        """Obtener un producto por su id."""
        db = next(get_db())
        try:
            return db.query(Producto).options(
                joinedload(Producto.categoria),
                joinedload(Producto.inventario),
            ).filter(Producto.id == producto_id).first()
        finally:
            db.close()

    def obtener_por_codigo_barras(self, codigo_barras: str):
        """Obtener un producto por su código de barras.

        Se cargan las relaciones (categoría e inventario) para que el objeto
        siga siendo usable tras cerrar la sesión (p. ej. en el punto de venta).
        """
        db = next(get_db())
        try:
            return db.query(Producto).options(
                joinedload(Producto.categoria),
                joinedload(Producto.inventario),
            ).filter(Producto.codigo_barras == codigo_barras).first()
        finally:
            db.close()

    def obtener_categorias(self):
        """Obtener todas las categorías activas."""
        db = next(get_db())
        try:
            return db.query(Categoria).filter(Categoria.activa == True).order_by(Categoria.nombre).all()
        finally:
            db.close()

    def buscar(self, termino: str = "", categoria_id: int = None, estado: str = "todos"):
        """
        Buscar productos por texto, categoría y estado.

        Args:
            termino: Texto para buscar en nombre, código y código de barras.
            categoria_id: Filtro por categoría (None = todas).
            estado: "todos", "activos" o "inactivos".
        """
        db = next(get_db())
        try:
            q = db.query(Producto).options(
                joinedload(Producto.categoria),
                joinedload(Producto.inventario),
            )

            if estado == "activos":
                q = q.filter(Producto.activo == True)
            elif estado == "inactivos":
                q = q.filter(Producto.activo == False)

            if categoria_id:
                q = q.filter(Producto.categoria_id == categoria_id)

            termino = (termino or "").strip()
            if termino:
                patron = f"%{termino}%"
                q = q.filter(
                    or_(
                        Producto.nombre.ilike(patron),
                        Producto.codigo.ilike(patron),
                        Producto.codigo_barras.ilike(patron),
                    )
                )

            return q.order_by(Producto.nombre).all()
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Crear
    # ------------------------------------------------------------------

    @requiere_permiso("modificar_productos")
    def crear(self, datos: dict):
        """
        Crear un producto nuevo.

        Crea automáticamente el registro de inventario inicial y, si el stock
        inicial es mayor a 0, registra un movimiento de entrada.

        Returns:
            Producto creado.

        Raises:
            ValueError: Si algún dato no es válido.
        """
        nombre = (datos.get("nombre") or "").strip()
        if not nombre:
            raise ValueError("El nombre del producto es obligatorio.")

        # Validar precios y stock
        try:
            precio_venta = Decimal(str(datos.get("precio_venta") or 0))
            precio_compra = Decimal(str(datos.get("precio_compra") or 0))
            stock_inicial = Decimal(str(datos.get("stock_inicial") or 0))
            stock_minimo = Decimal(str(datos.get("stock_minimo") or 0))
        except Exception:
            raise ValueError("Los valores de precio y stock no son válidos.")

        if precio_venta <= 0:
            raise ValueError("El precio de venta debe ser mayor a cero.")
        if precio_compra < 0 or stock_inicial < 0 or stock_minimo < 0:
            raise ValueError("Precio de compra y stock no pueden ser negativos.")

        datos = dict(datos)
        db = next(get_db())
        try:
            self._validar_nombre(db, nombre)
            codigo_barras = self._preparar_codigo_barras(db, datos.get("codigo_barras"))
            codigo_interno = self._generar_codigo_interno(db)

            tipo_venta = datos.get("tipo_venta", TipoVentaEnum.PIEZA)
            if isinstance(tipo_venta, str):
                tipo_venta = TipoVentaEnum(tipo_venta)

            producto = Producto(
                codigo=codigo_interno,
                codigo_barras=codigo_barras,
                nombre=nombre,
                descripcion=datos.get("descripcion"),
                categoria_id=int(datos["categoria_id"]),
                tipo_venta=tipo_venta,
                precio_venta=precio_venta,
                precio_compra=precio_compra if precio_compra > 0 else None,
                unidad_medida=UNIDAD_POR_TIPO_VENTA.get(tipo_venta, "pza"),
                peso_por_unidad=datos.get("peso_por_unidad"),
                stock_minimo=stock_minimo,
                activo=True,
            )
            db.add(producto)
            db.flush()  # Asigna producto.id

            # Inventario inicial
            inventario = Inventario(producto_id=producto.id, cantidad=stock_inicial)
            db.add(inventario)

            # Movimiento de entrada inicial (solo si hay stock)
            if stock_inicial > 0:
                db.add(MovimientoInventario(
                    producto_id=producto.id,
                    tipo=TipoMovimientoEnum.ENTRADA,
                    cantidad=stock_inicial,
                    cantidad_anterior=Decimal("0"),
                    cantidad_nueva=stock_inicial,
                    notas="Stock inicial de producto",
                    referencia_tipo="alta_inicial",
                ))

            db.commit()

            # Recargar con relaciones cargadas (evita lazy load fuera de sesión)
            producto = db.query(Producto).options(
                joinedload(Producto.categoria),
                joinedload(Producto.inventario),
            ).filter(Producto.id == producto.id).first()

            # Auditoría (Fase 15)
            BitacoraService().registrar(
                usuario_id=obtener_usuario_id(),
                accion="crear_producto",
                detalle=f"Alta de producto '{producto.nombre}' (código {producto.codigo})",
            )
            return producto
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Actualizar
    # ------------------------------------------------------------------

    @requiere_permiso("modificar_productos")
    def actualizar(self, producto_id: int, datos: dict, nuevo_stock: Decimal = None):
        """
        Actualizar un producto existente.

        Si nuevo_stock se proporciona y difiere del stock actual, se ajusta el
        inventario y se registra un movimiento de tipo AJUSTE.

        Returns:
            Producto actualizado.

        Raises:
            ValueError: Si algún dato no es válido.
        """
        db = next(get_db())
        try:
            producto = db.query(Producto).filter(Producto.id == producto_id).first()
            if not producto:
                raise ValueError("El producto no existe.")

            nombre = (datos.get("nombre") or "").strip()
            self._validar_nombre(db, nombre, exclude_id=producto_id)

            try:
                precio_venta = Decimal(str(datos.get("precio_venta") or 0))
                precio_compra = Decimal(str(datos.get("precio_compra") or 0))
                stock_minimo = Decimal(str(datos.get("stock_minimo") or 0))
            except Exception:
                raise ValueError("Los valores de precio y stock no son válidos.")

            if precio_venta <= 0:
                raise ValueError("El precio de venta debe ser mayor a cero.")
            if precio_compra < 0 or stock_minimo < 0:
                raise ValueError("Precio de compra y stock mínimo no pueden ser negativos.")

            # Fase 14: modificar el PRECIO de un producto exige además el
            # permiso "modificar_precios" (no solo "modificar_productos").
            # Si el precio no cambia, basta con el permiso del decorador.
            precio_compra_actual = (
                producto.precio_compra if producto.precio_compra is not None else Decimal(0)
            )
            # Auditoría (Fase 15): distinguir edición simple de cambio de precio.
            hubo_cambio_precio = False
            if precio_venta != producto.precio_venta or precio_compra != precio_compra_actual:
                if not tiene_permiso(obtener_rol(), "modificar_precios"):
                    raise PermisoDenegado(
                        "No tiene permiso para modificar precios."
                    )
                hubo_cambio_precio = True

            # Código de barras (solo si se envía el campo)
            if "codigo_barras" in datos:
                producto.codigo_barras = self._preparar_codigo_barras(
                    db, datos.get("codigo_barras"), exclude_id=producto_id
                )

            tipo_venta = datos.get("tipo_venta", producto.tipo_venta)
            if isinstance(tipo_venta, str):
                tipo_venta = TipoVentaEnum(tipo_venta)

            producto.nombre = nombre
            producto.descripcion = datos.get("descripcion")
            producto.categoria_id = int(datos["categoria_id"])
            producto.tipo_venta = tipo_venta
            producto.unidad_medida = UNIDAD_POR_TIPO_VENTA.get(tipo_venta, "pza")
            producto.precio_venta = precio_venta
            producto.precio_compra = precio_compra if precio_compra > 0 else None
            producto.stock_minimo = stock_minimo
            if "activo" in datos:
                producto.activo = bool(datos.get("activo"))

            # Ajuste de stock manual. Se valida y aplica ANTES del commit,
            # en la misma transacción del producto, para no guardar cambios
            # parciales si el stock es inválido o el registro falla.
            if nuevo_stock is not None:
                nueva_cantidad = Decimal(str(nuevo_stock))
                if nueva_cantidad < 0:
                    raise ValueError("El stock no puede ser negativo.")

                inventario = (
                    db.query(Inventario)
                    .filter(Inventario.producto_id == producto_id)
                    .first()
                )
                if not inventario:
                    inventario = Inventario(producto_id=producto_id, cantidad=0)
                    db.add(inventario)

                cantidad_anterior = Decimal(str(inventario.cantidad))
                if nueva_cantidad != cantidad_anterior:
                    inventario.cantidad = nueva_cantidad
                    db.add(MovimientoInventario(
                        producto_id=producto_id,
                        tipo=TipoMovimientoEnum.AJUSTE,
                        cantidad=nueva_cantidad - cantidad_anterior,
                        cantidad_anterior=cantidad_anterior,
                        cantidad_nueva=nueva_cantidad,
                        notas="Ajuste manual de stock desde edición de producto",
                        referencia_tipo="ajuste",
                    ))

            db.commit()

            # Recargar con relaciones cargadas (evita lazy load fuera de sesión)
            producto = db.query(Producto).options(
                joinedload(Producto.categoria),
                joinedload(Producto.inventario),
            ).filter(Producto.id == producto.id).first()

            # Auditoría (Fase 15)
            accion_auditoria = "cambio_precio" if hubo_cambio_precio else "editar_producto"
            BitacoraService().registrar(
                usuario_id=obtener_usuario_id(),
                accion=accion_auditoria,
                detalle=(
                    ("Cambio de precio" if hubo_cambio_precio else "Edición de producto")
                    + f" '{producto.nombre}': venta {producto.precio_venta}, "
                    f"compra {producto.precio_compra or 0}"
                ),
            )
            return producto
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Activar / Desactivar (eliminación lógica)
    # ------------------------------------------------------------------

    @requiere_permiso("modificar_productos")
    def desactivar(self, producto_id: int):
        """Desactivar un producto (eliminación lógica)."""
        db = next(get_db())
        try:
            producto = db.query(Producto).filter(Producto.id == producto_id).first()
            if not producto:
                raise ValueError("El producto no existe.")
            producto.activo = False
            db.commit()
            db.refresh(producto)
            # Auditoría (Fase 15)
            BitacoraService().registrar(
                usuario_id=obtener_usuario_id(),
                accion="desactivar_producto",
                detalle=f"Producto desactivado: {producto.nombre}",
            )
            return producto
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def activar(self, producto_id: int):
        """Activar un producto."""
        db = next(get_db())
        try:
            producto = db.query(Producto).filter(Producto.id == producto_id).first()
            if not producto:
                raise ValueError("El producto no existe.")
            producto.activo = True
            db.commit()
            db.refresh(producto)
            # Auditoría (Fase 15)
            BitacoraService().registrar(
                usuario_id=obtener_usuario_id(),
                accion="activar_producto",
                detalle=f"Producto reactivado: {producto.nombre}",
            )
            return producto
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()