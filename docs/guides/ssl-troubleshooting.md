# SSL/TLS Troubleshooting Guide

This guide helps you diagnose and resolve common SSL/TLS database connection issues in CreditNexus.

## Quick Diagnostics

### Check SSL Status

Use the health endpoint to check SSL connection status:

```bash
curl http://localhost:8000/health/database/ssl
```

Expected response for healthy SSL connection:
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

### Validate Configuration

Check SSL configuration programmatically:

```python
from app.core.config import settings

try:
    settings.validate_ssl_config()
    print("✓ SSL configuration is valid")
except ValueError as e:
    print(f"✗ SSL configuration error: {e}")
```

## Common Issues and Solutions

### Issue 1: SSL Connection Failed

**Error Message:**
```
SSL connection has been closed unexpectedly
```

**Possible Causes:**
1. PostgreSQL server doesn't have SSL enabled
2. SSL mode mismatch between client and server
3. Certificate files are missing or inaccessible
4. Network/firewall blocking SSL connections

**Solutions:**

1. **Verify PostgreSQL SSL is enabled:**
   ```sql
   -- Connect to PostgreSQL and check SSL status
   SHOW ssl;
   -- Should return: on
   ```

2. **Check PostgreSQL configuration:**
   ```bash
   # Check postgresql.conf
   grep ssl /etc/postgresql/*/main/postgresql.conf
   # Should show: ssl = on
   ```

3. **Verify certificate files exist:**
   ```bash
   ls -la $DB_SSL_CA_CERT
   # File should exist and be readable
   ```

4. **Check certificate permissions:**
   ```bash
   # Certificates should be readable
   chmod 644 /path/to/ca.crt
   # Private keys should be restricted
   chmod 600 /path/to/client.key
   ```

5. **Test with psql:**
   ```bash
   psql "postgresql://user:pass@host:5432/dbname?sslmode=require"
   ```

### Issue 2: Certificate Verification Failed

**Error Message:**
```
certificate verify failed
certificate has expired
certificate signed by unknown authority
```

**Possible Causes:**
1. CA certificate doesn't match server certificate
2. Certificate has expired
3. Certificate chain is incomplete
4. Hostname mismatch (for verify-full mode)

**Solutions:**

1. **Verify CA certificate path:**
   ```bash
   # Check certificate exists
   test -f $DB_SSL_CA_CERT && echo "Certificate exists" || echo "Certificate missing"
   ```

2. **Check certificate expiration:**
   ```bash
   openssl x509 -in $DB_SSL_CA_CERT -noout -dates
   # Check both "notBefore" and "notAfter" dates
   ```

3. **Verify certificate matches server:**
   ```bash
   # Get server certificate
   openssl s_client -connect db.example.com:5432 -starttls postgres
   
   # Compare with CA certificate
   openssl verify -CAfile $DB_SSL_CA_CERT server.crt
   ```

4. **Check certificate chain:**
   ```bash
   # Verify certificate chain
   openssl verify -CAfile ca.crt -untrusted intermediate.crt server.crt
   ```

5. **Try verify-ca mode (for testing):**
   ```bash
   # Temporarily use verify-ca instead of verify-full
   DB_SSL_MODE=verify-ca
   ```

6. **Check hostname in certificate:**
   ```bash
   openssl x509 -in server.crt -text -noout | grep -A 2 "Subject Alternative Name"
   # Verify hostname matches database server hostname
   ```

### Issue 3: Connection Timeout with SSL

**Error Message:**
```
connection timeout
could not connect to server
```

**Possible Causes:**
1. Network connectivity issues
2. Firewall blocking SSL connections
3. PostgreSQL not listening on SSL port
4. SSL handshake failing

**Solutions:**

1. **Test network connectivity:**
   ```bash
   # Test basic connectivity
   telnet db.example.com 5432
   # Or use nc
   nc -zv db.example.com 5432
   ```

2. **Check firewall rules:**
   ```bash
   # Allow PostgreSQL SSL port (usually 5432)
   sudo ufw allow 5432/tcp
   # Or check iptables
   sudo iptables -L -n | grep 5432
   ```

3. **Verify PostgreSQL is listening:**
   ```bash
   # Check if PostgreSQL is listening on SSL port
   sudo netstat -tlnp | grep 5432
   # Or use ss
   sudo ss -tlnp | grep 5432
   ```

4. **Test SSL handshake:**
   ```bash
   # Test SSL connection
   openssl s_client -connect db.example.com:5432 -starttls postgres
   ```

5. **Check PostgreSQL logs:**
   ```bash
   # Check PostgreSQL error log
   sudo tail -f /var/log/postgresql/postgresql-*.log
   ```

### Issue 4: SSL Required but Not Available

**Error Message:**
```
SSL is required but connection is not using SSL
DB_SSL_REQUIRED=true but SSL connection failed
```

**Possible Causes:**
1. PostgreSQL server doesn't support SSL
2. SSL mode is set to disable
3. Connection falling back to non-SSL

**Solutions:**

1. **Check SSL requirement setting:**
   ```bash
   # Verify environment variable
   echo $DB_SSL_REQUIRED
   # Should be: true
   ```

2. **Verify SSL mode:**
   ```bash
   # Check SSL mode is not disable
   echo $DB_SSL_MODE
   # Should be: require, verify-ca, or verify-full
   ```

3. **Check PostgreSQL SSL support:**
   ```sql
   -- In PostgreSQL
   SHOW ssl;
   -- Should return: on
   ```

4. **Temporarily allow fallback (for debugging):**
   ```bash
   # Change to prefer mode (allows fallback)
   DB_SSL_MODE=prefer
   DB_SSL_REQUIRED=false
   ```

### Issue 5: Auto-Generation Failed

**Error Message:**
```
Failed to auto-generate database SSL certificates
Permission denied
```

**Possible Causes:**
1. Certificate directory doesn't exist
2. Insufficient permissions
3. Disk space full
4. Certificate generation library missing

**Solutions:**

1. **Check certificate directory:**
   ```bash
   # Verify directory exists
   ls -la $DB_SSL_AUTO_CERT_DIR
   # Create if missing
   mkdir -p $DB_SSL_AUTO_CERT_DIR
   ```

2. **Fix permissions:**
   ```bash
   # Set proper permissions
   chmod 700 $DB_SSL_AUTO_CERT_DIR
   ```

3. **Check disk space:**
   ```bash
   df -h $DB_SSL_AUTO_CERT_DIR
   ```

4. **Verify cryptography library:**
   ```bash
   python -c "from cryptography import x509; print('OK')"
   ```

5. **Manually generate certificates:**
   ```bash
   # Use OpenSSL to generate certificates manually
   openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes
   ```

### Issue 6: Client Certificate Issues (Mutual TLS)

**Error Message:**
```
client certificate required
certificate and private key do not match
```

**Possible Causes:**
1. Client certificate not provided
2. Certificate and key mismatch
3. Certificate not signed by CA
4. Certificate expired

**Solutions:**

1. **Verify both certificate and key are provided:**
   ```bash
   # Both must be set
   test -f $DB_SSL_CLIENT_CERT && echo "Cert exists" || echo "Cert missing"
   test -f $DB_SSL_CLIENT_KEY && echo "Key exists" || echo "Key missing"
   ```

2. **Check certificate and key match:**
   ```bash
   # Verify certificate and key match
   openssl x509 -noout -modulus -in client.crt | openssl md5
   openssl rsa -noout -modulus -in client.key | openssl md5
   # Both should produce the same hash
   ```

3. **Verify certificate is signed by CA:**
   ```bash
   openssl verify -CAfile ca.crt client.crt
   ```

4. **Check certificate expiration:**
   ```bash
   openssl x509 -in client.crt -noout -dates
   ```

## Debugging Commands

### PostgreSQL SSL Status

```sql
-- Check SSL status
SHOW ssl;
SHOW ssl_version;
SHOW ssl_cipher;

-- Check current connection SSL status
SELECT ssl_is_used();
```

### Certificate Inspection

```bash
# View certificate details
openssl x509 -in ca.crt -text -noout

# Check certificate expiration
openssl x509 -in ca.crt -noout -dates

# Verify certificate chain
openssl verify -CAfile ca.crt server.crt

# Check certificate subject
openssl x509 -in server.crt -noout -subject

# Check certificate issuer
openssl x509 -in server.crt -noout -issuer
```

### Connection Testing

```bash
# Test SSL connection with psql
psql "postgresql://user:pass@host:5432/dbname?sslmode=verify-full&sslrootcert=ca.crt"

# Test with OpenSSL
openssl s_client -connect db.example.com:5432 -starttls postgres -CAfile ca.crt

# Test connection with Python
python -c "
from app.db.ssl_config import get_ssl_connection_string
print(get_ssl_connection_string())
"
```

### Configuration Validation

```bash
# Check environment variables
env | grep DB_SSL

# Validate configuration
python -c "
from app.core.config import settings
settings.validate_ssl_config()
print('Configuration valid')
"
```

## Logging and Monitoring

### Enable Debug Logging

```python
# In your application code
import logging
logging.getLogger('app.db.ssl_config').setLevel(logging.DEBUG)
```

### Check Application Logs

```bash
# View application logs
tail -f logs/application.log | grep -i ssl

# Check for SSL errors
grep -i "ssl\|tls" logs/application.log
```

### Monitor SSL Health

```bash
# Regular health checks
watch -n 5 'curl -s http://localhost:8000/health/database/ssl | jq'
```

## Performance Issues

### SSL Handshake Overhead

SSL adds minimal overhead (~1-2ms per connection). If experiencing performance issues:

1. **Use connection pooling:**
   - SSL connections are reused in the pool
   - Reduces handshake overhead

2. **Check connection pool settings:**
   ```python
   # In app/db/__init__.py
   engine = create_engine(
       url,
       pool_size=10,  # Increase pool size
       max_overflow=20
   )
   ```

3. **Monitor connection times:**
   ```bash
   # Time SSL connection
   time psql "postgresql://user:pass@host:5432/dbname?sslmode=require"
   ```

## Getting Help

If you're still experiencing issues:

1. **Collect diagnostic information:**
   ```bash
   # SSL configuration
   env | grep DB_SSL > ssl_config.txt
   
   # Certificate info
   openssl x509 -in $DB_SSL_CA_CERT -text -noout > cert_info.txt
   
   # Health check
   curl http://localhost:8000/health/database/ssl > health_check.json
   ```

2. **Check application logs:**
   - Look for SSL-related error messages
   - Check stack traces for connection failures

3. **Review documentation:**
   - [Database SSL Setup Guide](./database-ssl-setup.md)
   - [Security Documentation](../SECURITY.md)

4. **Contact support:**
   - Include diagnostic information
   - Provide error messages and logs
   - Describe steps to reproduce

## Prevention

To avoid SSL issues:

1. **Validate configuration before deployment**
2. **Test SSL connections in staging first**
3. **Monitor certificate expiration dates**
4. **Use automated certificate rotation**
5. **Regular health checks**
6. **Keep certificates secure and backed up**

## Additional Resources

- [PostgreSQL SSL Documentation](https://www.postgresql.org/docs/current/ssl-tcp.html)
- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [Database SSL Setup Guide](./database-ssl-setup.md)
- [Security Best Practices](../SECURITY.md)
