# Security Policy — MoodMarket

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x.x (main) | ✅ Active security updates |
| Older | ❌ End of life |

---

## 🔒 Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

If you discover a security vulnerability in MoodMarket, please report it responsibly:

### Preferred Channel

1. **GitHub Private Vulnerability Reporting** (preferred):
   - Navigate to the [Security tab](https://github.com/Yashaswini-V21/Mood_Market/security) on GitHub
   - Click "Report a vulnerability"
   - Fill in the advisory form

### What to Include

Please provide:

- **Description**: What is the vulnerability?
- **Impact**: What can an attacker accomplish?
- **Reproduction steps**: Minimal steps to reproduce
- **Environment**: Python version, OS, dependencies
- **Proof of concept** (optional but helpful): Code or screenshot
- **Suggested fix** (optional): If you have one in mind

---

## ⏱ Response Timeline

| Stage | Timeline |
|-------|----------|
| Initial acknowledgement | Within **48 hours** |
| Vulnerability confirmed | Within **7 days** |
| Fix deployed | Within **30 days** (critical: ASAP) |
| Public disclosure | After fix + 90-day coordinated disclosure |

---

## 🛡️ Security Architecture

MoodMarket implements multiple security layers:

| Layer | Implementation |
|-------|----------------|
| **Authentication** | JWT HS256 with `iss`/`aud` claims, env-var secrets, refresh tokens |
| **Rate Limiting** | Redis sliding window — 100 req/min per IP |
| **Input Validation** | Ticker regex `^[A-Za-z]{1,5}$` + Pydantic v2 strict mode |
| **CORS** | Restricted to frontend origin in production |
| **HTTPS** | Enforced in production — fail-fast if disabled |
| **Secrets** | Environment variables only — fail-fast if defaults used |
| **Request Tracing** | UUID-based `X-Request-ID` on every response |
| **Container** | Non-root user in Dockerfile, minimal base image |
| **Dependencies** | Weekly Dependabot updates, Trivy scanning, pip-audit |

---

## 🚫 Out of Scope

The following are **not** in scope for bug bounties/reports:

- Vulnerabilities in mock/demo data (it's intentionally fake)
- Rate limiting bypass in development mode
- Social engineering attacks
- Physical access attacks
- Issues in third-party services (Redis, PostgreSQL, GitHub)
- Self-XSS (requires attacker to control their own browser)

---

## 🙏 Acknowledgements

We sincerely thank security researchers who responsibly disclose vulnerabilities. Credited researchers will be acknowledged in our release notes (unless they prefer anonymity).

---

*MoodMarket Security Team · Yashaswini V*
