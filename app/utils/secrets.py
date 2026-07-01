import base64
import hashlib

from app.config import get_settings


def _key_stream(length: int) -> bytes:
    settings = get_settings()
    secret = settings.op_token_secret or settings.bot_token
    seed = hashlib.sha256(secret.encode("utf-8")).digest()
    chunks = []
    counter = 0
    while sum(len(chunk) for chunk in chunks) < length:
        chunks.append(hashlib.sha256(seed + counter.to_bytes(4, "big")).digest())
        counter += 1
    return b"".join(chunks)[:length]


def encrypt_token(token: str) -> str:
    data = token.encode("utf-8")
    encrypted = bytes(byte ^ key for byte, key in zip(data, _key_stream(len(data))))
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_token(value: str) -> str:
    encrypted = base64.urlsafe_b64decode(value.encode("ascii"))
    data = bytes(byte ^ key for byte, key in zip(encrypted, _key_stream(len(encrypted))))
    return data.decode("utf-8")


def token_hint(token: str) -> str:
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"
