# Database Export Encryption Feature

This document describes the AES-256 encryption feature for protecting exported database data at rest.

## Overview

The encryption feature provides end-to-end protection for database exports using industry-standard AES-256-CBC encryption. Exported data can be encrypted with a user-provided password, generating an encrypted payload that is safe to store or transmit.

## Technical Details

### Encryption Algorithm
- **Algorithm**: AES-256-CBC (Advanced Encryption Standard, 256-bit key, Cipher Block Chaining)
- **Key Derivation**: PBKDF2-SHA256 with 100,000 iterations
- **IV Size**: 128 bits (16 bytes), randomly generated per encryption
- **Salt Size**: 128 bits (16 bytes), randomly generated per encryption
- **Key Size**: 256 bits (32 bytes)

### Security Characteristics
- **Confidentiality**: AES-256 provides strong encryption against brute-force attacks
- **Key Derivation**: PBKDF2 with high iteration count slows down password-based attacks
- **Randomization**: Each encryption uses a unique IV and salt, preventing pattern detection
- **No Authentication**: Standard CBC mode without authentication. Data integrity should be verified by the application (checksum in metadata is calculated before encryption)

## API Endpoints

### Export with Encryption

**Endpoint**: `POST /api/v1/data/export`

**Request**:
```json
{
  "scope": "full",
  "encrypt": true,
  "password": "your_secure_password_here"
}
```

**Parameters**:
- `scope`: Export scope - "full", "table", or "rows"
- `encrypt`: Boolean, whether to encrypt the export
- `password`: User-provided password (required if encrypt=true)
- Other scope-specific parameters (table name, primary_keys, etc.)

**Response** (Success, 200):
```json
{
  "encrypted": true,
  "encrypted_data": "base64_encoded_ciphertext...",
  "iv": "base64_encoded_iv...",
  "salt": "base64_encoded_salt...",
  "version": 1,
  "algorithm": "AES-256-CBC",
  "pbkdf2_iterations": 100000
}
```

**Response** (Error - Missing Password, 400):
```json
{
  "error": "Password required for encryption"
}
```

### Decrypt Export

**Endpoint**: `POST /api/v1/data/export/decrypt`

**Request**:
```json
{
  "encrypted_data": "base64_encoded_ciphertext...",
  "iv": "base64_encoded_iv...",
  "salt": "base64_encoded_salt...",
  "password": "your_secure_password_here"
}
```

**Parameters**:
- `encrypted_data`: Base64-encoded ciphertext from encryption
- `iv`: Base64-encoded initialization vector
- `salt`: Base64-encoded salt for key derivation
- `password`: User-provided password used during encryption

**Response** (Success, 200):
```json
{
  "metadata": {
    "format_version": 1,
    "application_version": "1.0.0",
    "exported_at": "2025-03-22T10:30:00+00:00",
    "scope": {"type": "full"},
    "tables": [{"name": "users", "row_count": 5}],
    ...
  },
  "data": {
    "tables": {
      "users": [...]
    }
  }
}
```

**Response** (Error - Wrong Password, 400):
```json
{
  "error": "Decryption failed: Decryption failed: ..."
}
```

## Standalone Decryption Script

For offline decryption without API access, use the standalone script:

```bash
python decrypt_export.py <encrypted_file.json> <password>
```

### Options

- `-o, --output <file>`: Write decrypted output to file (default: stdout)
- `-p, --pretty`: Pretty-print the JSON output (default: compact)

### Examples

```bash
# Decrypt to stdout
python decrypt_export.py export_encrypted.json mypassword

# Decrypt to file with pretty-printing
python decrypt_export.py export_encrypted.json mypassword -o decrypted.json -p

# Decrypt and pipe to another tool
python decrypt_export.py export_encrypted.json mypassword | jq '.data.tables.users'
```

## Usage Examples

### Python (using requests library)

```python
import requests
import json

BASE_URL = "http://localhost:5000/api/v1"
HEADERS = {"Authorization": f"Bearer {your_jwt_token}"}

# Export with encryption
export_payload = {
    "scope": "full",
    "encrypt": True,
    "password": "secure_password_123"
}

response = requests.post(f"{BASE_URL}/data/export", json=export_payload, headers=HEADERS)
encrypted_export = response.json()

# Save encrypted export to file
with open("export_encrypted.json", "w") as f:
    json.dump(encrypted_export, f)

# Later: decrypt
decrypt_payload = {
    "encrypted_data": encrypted_export["encrypted_data"],
    "iv": encrypted_export["iv"],
    "salt": encrypted_export["salt"],
    "password": "secure_password_123"
}

response = requests.post(f"{BASE_URL}/data/export/decrypt", json=decrypt_payload, headers=HEADERS)
decrypted_data = response.json()
```

### cURL

```bash
# Export with encryption
curl -X POST http://localhost:5000/api/v1/data/export \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "full",
    "encrypt": true,
    "password": "secure_password_123"
  }' > export_encrypted.json

# Decrypt
curl -X POST http://localhost:5000/api/v1/data/export/decrypt \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "encrypted_data": "...",
    "iv": "...",
    "salt": "...",
    "password": "secure_password_123"
  }' > decrypted.json
```

## Security Considerations

### Password Strength
- Use a strong, random password (minimum 12 characters recommended)
- Avoid dictionary words or personal information
- Example strong password: `K9@mP2!xL5$nQ8vY3`

### Transmission
- Always use HTTPS/TLS when transmitting encrypted payloads or passwords over the network
- Consider using short-lived sessions or rotating credentials frequently

### Storage
- Store encrypted exports in a secure location with appropriate access controls
- Keep the password separate from the encrypted file
- Consider using environment variables or secure key management systems for passwords

### Compatibility
- Encrypted exports from newer versions may not be decryptable by older versions
- The encryption version is included in the encrypted payload for forward compatibility

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Password required for encryption" | Encrypt flag is true but no password provided | Add "password" field to request |
| "Decryption failed" | Wrong password or corrupted data | Verify password matches encryption password |
| "Invalid base64 encoding in payload" | Corrupted base64 data in encrypted_data/iv/salt | Check that values are valid base64 |
| "Missing required field" | Missing encrypted_data, iv, or salt | Provide all three required fields |

## Testing

Run the test suite:

```bash
# Test encryption service
pytest tests/test_encryption_service.py -v

# Test API endpoints
pytest tests/test_encryption_api.py -v

# Test data export (including encryption)
pytest tests/test_data_api.py -v
```

## Performance

- Encryption/decryption performance depends on data size
- PBKDF2 key derivation takes ~100ms per operation (intentionally slow for security)
- Large exports (>100MB) may take several seconds to encrypt/decrypt
- Memory usage scales with export size

## Limitations

- **No Streaming**: Entire export is loaded into memory for encryption
- **No Incremental Encryption**: Must decrypt entire payload to read any portion
- **Single Password**: All encrypted data uses same password scheme
- **No Key Management**: Passwords are provided by users, not stored server-side

## Future Enhancements

Potential improvements for future versions:
- Streaming encryption for very large exports
- Asymmetric encryption option (RSA)
- Key management integration (AWS KMS, Azure Key Vault, etc.)
- Authenticated encryption (AES-GCM instead of CBC)
- Encrypted field-level export
- Multi-password shares (Shamir's Secret Sharing)

## Dependencies

- `cryptography>=45.0.7,<47` (mit `pyOpenSSL>=25.3`): Cryptographic primitives (AES, PBKDF2); abgestimmt mit pyhanko (`>=43.0.3`) und aktuellem PyOpenSSL (nicht 24.x mit `cryptography<45`)

Install with:
```bash
pip install cryptography
```

## References

- [OWASP: Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [Cryptography.io: AES](https://cryptography.io/en/latest/hazmat/primitives/ciphers/)
- [NIST: Special Publication 800-132](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf)
