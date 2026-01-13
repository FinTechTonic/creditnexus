# Database SSL/TLS Setup Guide

This guide explains how to configure SSL/TLS encryption for database connections in CreditNexus.

## Overview

CreditNexus supports SSL/TLS encryption for PostgreSQL database connections to ensure secure data transmission. The implementation includes:

- **Automatic certificate generation** - Self-signed certificates for development
- **Manual certificate configuration** - Production certificates from your CA
- **Multiple SSL modes** - From basic encryption to full certificate verification
- **Health monitoring** - SSL connection status endpoint

## Quick Start

### Development (Automatic Setup)

For development, SSL can be automatically configured with zero setup:

```bash
# .env file
DATABASE_URL=postgresql://user:password@localhost:5432/creditnexus
DB_SSL_MODE=prefer
DB_SSL_AUTO_GENERATE=true
```

The application will automatically generate self-signed certificates on first run.

### Production (Manual Setup)

For production, use certificates from your Certificate Authority:

```bash
# .env file
DATABASE_URL=postgresql://user:password@db.example.com:5432/creditnexus
DB_SSL_MODE=verify-full
DB_SSL_REQUIRED=true
DB_SSL_CA_CERT=/etc/ssl/certs/postgresql-ca.crt
```

## SSL Modes

CreditNexus supports all PostgreSQL SSL modes:

| Mode | Description | Security | Use Case |
|------|-------------|----------|----------|
| `disable` | No SSL | ❌ None | Development only |
| `allow` | Try SSL, fallback | ⚠️ Low | Not recommended |
| `prefer` | Prefer SSL, fallback | ⚠️ Low | Migration |
| `require` | Require SSL, no cert verification | ⚠️ Medium | Internal networks |
| `verify-ca` | Require SSL, verify CA | ✅ High | Production |
| `verify-full` | Require SSL, verify CA and hostname | ✅ Highest | Production (recommended) |

**Recommendation:** Use `verify-full` for production environments.

## Configuration Options

### Basic SSL Configuration

```bash
# SSL Mode
DB_SSL_MODE=verify-full

# CA Certificate (required for verify-ca and verify-full)
DB_SSL_CA_CERT=/path/to/ca.crt

# Require SSL (fail if SSL unavailable)
DB_SSL_REQUIRED=true
```

### Automatic Certificate Generation

```bash
# Enable auto-generation
DB_SSL_AUTO_GENERATE=true

# Auto-generate CA certificate
DB_SSL_AUTO_GENERATE_CA=true

# Auto-generate client certificate (mutual TLS)
DB_SSL_AUTO_GENERATE_CLIENT=false

# Certificate directory
DB_SSL_AUTO_CERT_DIR=./ssl_certs/db

# Certificate validity (days)
DB_SSL_AUTO_CERT_VALIDITY_DAYS=365
```

### Mutual TLS (Client Certificates)

For enhanced security, configure mutual TLS:

```bash
# Client certificate and key
DB_SSL_CLIENT_CERT=/path/to/client.crt
DB_SSL_CLIENT_KEY=/path/to/client.key

# Or enable auto-generation
DB_SSL_AUTO_GENERATE_CLIENT=true
```

## Setup Steps

### Step 1: Obtain Certificates

#### Option A: Automatic Generation (Development)

1. Set `DB_SSL_AUTO_GENERATE=true` in your `.env` file
2. Start the application - certificates will be generated automatically
3. Certificates are stored in `./ssl_certs/db/` by default

#### Option B: Manual Setup (Production)

1. Obtain CA certificate from your database administrator
2. Store certificate in secure location (e.g., `/etc/ssl/certs/`)
3. Set `DB_SSL_CA_CERT` to certificate path
4. Ensure proper file permissions:
   ```bash
   chmod 644 /etc/ssl/certs/postgresql-ca.crt
   ```

### Step 2: Configure Environment Variables

Create or update your `.env` file:

```bash
# Database connection
DATABASE_URL=postgresql://user:password@host:5432/dbname

# SSL Configuration
DB_SSL_MODE=verify-full
DB_SSL_CA_CERT=/etc/ssl/certs/postgresql-ca.crt
DB_SSL_REQUIRED=true
```

### Step 3: Validate Configuration

The application validates SSL configuration at startup. If validation fails, the application will not start.

You can also validate manually:

```python
from app.core.config import settings

try:
    settings.validate_ssl_config()
    print("SSL configuration is valid")
except ValueError as e:
    print(f"SSL configuration error: {e}")
```

### Step 4: Verify SSL Connection

Check SSL status using the health endpoint:

```bash
curl http://localhost:8000/health/database/ssl
```

Response:
```json
{
  "ssl_enabled": true,
  "ssl_mode": "verify-full",
  "ssl_version": "TLSv1.3",
  "ssl_cipher": "TLS_AES_256_GCM_SHA384",
  "certificate_validation": "enabled",
  "status": "healthy"
}
```

## PostgreSQL Server Configuration

Ensure your PostgreSQL server has SSL enabled:

### postgresql.conf

```ini
# Enable SSL
ssl = on

# Certificate files
ssl_cert_file = '/var/lib/postgresql/server.crt'
ssl_key_file = '/var/lib/postgresql/server.key'
ssl_ca_file = '/var/lib/postgresql/ca.crt'

# SSL Protocol versions
ssl_min_protocol_version = 'TLSv1.2'

# Cipher suites
ssl_ciphers = 'HIGH:!aNULL:!MD5'
```

### pg_hba.conf

```ini
# Require SSL for remote connections
hostssl    all    all    0.0.0.0/0    scram-sha-256

# Local connections (optional SSL)
host       all    all    127.0.0.1/32    scram-sha-256
```

## Certificate Management

### Auto-Generated Certificates

Auto-generated certificates are stored in `./ssl_certs/db/` by default:

- `ca.crt` - CA certificate
- `server.crt` - Server certificate
- `server.key` - Server private key
- `client.crt` - Client certificate (if mutual TLS enabled)
- `client.key` - Client private key (if mutual TLS enabled)

**Security Note:** Auto-generated certificates are self-signed and suitable for development only. Do not use in production.

### Certificate Rotation

1. Obtain new certificates from your CA
2. Update `DB_SSL_CA_CERT` environment variable
3. Restart the application
4. Verify SSL connection using health endpoint
5. Remove old certificates after verification

### Certificate Expiration

The application checks certificate expiration. Certificates are valid for 365 days by default (configurable via `DB_SSL_AUTO_CERT_VALIDITY_DAYS`).

Monitor certificate expiration:

```bash
openssl x509 -in /path/to/ca.crt -noout -dates
```

## Environment-Specific Configuration

### Development

```bash
DB_SSL_MODE=prefer
DB_SSL_REQUIRED=false
DB_SSL_AUTO_GENERATE=true
```

### Staging

```bash
DB_SSL_MODE=verify-ca
DB_SSL_REQUIRED=true
DB_SSL_CA_CERT=/etc/ssl/certs/staging-ca.crt
```

### Production

```bash
DB_SSL_MODE=verify-full
DB_SSL_REQUIRED=true
DB_SSL_CA_CERT=/etc/ssl/certs/production-ca.crt
```

## Troubleshooting

### Common Issues

1. **SSL connection failed**
   - Verify PostgreSQL server has SSL enabled
   - Check certificate paths are correct
   - Ensure certificates have proper permissions

2. **Certificate verification failed**
   - Verify CA certificate matches server certificate
   - Check certificate expiration
   - Ensure certificate chain is complete

3. **Connection timeout**
   - Check network connectivity
   - Verify firewall allows SSL connections
   - Check PostgreSQL SSL port (usually 5432)

For detailed troubleshooting, see [SSL Troubleshooting Guide](./ssl-troubleshooting.md).

## Security Best Practices

1. **Always use SSL in production** - Set `DB_SSL_REQUIRED=true`
2. **Use verify-full mode** - Highest security level
3. **Validate certificates** - Never skip certificate validation
4. **Secure certificate storage** - Restrict file permissions (600 for keys, 644 for certs)
5. **Monitor SSL connections** - Use health endpoint to monitor status
6. **Rotate certificates** - Before expiration
7. **Use strong TLS versions** - TLS 1.2 minimum, TLS 1.3 preferred
8. **Disable weak ciphers** - Use strong cipher suites only

## Compliance

SSL/TLS encryption for database connections is required for:

- **GDPR** - Article 32 (Security of processing)
- **DORA** - Article 8 (ICT risk management)
- **PCI-DSS** - Requirement 4 (Encrypt transmission)

## Additional Resources

- [PostgreSQL SSL/TLS Documentation](https://www.postgresql.org/docs/current/ssl-tcp.html)
- [SSL Troubleshooting Guide](./ssl-troubleshooting.md)
- [Security Documentation](../SECURITY.md)
