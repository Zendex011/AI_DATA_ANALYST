"""
Symmetric encryption for secrets stored in the database -- currently just
each user's own Gemini API key (users.gemini_api_key). Without this, a
Postgres dump or a leaked DB credential hands over every user's API key
in plaintext.
"""

from cryptography.fernet import Fernet, InvalidToken
from app.config import ENCRYPTION_KEY

_fernet = Fernet(ENCRYPTION_KEY.encode())


def encrypt_secret(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        # Happens if ENCRYPTION_KEY changed since this value was encrypted,
        # or the stored value is corrupt. Treat as "no usable key" rather
        # than crashing the request.
        raise ValueError("Could not decrypt stored API key")
