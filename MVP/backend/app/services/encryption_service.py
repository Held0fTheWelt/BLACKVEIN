"""AES-256 encryption/decryption service for protecting exported data at rest.

This module provides utilities for:
- Encrypting exported data with AES-256-CBC using user-provided password
- Deriving encryption keys from passwords using PBKDF2
- Generating random IVs and salts
- Decrypting encrypted payloads
"""
from __future__ import annotations

import base64
import json
from typing import Dict, Any, Tuple

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.backends import default_backend
import os


# Constants
ENCRYPTION_VERSION = 1
KEY_SIZE = 32  # 256 bits for AES-256
IV_SIZE = 16  # 128 bits for CBC mode
SALT_SIZE = 16  # 128 bits for PBKDF2
PBKDF2_ITERATIONS = 100000


def _generate_random_bytes(length: int) -> bytes:
    """Generate cryptographically secure random bytes."""
    return os.urandom(length)


def _derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit encryption key from password using PBKDF2.

    Args:
        password: User-provided password string
        salt: Random salt bytes for key derivation

    Returns:
        32-byte (256-bit) encryption key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    return kdf.derive(password.encode('utf-8'))


def encrypt_export(export_data: Dict[str, Any], password: str) -> Dict[str, Any]:
    """Encrypt exported data with AES-256-CBC.

    The export_data is first converted to JSON, then encrypted using AES-256-CBC
    with a randomly generated IV. The key is derived from the password using PBKDF2
    with a random salt.

    Args:
        export_data: Dictionary containing metadata and data sections to encrypt
        password: User-provided password for encryption

    Returns:
        Dictionary containing:
            - encrypted_data: base64-encoded ciphertext
            - iv: base64-encoded initialization vector
            - salt: base64-encoded salt for key derivation
            - version: encryption format version
            - algorithm: encryption algorithm used (AES-256-CBC)
            - pbkdf2_iterations: number of PBKDF2 iterations used

    Raises:
        TypeError: If export_data cannot be serialized to JSON
        ValueError: If password is empty
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")

    # Serialize export data to JSON
    plaintext_json = json.dumps(export_data, sort_keys=True, separators=(",", ":"))
    plaintext = plaintext_json.encode('utf-8')

    # Apply PKCS7 padding
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_plaintext = padder.update(plaintext) + padder.finalize()

    # Generate random salt and IV
    salt = _generate_random_bytes(SALT_SIZE)
    iv = _generate_random_bytes(IV_SIZE)

    # Derive encryption key from password
    key = _derive_key_from_password(password, salt)

    # Encrypt data using AES-256-CBC
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend(),
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()

    # Return encrypted payload with metadata
    return {
        "encrypted_data": base64.b64encode(ciphertext).decode('utf-8'),
        "iv": base64.b64encode(iv).decode('utf-8'),
        "salt": base64.b64encode(salt).decode('utf-8'),
        "version": ENCRYPTION_VERSION,
        "algorithm": "AES-256-CBC",
        "pbkdf2_iterations": PBKDF2_ITERATIONS,
    }


def decrypt_export(encrypted_payload: Dict[str, Any], password: str) -> Dict[str, Any]:
    """Decrypt an encrypted export payload.

    Args:
        encrypted_payload: Dictionary containing encrypted_data, iv, salt, and metadata
        password: User-provided password for decryption

    Returns:
        Decrypted export data dictionary (with metadata and data sections)

    Raises:
        ValueError: If payload format is invalid, password is wrong, decryption fails, or decrypted data is not valid JSON
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")

    # Validate payload structure
    required_fields = ["encrypted_data", "iv", "salt"]
    for field in required_fields:
        if field not in encrypted_payload:
            raise ValueError(f"Missing required field: {field}")

    # Decode from base64
    try:
        ciphertext = base64.b64decode(encrypted_payload["encrypted_data"])
        iv = base64.b64decode(encrypted_payload["iv"])
        salt = base64.b64decode(encrypted_payload["salt"])
    except Exception as exc:
        raise ValueError(f"Invalid base64 encoding in payload: {exc}")

    # Validate sizes
    if len(iv) != IV_SIZE:
        raise ValueError(f"Invalid IV size: expected {IV_SIZE}, got {len(iv)}")
    if len(salt) != SALT_SIZE:
        raise ValueError(f"Invalid salt size: expected {SALT_SIZE}, got {len(salt)}")

    # Derive key using password and salt
    key = _derive_key_from_password(password, salt)

    # Decrypt
    try:
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    except Exception as exc:
        # Could indicate wrong password or corrupted data
        raise ValueError(f"Decryption failed: {exc}")

    # Remove PKCS7 padding
    try:
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
    except Exception as exc:
        raise ValueError(f"Invalid padding in decrypted data: {exc}")

    # Decode and parse JSON
    try:
        plaintext_json = plaintext.decode('utf-8')
        export_data = json.loads(plaintext_json)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Decrypted data is not valid JSON: {exc}")

    return export_data
