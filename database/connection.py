"""
Conexión a base de datos usando SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import DATABASE_URL

# Crear motor de base de datos
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Cambiar a True para debug SQL
    connect_args={"check_same_thread": False}  # Necesario para SQLite
)

# Sesión de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


def get_db():
    """Generador de sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Inicializar la base de datos completa con datos semilla."""
    from services.db_init_service import inicializar_base_datos
    return inicializar_base_datos()