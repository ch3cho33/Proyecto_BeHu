"""Cifrado AES-256-GCM y sello HMAC. La clave sale de JWT_SECRET (sobre local, compatible con KMS)."""

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _clave() -> bytes:
    material = settings.jwt_secret.encode()
    if settings.aws_kms_key_id:
        material = f"{settings.jwt_secret}:{settings.aws_kms_key_id}".encode()
    return hashlib.sha256(material).digest()


def cifrar(contenido: bytes) -> str:
    nonce = os.urandom(12)
    cifrado = AESGCM(_clave()).encrypt(nonce, contenido, None)
    return base64.b64encode(nonce + cifrado).decode()


def descifrar(token: str) -> bytes:
    crudo = base64.b64decode(token.encode())
    return AESGCM(_clave()).decrypt(crudo[:12], crudo[12:], None)


def sello_ledger(*, transaccion_id: str, cuenta_id: str, naturaleza: str, monto: str) -> str:
    mensaje = f"{transaccion_id}|{cuenta_id}|{naturaleza}|{monto}".encode()
    return hmac.new(_clave(), mensaje, hashlib.sha256).hexdigest()
