import json
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Lazy singleton — avoids importing settings at module load time."""
    from .config import settings
    return Fernet(settings.ENCRYPTION_KEY.encode())


class EncryptedText(TypeDecorator):
    """
    Transparent field-level encryption for string/text columns.

    Encrypts with Fernet (AES-128-CBC + HMAC-SHA256) on write and decrypts on
    read. If a value cannot be decrypted (e.g. a plaintext row written before
    encryption was enabled), it is returned as-is so existing data stays
    accessible. It will be encrypted the next time that row is written.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, _dialect):
        if value is None:
            return None
        return _get_fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, _dialect):
        if value is None:
            return None
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Pre-encryption plaintext row — return as-is, encrypted on next write.
            return value


class EncryptedJSON(TypeDecorator):
    """
    Transparent field-level encryption for JSON data stored in a TEXT column.

    Serialises the Python object to a JSON string, encrypts it, then stores the
    result as TEXT. On read, decrypts and deserialises back to a Python object.
    Falls back to plain JSON parsing for rows written before encryption was enabled.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, _dialect):
        if value is None:
            return None
        return _get_fernet().encrypt(json.dumps(value).encode()).decode()

    def process_result_value(self, value, _dialect):
        if value is None:
            return None
        try:
            return json.loads(_get_fernet().decrypt(value.encode()).decode())
        except InvalidToken:
            # Pre-encryption row — value is a plain JSON string.
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return value
