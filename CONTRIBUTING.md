# Contributing to ORCHESTRATORS_V2

Thank you for your interest! This project values **quality over velocity** and **discipline over surface area**.

## Before You Contribute

### 1. Read the Philosophy
**REQUIRED**: Read [Operational Philosophy](docs/OPERATIONAL_PHILOSOPHY.md) to understand the "why" behind design decisions.

**Core principles:**
- Bounded Memory (no unbounded growth)
- Receipts Over Assertions (evidence required)
- Rehearsal Before Release (dry-run mode first)
- Defaults Off (explicit enablement)
- Automation Over Heroics (timers > humans)

### 2. Check the Boundary
All contributions must pass boundary verification:
```bash
./scripts/verify_public_boundary.sh
```
This ensures no secrets, runtime state, or private patterns leak into the public repo.

### 3. Public Boundary Contract (Non-Negotiable)
**Boundary check must pass.** Do not commit runtime artifacts or identity strings.

**Rules:**
- **No runtime artifacts**: never commit `instance/`, `logs/`, `reports/`, `*.db`, `*.sqlite`, or test output.
- **No absolute paths**: use `$PROJECT_ROOT` or relative paths in docs/scripts.
- **No identity strings**: replace real names/handles with placeholders.

**CI gates** (enforced on every PR/push):
- `./scripts/verify_public_boundary.sh`
- `pytest -q`

### 4. Repository Layout (Current vs. Recommended)
Keep reviews factual: separate shipped layout from suggested extensions.

**Current shipped structure:**
- `src/server.py` - Flask API stub (routes + memory capture decision)
- `src/memory.py` - Memory capture logic + taxonomy
- `src/orchestrator_memory.py` - Memory decision evaluation
- `src/tracer.py` - Trace store + steps
- `src/tool_registry.py` - Minimal tool registry
- `src/router.py` - Rule-based router
- `src/llm_provider.py` - Optional local LLM provider
- `examples/` - Teaching examples
- `tests/` - Test suite (boundary + memory taxonomy + server)

**Recommended extension structure (optional, not shipped by default):**
- `src/routers/` - Model selection logic
- `src/tools/` - Custom tool implementations
- `src/memory/` - Additional memory backends

## Contribution Types

### 🐛 Bug Reports
Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Include:
- Reproduction steps
- Boundary verification results
- Philosophy alignment check (does bug violate a principle?)

### ✨ Feature Requests
Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md). **MUST answer 5 philosophy questions:**
1. Is it bounded?
2. Is it receipted?
3. Is it rehearsed?
4. Is it default-off?
5. Is it automated?

**High bar**: Features that violate principles will be rejected, even if technically sound.

### 🔧 Pull Requests
1. **Fork and branch**: `feature/your-feature` or `fix/your-fix`
2. **Test locally**: Run tests and boundary checks
3. **Verify philosophy alignment**: Does your code follow the 5 principles?
4. **Keep it minimal**: Resist feature creep. Smaller is better.
5. **Add tests**: All new code should have tests
6. **Document changes**: Update relevant docs

**PR Checklist:**
- [ ] All tests pass (`pytest`)
- [ ] Boundary verification passes (`./scripts/verify_public_boundary.sh`)
- [ ] Philosophy principles followed (see below)
- [ ] No new secrets/tokens introduced
- [ ] No unbounded growth (memory, disk, network)
- [ ] Feature is default-off (if applicable)
- [ ] Documentation updated

## Development Workflow

### Setup
```bash
# Clone
git clone https://github.com/example-org/orchestrators-v2.git
cd orchestrators-v2

# Create virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install deps
pip install -r requirements.txt

# Copy env
cp .env.example .env
```

### Running Tests
```bash
# All tests
pytest

# Specific test
pytest tests/test_server.py -v

# With coverage
pytest --cov=src --cov-report=term-missing
```

### Boundary Verification
```bash
# Before committing
./scripts/verify_public_boundary.sh

# Expected output:
# ✅ PUBLIC BOUNDARY SAFE (5/5 checks passing)
```

### Try the Example
```bash
# Interactive mode
python examples/toy_orchestrator.py

# Automated demo
python examples/toy_orchestrator.py --auto
```

## Code Standards

### Python Style
- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Keep functions small (<50 lines)

### Philosophy-Aligned Code

**✅ Good Example** (bounded, receipted, default-off):
```python
def store_memory(content: str, ttl_days: int = 30, enabled: bool = False) -> Dict[str, Any]:
    """Store memory with explicit TTL and opt-in flag"""
    if not enabled:
        return {"status": "skipped", "reason": "memory disabled by default"}
    
    # Enforce bound
    if len(content) > 10000:
        return {"status": "error", "reason": "content exceeds 10KB limit"}
    
    # Receipt
    receipt = {
        "timestamp": datetime.utcnow().isoformat(),
        "content_hash": hashlib.sha256(content.encode()).hexdigest(),
        "ttl_seconds": ttl_days * 86400,
        "expires_at": (datetime.utcnow() + timedelta(days=ttl_days)).isoformat()
    }
    
    # Store with TTL
    db.execute("INSERT INTO memories (content, expires_at) VALUES (?, ?)", 
               (content, receipt["expires_at"]))
    
    return {"status": "success", "receipt": receipt}
```

**❌ Bad Example** (unbounded, no receipts, auto-on):
```python
def save_everything(data):
    """Save data forever"""
    # No size limit
    # No expiration
    # No receipt
    # Always enabled
    db.execute("INSERT INTO stuff (data) VALUES (?)", (data,))
```

## Extension Points

### Safe Areas to Extend
- **Tools** (`src/tools/`, optional): Add new tools with bounded execution
- **Routers** (`src/routers/`, optional): Add new routing logic
- **Memory** (`src/memory/`, optional): Add new memory backends (with TTL!)
- **Tests** (`tests/`): More tests = better
- **Docs** (`docs/`): Clarity improvements always welcome

### Restricted Areas
- **Boundary scripts** (`scripts/verify_public_boundary.sh`): Changes require justification
- **Core principles** (`docs/OPERATIONAL_PHILOSOPHY.md`): Philosophy is stable
- **GitHub workflows** (`.github/workflows/`): CI changes need careful review

## What We DON'T Want

**Rejected contributions:**
- Unbounded memory/storage (no TTL)
- Silent auto-activation (defaults on)
- Missing evidence/receipts (no logs)
- Cloud-first features (local-first only)
- "Move fast and break things" code
- Feature creep (scope bloat)

**Read the philosophy doc** to understand why.

## Community Standards

### Behavior
- Be respectful and constructive
- Assume good intent
- Prioritize clarity over cleverness
- Slow and steady > fast and broken

### Communication
- Issues: Describe problem, not solution (we'll collaborate on approach)
- PRs: Small, focused changes beat large rewrites
- Reviews: Feedback is about code, not people
- Philosophy: If you disagree with a principle, open a discussion issue first

## Vulnerability Disclosure Policy (VDP)

We welcome security research and coordinated disclosure.

**How to report**
- Email: security@nexusstl.com
- Subject: "ORCHESTRATORS_V2 Security Report"
- Include: affected version, proof-of-concept (if safe), impact assessment, and reproduction steps.

**Scope**
- In scope: runtime safety gates, tokenization and pruning, trace receipts, compliance exports, and API surface.
- Out of scope: third-party services and unrelated infrastructure.

**What to expect**
- Acknowledgment within 3 business days.
- Remediation plan within 10 business days.
- Coordinated disclosure window agreed upon before publication.

**Safe harbor**
We will not pursue legal action against researchers who follow this policy and act in good faith.

## Versioning

We follow **semantic versioning**:
- `v0.x.x` - Pre-1.0 (breaking changes allowed)
- `v1.x.x` - Stable (philosophy locked, API stable)

Current version: **v0.1.0** (trust-building phase)

## License

By contributing, you agree your code will be licensed under [MIT License](LICENSE).

## Questions?

- **Bug/Feature**: Use issue templates
- **Philosophy questions**: Read [Operational Philosophy](docs/OPERATIONAL_PHILOSOPHY.md) first
- **Architecture questions**: Read [Architecture](docs/ARCHITECTURE.md)
- **Security questions**: Read [Threat Model](docs/THREAT_MODEL.md)

---

**Remember**: This project values **restraint** over **velocity**. We protect the philosophy, resist feature creep, and maintain discipline.

*"The best code is the code you don't write. The best feature is the one you don't add."*
