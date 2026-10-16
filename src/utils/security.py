"""
Utilidades de seguridad: hash de contraseñas con bcrypt.
"""

import bcrypt
from typing import Optional


def hash_password(password: str) -> str:
    """
    Generar hash bcrypt de una contraseña.

    Args:
        password: Contraseña en texto plano

    Returns:
        Hash bcrypt como string (incluye salt)
    """
    if not password:
        raise ValueError("La contraseña no puede estar vacía")

    # bcrypt.gensalt() genera un salt aleatorio
    # bcrypt.hashpw() combina password + salt y hashea
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds = buen balance seguridad/velocidad
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    Verificar una contraseña contra su hash.

    Args:
        password: Contraseña en texto plano a verificar
        hashed: Hash bcrypt almacenado en BD

    Returns:
        True si la contraseña coincide, False en caso contrario
    """
    if not password or not hashed:
        return False

    try:
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # Si hay cualquier error (hash inválido, etc.), retorna False
        return False


def generar_password_aleatorio(longitud: int = 12) -> str:
    """
    Generar contraseña aleatoria segura.

    Args:
        longitud: Longitud de la contraseña (mín 8)

    Returns:
        Contraseña aleatoria
    """
    import secrets
    import string

    if longitud < 8:
        longitud = 8

    # Caracteres permitidos (sin caracteres ambiguos)
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    # Excluir caracteres ambiguos: l, I, 1, 0, O, o
    chars = chars.replace('l', '').replace('I', '').replace('1', '') \
                 .replace('0', '').replace('O', '').replace('o', '')

    return ''.join(secrets.choice(chars) for _ in range(longitud))


def validar_fortaleza_password(password: str) -> tuple[bool, list[str]]:
    """
    Validar fortaleza de contraseña.

    Args:
        password: Contraseña a validar

    Returns:
        Tupla (es_valida, lista_advertencias)
    """
    advertencias = []

    if not password:
        return False, ["La contraseña no puede estar vacía"]

    if len(password) < 8:
        advertencias.append("Mínimo 8 caracteres")

    if not any(c.isupper() for c in password):
        advertencias.append("Debe contener al menos una mayúscula")

    if not any(c.islower() for c in password):
        advertencias.append("Debe contener al menos una minúscula")

    if not any(c.isdigit() for c in password):
        advertencias.append("Debe contener al menos un número")

    if not any(c in "!@#$%^&*" for c in password):
        advertencias.append("Debe contener al menos un símbolo (!@#$%^&*)")

    es_valida = len(advertencias) == 0
    return es_valida, advertencias