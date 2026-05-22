# Security

## Credential Encryption

GeoTUI encrypts all stored GeoServer passwords at rest:

- **Algorithm**: Fernet (AES-128-CBC + HMAC-SHA256)
- **Key derivation**: PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP recommendation)
- **Salt**: Unique random salt per vault, stored alongside encrypted data
- **Master password**: Never stored — only held in memory during the session

The encryption implementation uses the `cryptography` library, a well-audited Python cryptographic toolkit.

## Vault Architecture

```
~/.config/geotui/config.json
├── salt (base64-encoded, unique per vault)
├── connections[]
│   ├── name (plaintext)
│   ├── url (plaintext)
│   ├── username (plaintext)
│   └── password (Fernet-encrypted)
└── verify_token (encrypted marker for password validation)
```

On launch, GeoTUI prompts for the master password and uses it to derive the decryption key. An incorrect password is detected via the verify token before any connection data is accessed.

## Network Security

- All connections use HTTPS by default
- TLS certificate verification is enabled (via `httpx` defaults)
- No data is transmitted to third parties — GeoTUI communicates only with the GeoServer instances you configure
- Connection details never leave the local machine except as authenticated REST API calls

## Input Validation

- GeoServer resource names are validated against `^[a-zA-Z0-9_.\-]+$` with a 256-character maximum
- Path traversal attacks are prevented through Textual's `DirectoryTree` widget
- All user inputs are validated before being sent to the GeoServer REST API

## File Permissions

The config file is created with user-only read/write permissions on Linux/macOS. On Windows, standard NTFS user permissions apply.

## Threat Model

| Threat | Mitigation |
|--------|------------|
| Credential theft from disk | AES encryption with PBKDF2-derived key |
| Brute-force master password | 600,000 PBKDF2 iterations |
| Man-in-the-middle attacks | HTTPS with certificate verification |
| Shoulder surfing | Password fields are masked in the UI |
| Memory dumps | Master password is not persisted; credentials are decrypted only when needed |

## Reporting Vulnerabilities

Please report security vulnerabilities to **security@kartoza.com**. Do not create public GitHub issues for security vulnerabilities.

We aim to acknowledge reports within 48 hours and provide a fix within 7 days for critical issues.

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)
