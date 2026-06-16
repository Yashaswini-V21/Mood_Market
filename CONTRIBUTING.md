# Contributing to MoodMarket

Thank you for your interest in contributing to **MoodMarket** — the AI Financial Intelligence Platform! 🎉

We welcome contributions of all kinds: bug fixes, new features, documentation improvements, and tests.

---

## 🚀 Getting Started

### Prerequisites

```
Python 3.10+  |  Node.js 18+  |  Redis 7+  |  Docker (optional)
```

### 1. Fork & Clone

```bash
git clone https://github.com/Yashaswini-V21/Mood_Market.git
cd Mood_Market
```

### 2. Install Dependencies

```bash
# Backend
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-ci.txt  # Dev tools

# Frontend
cd frontend && npm install && cd ..
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Redis URI, DB URL, and API keys
```

### 4. Run Tests

```bash
# Backend
pytest --no-cov -q

# Frontend
cd frontend && npm run lint && npm run build
```

---

## 📋 Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

<optional body>

<optional footer>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Code restructure, no new feature |
| `test` | Adding or updating tests |
| `chore` | Build, CI, dependencies |
| `perf` | Performance improvement |

### Examples

```
feat(agents): add GPT-4o news summarizer agent
fix(anomaly): correct Z-Score normalization for multi-variate case
test(sentiment): add FinBERT confidence calibration tests
docs(api): add WebSocket authentication examples
chore(deps): bump fastapi from 0.109 to 0.112
```

---

## 🌿 Branching Strategy

```
main          → Production-ready code (protected)
develop       → Integration branch
feature/<name>  → New features
fix/<name>      → Bug fixes
docs/<name>     → Documentation
```

### Workflow

```bash
git checkout develop
git pull origin develop
git checkout -b feature/my-feature
# ... make changes ...
git commit -m "feat(scope): description"
git push origin feature/my-feature
# Open PR to develop
```

---

## 🧪 Testing Requirements

All PRs must maintain:

- **Backend**: ≥ 90% code coverage (`pytest --cov`)
- **Frontend**: Zero ESLint errors (`npm run lint`)
- **TypeScript**: Strict build pass (`npm run build`)
- **Flake8**: Zero syntax errors (hard fail)

```bash
# Run full test suite before opening PR
pytest --cov=. --cov-fail-under=90 -q
cd frontend && npm run lint && npm run build
```

---

## 📂 Project Structure

See `README.md` for the full structure. Key areas:

| Area | Path | Notes |
|------|------|-------|
| ML Models | `model.py`, `inference.py` | Informer Transformer |
| Agents | `agents/` | 5-agent async trading desk |
| Anomaly | `detectors/` | 7-method ensemble |
| API Routes | `routes/` | FastAPI endpoints |
| Frontend | `frontend/src/` | React 19 + TypeScript |
| Tests | `tests/` | 200+ tests, 22 files |

---

## 🔒 Security

Please **do not** open public issues for security vulnerabilities. See [SECURITY.md](SECURITY.md) for our responsible disclosure process.

---

## 📜 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- No harassment or discrimination of any kind

---

## 🏆 Recognition

Contributors are acknowledged in release notes and the README. Top contributors may be featured as collaborators.

---

*Made with 💜 — MoodMarket Team*
