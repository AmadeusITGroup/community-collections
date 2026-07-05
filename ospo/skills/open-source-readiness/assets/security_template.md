# Security Policy

## Supported Versions

<!-- List which versions receive security updates -->

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | ✅ Yes             |
| 1.x.x   | ⚠️ Critical only   |
| < 1.0   | ❌ No              |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**⚠️ Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **GitHub Security Advisories** (Preferred)
   - Go to the [Security tab](https://github.com/[org]/[project]/security)
   - Click "Report a vulnerability"
   - Fill out the private security advisory form

2. **Email**
   - Send details to: [security@example.com]
   - Use our PGP key for sensitive information: [link to key or fingerprint]

### What to Include

Please include as much of the following information as possible:

- **Type of vulnerability** (e.g., SQL injection, XSS, authentication bypass)
- **Affected component** (file paths, functions, endpoints)
- **Steps to reproduce** the vulnerability
- **Proof of concept** (code, screenshots, or video)
- **Impact assessment** of the vulnerability
- **Suggested fix** (if you have one)

### What to Expect

| Timeline | Action |
|----------|--------|
| **24 hours** | Acknowledgment of your report |
| **72 hours** | Initial assessment and severity determination |
| **7 days** | Detailed response with remediation plan |
| **90 days** | Target fix for most vulnerabilities |

### Safe Harbor

We consider security research conducted in accordance with this policy to be:
- Authorized concerning any applicable anti-hacking laws
- Exempt from restrictions in our Terms of Service that would interfere with security research

We will not pursue legal action against researchers who:
- Make a good faith effort to comply with this policy
- Avoid privacy violations, data destruction, or service disruption
- Report findings promptly and work with us on remediation

## Security Practices

### For Users

- **Keep updated**: Always use the latest supported version
- **Review dependencies**: Regularly update project dependencies
- **Secure configuration**: Follow our [Security Best Practices Guide](docs/security-best-practices.md)
- **Access control**: Use principle of least privilege

### For Contributors

- **No secrets in code**: Never commit credentials, API keys, or tokens
- **Dependency review**: Check for vulnerabilities before adding dependencies
- **Secure coding**: Follow OWASP guidelines for secure development
- **Code review**: All changes require security-conscious review

## Dependency Security

We use automated tools to monitor dependencies:

- **Dependabot**: Automated security updates for dependencies
- **SAST**: Static Application Security Testing in CI/CD
- **Secret scanning**: Detection of accidentally committed secrets

## Security Updates

Security updates are announced via:

- **GitHub Security Advisories**: [Security tab](https://github.com/[org]/[project]/security/advisories)
- **Release notes**: [Releases page](https://github.com/[org]/[project]/releases)
- **Mailing list**: [Subscribe to security announcements](mailto:security-announce@example.com?subject=subscribe)

## Acknowledgments

We thank the following researchers for responsibly disclosing vulnerabilities:

<!-- Add security researchers who have helped -->
| Researcher | Date | Issue |
|------------|------|-------|
| [Name] | YYYY-MM | Brief description |

---

Thank you for helping keep [Project Name] and our users safe!
