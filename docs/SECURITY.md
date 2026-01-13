# Security Documentation

**Version:** 1.0  
**Last Updated:** 2024-12-XX

---

## Table of Contents

1. [Security Architecture](#1-security-architecture)
2. [Authentication & Authorization](#2-authentication--authorization)
3. [Data Protection](#3-data-protection)
4. [Network Security](#4-network-security)
5. [Compliance](#5-compliance)
6. [Security Controls](#6-security-controls)
7. [Incident Response](#7-incident-response)
8. [Vulnerability Management](#8-vulnerability-management)

---

## 1. Security Architecture

### 1.1 Defense in Depth

CreditNexus implements multiple layers of security:

1. **Network Layer:**
   - HTTPS/TLS encryption
   - Firewall rules
   - DDoS protection
   - Rate limiting

2. **Application Layer:**
   - Authentication & authorization
   - Input validation
   - Output encoding
   - Security headers

3. **Data Layer:**
   - Database encryption
   - Access controls
   - Audit logging
   - Backup encryption

4. **Infrastructure Layer:**
   - Secure configuration
   - Patch management
   - Monitoring & alerting
   - Incident response

### 1.2 Security Principles

- **Least Privilege:** Users have minimum necessary permissions
- **Defense in Depth:** Multiple security layers
- **Fail Secure:** System fails in secure state
- **Security by Design:** Security built into architecture
- **Privacy by Design:** Privacy considerations from start

---

## 2. Authentication & Authorization

### 2.1 Authentication

**Methods:**
- JWT-based authentication
- Password-based login
- Wallet-based authentication (MetaMask)
- OAuth (if configured)

**Password Requirements:**
- Minimum 12 characters
- Uppercase, lowercase, number, special character
- Bcrypt hashing (with SHA-256 pre-hashing for long passwords)

**Account Protection:**
- Account lockout after 5 failed attempts (30 minutes)
- Password change required on first login
- Session timeout (30 minutes access token, 7 days refresh token)

### 2.2 Authorization

**Role-Based Access Control (RBAC):**
- **Admin:** Full system access
- **Auditor:** Read-only access to all data
- **Banker:** Write access to deals and documents
- **Law Officer:** Write/edit legal documents
- **Accountant:** Write/edit financial data
- **Applicant:** Apply and track applications
- **Analyst/Reviewer:** Analysis and review permissions

**Permission Model:**
- Role-based permissions (default)
- User-specific permissions (override)
- Resource-level access control

---

## 3. Data Protection

### 3.1 Data Classification

#### Highly Sensitive
- Password hashes (encrypted with bcrypt)
- JWT secrets (environment variables)
- API keys (SecretStr in config)
- Financial data (CDM events)

#### Sensitive
- User email addresses
- Profile data (phone, address, company)
- Credit agreement PDFs
- Policy decisions

#### Internal
- Document metadata
- Workflow states
- Template data

### 3.2 Encryption

#### At Rest
- **Database:** Relies on database server encryption (PostgreSQL)
- **File Storage:** Files stored in `storage/` directory (encryption recommended)
- **Backups:** Backup encryption policy (to be implemented)

#### In Transit
- **API:** HTTPS/TLS required
- **Database:** SSL/TLS **REQUIRED** in production (enforced via `DB_SSL_REQUIRED=true`)
  - Supports all PostgreSQL SSL modes: `prefer`, `require`, `verify-ca`, `verify-full`
  - Automatic certificate generation for development
  - Manual certificate configuration for production
  - Health monitoring via `/health/database/ssl` endpoint
  - See [Database SSL Setup Guide](../guides/database-ssl-setup.md) for configuration
- **File Uploads:** HTTPS via FastAPI

### 3.3 Data Retention

**Current Policy:**
- **Audit Logs:** 7 years (regulatory requirement)
- **User Data:** Until deletion requested (GDPR)
- **Documents:** Until deletion requested
- **Financial Data:** Per regulatory requirements

**Future Enhancements:**
- Automated data retention service
- Configurable retention policies
- Automated archival

---

## 4. Network Security

### 4.1 CORS Configuration

**Production:**
- Specific allowed origins (no wildcards)
- Restricted HTTP methods
- Restricted headers
- Credentials allowed for trusted origins

**Development:**
- Localhost origins allowed
- More permissive for development

### 4.2 Security Headers

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (production)
- `Content-Security-Policy`
- `Referrer-Policy`
- `Permissions-Policy`

### 4.3 Rate Limiting

- **Default:** 60 requests per minute per IP
- **Login Endpoint:** Stricter limits (account lockout)
- **File Upload:** Size limits (20MB)
- **Configurable:** Via `settings.RATE_LIMIT_PER_MINUTE`

### 4.4 Trusted Hosts

- **Production:** Specific domains only
- **Development:** Localhost and all hosts
- **Middleware:** TrustedHostMiddleware

### 4.5 Database SSL/TLS Encryption

**Implementation Status:** ✅ **COMPLETE**

CreditNexus enforces SSL/TLS encryption for all PostgreSQL database connections in production.

**Configuration:**
- **SSL Modes:** `prefer`, `require`, `verify-ca`, `verify-full`
- **Production Mode:** `verify-full` (recommended)
- **Certificate Validation:** CA certificate verification enabled
- **Auto-Generation:** Self-signed certificates for development
- **Health Monitoring:** Real-time SSL status via `/health/database/ssl`

**Environment Variables:**
```bash
DB_SSL_MODE=verify-full          # SSL mode
DB_SSL_CA_CERT=/path/to/ca.crt   # CA certificate path
DB_SSL_REQUIRED=true              # Require SSL (fail if unavailable)
DB_SSL_AUTO_GENERATE=true         # Auto-generate certs (development)
```

**Security Features:**
- ✅ Automatic certificate generation for development
- ✅ Manual certificate configuration for production
- ✅ Certificate validation (CA and hostname)
- ✅ Mutual TLS support (client certificates)
- ✅ Connection health monitoring
- ✅ Configuration validation at startup

**Compliance:**
- ✅ **GDPR:** Article 32 - Encrypted data in transit
- ✅ **DORA:** Article 8 - Secure communication channels
- ✅ **PCI-DSS:** Requirement 4 - Encrypted transmission

**Documentation:**
- [Database SSL Setup Guide](../guides/database-ssl-setup.md)
- [SSL Troubleshooting Guide](../guides/ssl-troubleshooting.md)

---

## 5. Compliance

### 5.1 GDPR Compliance

**Implemented:**
- ✅ Right to access (data export endpoint)
- ✅ Right to deletion (data erasure endpoint)
- ✅ Audit logging
- ✅ Data minimization principles

**In Progress:**
- ⚠️ Data retention policies (automated)
- ⚠️ Encryption at rest for PII
- ⚠️ Breach notification automation

**Endpoints:**
- `POST /api/gdpr/export` - Export user data
- `POST /api/gdpr/delete` - Delete user data
- `GET /api/gdpr/status` - Compliance status

### 5.2 DORA Compliance

**Implemented:**
- ✅ Security testing in CI/CD
- ✅ Vulnerability management process
- ✅ Incident response plan

**In Progress:**
- ⚠️ Business continuity plan
- ⚠️ Third-party risk assessment
- ⚠️ Operational resilience documentation

### 5.3 FINOS CDM Compliance

**Implemented:**
- ✅ CDM event generation
- ✅ CDM-compliant data models
- ✅ Policy evaluation events
- ✅ Trade execution events

---

## 6. Security Controls

### 6.1 Input Validation

- **Pydantic Models:** All API inputs validated
- **File Uploads:** PDF magic bytes validation, structure validation
- **SQL Injection:** Prevented via SQLAlchemy ORM
- **XSS:** Output encoding, CSP headers

### 6.2 Secrets Management

- **Environment Variables:** All secrets in environment
- **Pydantic SecretStr:** API keys stored as SecretStr
- **No Hardcoding:** Secrets never in code
- **Secrets Scanning:** detect-secrets in pre-commit and CI/CD

### 6.3 Security Scanning

**Automated Scans:**
- **SAST:** Bandit, Semgrep (on every push)
- **SCA:** pip-audit, Safety, npm audit (on every push)
- **Secrets:** detect-secrets (pre-commit and CI/CD)
- **DAST:** OWASP ZAP (weekly scheduled)

**Frequency:**
- **On Push:** All SAST and SCA scans
- **Weekly:** DAST scans
- **On PR:** Full security scan suite

### 6.4 Dependency Management

- **Dependabot:** Automated dependency updates
- **Version Pinning:** uv.lock and package-lock.json
- **Vulnerability Scanning:** Automated in CI/CD
- **Update Policy:** Critical/High within 30 days

---

## 7. Incident Response

See [Incident Response Plan](./INCIDENT_RESPONSE.md) for detailed procedures.

**Key Points:**
- 24/7 incident response capability
- Classified severity levels (P0-P3)
- Defined response timelines
- Communication procedures
- Post-incident review process

---

## 8. Vulnerability Management

See [Vulnerability Management Process](./VULNERABILITY_MANAGEMENT.md) for detailed procedures.

**Key Points:**
- Automated vulnerability detection
- Severity classification (Critical, High, Medium, Low)
- Remediation timelines
- Responsible disclosure process
- Continuous improvement

---

## 9. Security Best Practices

### For Developers

1. **Never commit secrets:**
   - Use environment variables
   - Use `.env` files (not committed)
   - Use secret management services in production

2. **Validate all input:**
   - Use Pydantic models
   - Sanitize user-provided data
   - Validate file uploads

3. **Follow secure coding practices:**
   - Use parameterized queries (SQLAlchemy ORM)
   - Escape output
   - Implement proper error handling
   - Use security headers

4. **Keep dependencies updated:**
   - Review Dependabot PRs promptly
   - Update dependencies regularly
   - Test updates before merging

5. **Review security scan results:**
   - Check GitHub Security tab regularly
   - Fix high/critical issues immediately
   - Address medium issues within 30 days

### For Operations

1. **Monitor security:**
   - Review security scan results
   - Monitor for anomalies
   - Respond to alerts promptly

2. **Maintain security:**
   - Keep systems patched
   - Update security configurations
   - Review access controls regularly

3. **Document security:**
   - Document security changes
   - Maintain security logs
   - Update security documentation

---

## 10. Security Contacts

### Reporting Vulnerabilities

- **Email:** security@creditnexus.com
- **Response Time:** Within 24 hours
- **Process:** See [Vulnerability Management](./VULNERABILITY_MANAGEMENT.md)

### Security Team

- **Security Lead:** [Email]
- **CTO:** [Email]
- **DevOps:** [Email]

---

## 11. Security Resources

### Documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### Tools
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Semgrep Documentation](https://semgrep.dev/docs/)
- [OWASP ZAP Documentation](https://www.zaproxy.org/docs/)

### Compliance
- [GDPR Compliance Guide](https://gdpr.eu/)
- [DORA Regulation](https://www.eba.europa.eu/regulation-and-policy/operational-risk/digital-operational-resilience-act-dora)

---

**Document Owner:** Security Team  
**Review Date:** Quarterly  
**Next Review:** [Date]
