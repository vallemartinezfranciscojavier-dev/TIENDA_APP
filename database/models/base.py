"""
Modelos de base de datos para el sistema de tienda.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    Enum as SQLEnum,
    Date,
    Time,
    Numeric,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
import enum
import datetime


class TipoVentaEnum(str, enum.Enum):
    PIEZA = "pieza"
    KILOGRAMO = "kilogramo"
    GRAMOS = "gramos"
    BOLSA = "bolsa"
    UNIDAD_PERSONALIZADA = "unidad_personalizada"


class EstadoVentaEnum(str, enum.Enum):
    PENDIENTE = "pendiente"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"
    FIADO = "fiado"


class TipoMovimientoEnum(str, enum.Enum):
    ENTRADA = "entrada"
    SALIDA = "salida"
    AJUSTE = "ajuste"
    DEVOLUCION = "devolucion"


class RolUsuarioEnum(str, enum.Enum):
    ADMIN = "admin"
    VENDEDOR = "vendedor"
    CAJERO = "cajero"
    ALMACEN = "almacen"


class MetodoPagoEnum(str, enum.Enum):
    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"
    TRANSFERENCIA = "transferencia"
    FIADO = "fiado"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    usuario = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(SQLEnum(RolUsuarioEnum), default=RolUsuarioEnum.VENDEDOR, nullable=False)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    ventas = relationship("Venta", back_populates="usuario")
    cortes_caja = relationship("CorteCaja", back_populates="usuario")


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    activa = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())

    # Relaciones
    productos = relationship("Producto", back_populates="categoria")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    codigo_barras = Column(String(100), unique=True, nullable=True, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    tipo_venta = Column(SQLEnum(TipoVentaEnum), default=TipoVentaEnum.PIEZA, nullable=False)
    precio_venta = Column(Numeric(10, 2), nullable=False)
    precio_compra = Column(Numeric(10, 2), nullable=True)
    unidad_medida = Column(String(20), default="pza")
    peso_por_unidad = Column(Numeric(10, 3), nullable=True)  # Para productos por peso
    stock_minimo = Column(Numeric(10, 3), default=0)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    categoria = relationship("Categoria", back_populates="productos")
    inventario = relationship("Inventario", back_populates="producto", uselist=False)
    detalles_venta = relationship("DetalleVenta", back_populates="producto")
    detalles_compra = relationship("DetalleCompra", back_populates="producto")
    movimientos = relationship("MovimientoInventario", back_populates="producto")


class Inventario(Base):
    __tablename__ = "inventario"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), unique=True, nullable=False)
    cantidad = Column(Numeric(10, 3), default=0, nullable=False)
    cantidad_reservada = Column(Numeric(10, 3), default=0, nullable=False)
    ultima_actualizacion = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    producto = relationship("Producto", back_populates="inventario")


class Venta(Base):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    folio = Column(String(20), unique=True, nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    corte_caja_id = Column(Integer, ForeignKey("cortes_caja.id"), nullable=True)
    # Hora local (importante para reportes de "ventas del día")
    fecha = Column(DateTime, default=datetime.datetime.now, index=True)
    subtotal = Column(Numeric(10, 2), default=0)
    descuento = Column(Numeric(10, 2), default=0)
    impuestos = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)
    metodo_pago = Column(SQLEnum(MetodoPagoEnum), default=MetodoPagoEnum.EFECTIVO)
    estado = Column(SQLEnum(EstadoVentaEnum), default=EstadoVentaEnum.PENDIENTE)
    notas = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.datetime.now)

    # Relaciones
    usuario = relationship("Usuario", back_populates="ventas")
    cliente = relationship("Cliente", back_populates="ventas")
    detalles = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")
    corte_caja = relationship("CorteCaja", back_populates="ventas")


class DetalleVenta(Base):
    __tablename__ = "detalle_ventas"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Numeric(10, 3), nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    descuento = Column(Numeric(10, 2), default=0)
    subtotal = Column(Numeric(10, 2), nullable=False)

    # Relaciones
    venta = relationship("Venta", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_venta")


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    telefono = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    direccion = Column(Text, nullable=True)
    limite_credito = Column(Numeric(10, 2), default=0)
    saldo_actual = Column(Numeric(10, 2), default=0)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    ventas = relationship("Venta", back_populates="cliente")
    creditos = relationship("Credito", back_populates="cliente")


class Credito(Base):
    __tablename__ = "creditos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=True)
    monto_original = Column(Numeric(10, 2), nullable=False)
    monto_pendiente = Column(Numeric(10, 2), nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)
    pagado = Column(Boolean, default=False)
    # Hora local (consistente con Abono.fecha) para que el historial no cambie de día
    fecha_creacion = Column(DateTime, default=datetime.datetime.now)
    fecha_pago = Column(DateTime, nullable=True)

    # Relaciones
    cliente = relationship("Cliente", back_populates="creditos")
    venta = relationship("Venta")
    abonos = relationship("Abono", back_populates="credito", order_by="Abono.fecha")


class Abono(Base):
    """Abono (pago parcial) aplicado a un crédito/fiado de un cliente."""

    __tablename__ = "abonos"

    id = Column(Integer, primary_key=True, index=True)
    credito_id = Column(Integer, ForeignKey("creditos.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    monto = Column(Numeric(10, 2), nullable=False)
    notas = Column(Text, nullable=True)
    fecha = Column(DateTime, default=datetime.datetime.now, index=True)

    # Relaciones
    credito = relationship("Credito", back_populates="abonos")
    usuario = relationship("Usuario")


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    contacto = Column(String(100), nullable=True)
    telefono = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    direccion = Column(Text, nullable=True)
    rfc = Column(String(13), nullable=True)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())

    # Relaciones
    compras = relationship("Compra", back_populates="proveedor")


class Compra(Base):
    __tablename__ = "compras"

    id = Column(Integer, primary_key=True, index=True)
    folio = Column(String(20), unique=True, nullable=False, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)
    # Hora local (importante para reportes y fechas de compra)
    fecha = Column(DateTime, default=datetime.datetime.now, index=True)
    subtotal = Column(Numeric(10, 2), default=0)
    impuestos = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)
    pagado = Column(Boolean, default=False)
    notas = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, server_default=func.now())

    # Relaciones
    proveedor = relationship("Proveedor", back_populates="compras")
    detalles = relationship("DetalleCompra", back_populates="compra", cascade="all, delete-orphan")


class DetalleCompra(Base):
    __tablename__ = "detalle_compras"

    id = Column(Integer, primary_key=True, index=True)
    compra_id = Column(Integer, ForeignKey("compras.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Numeric(10, 3), nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    # Relaciones
    compra = relationship("Compra", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_compra")


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    tipo = Column(SQLEnum(TipoMovimientoEnum), nullable=False)
    cantidad = Column(Numeric(10, 3), nullable=False)
    cantidad_anterior = Column(Numeric(10, 3), nullable=False)
    cantidad_nueva = Column(Numeric(10, 3), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    referencia_id = Column(Integer, nullable=True)  # ID de venta, compra, ajuste, etc.
    referencia_tipo = Column(String(50), nullable=True)  # 'venta', 'compra', 'ajuste', 'devolucion'
    notas = Column(Text, nullable=True)
    fecha = Column(DateTime, default=datetime.datetime.now, index=True)

    # Relaciones
    producto = relationship("Producto", back_populates="movimientos")
    usuario = relationship("Usuario")


class CorteCaja(Base):
    __tablename__ = "cortes_caja"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    # Hora local (igual que Venta.fecha) para que el corte de caja cuente
    # correctamente las ventas del periodo sin desfase de zona horaria.
    fecha_apertura = Column(DateTime, default=datetime.datetime.now)
    fecha_cierre = Column(DateTime, nullable=True)
    monto_inicial = Column(Numeric(10, 2), default=0)
    monto_final_sistema = Column(Numeric(10, 2), default=0)
    monto_final_real = Column(Numeric(10, 2), default=0)
    diferencia = Column(Numeric(10, 2), default=0)
    observaciones = Column(Text, nullable=True)
    cerrado = Column(Boolean, default=False)

    # Relaciones
    usuario = relationship("Usuario", back_populates="cortes_caja")
    ventas = relationship("Venta", back_populates="corte_caja")


class RegistroActividad(Base):
    """
    Bitácora de acciones importantes del sistema.

    Guarda quién (usuario), qué acción realizó y cuándo, para poder
    rastrear actividades relevantes (inicio/cierre de sesión, ventas,
    creación de usuarios, cambios de inventario, etc.).
    """

    __tablename__ = "registro_actividad"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    # Snapshot del nombre para conservarlo aunque el usuario se desactive
    usuario_nombre = Column(String(100), nullable=True)
    accion = Column(String(50), nullable=False)
    detalle = Column(Text, nullable=True)
    # Hora local (consistente con el resto de la aplicación)
    fecha = Column(DateTime, default=datetime.datetime.now, index=True)

    # Relaciones
    usuario = relationship("Usuario")