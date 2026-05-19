# Security

## Security Posture

GeoTUI takes security extremely seriously. The application is designed to protect user data and infrastructure at all times.

## Credential Management

- Credentials are stored using the system keyring (via the `keyring` library)
- No passwords are stored in plain text
- No credentials are logged or written to disk

## Network Security

- All connections use HTTPS by default
- Certificate verification is enabled
- No data is transmitted to third parties

## Input Validation

- All user inputs are validated and sanitized
- Path traversal attacks are prevented
- Command injection is mitigated

## Reporting Vulnerabilities

Please report security vulnerabilities to security@kartoza.com. Do not create public GitHub issues for security vulnerabilities.

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)
