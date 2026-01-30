# ORCHESTRATORS_V2 - Public Release Guide

## What This Is

A **sanitized, reproducible reference implementation** of the Orchestrator pattern extracted from a private system. Safe to publish, free of secrets, designed for "bring-your-own-identity."

**Project relationship**: v1 (ORCHESTRATOR_V1) is historical/research; **v2 (ORCHESTRATORS_V2) is the maintained public baseline**. The "two organisms" doctrine keeps private production (v1) separate from public distribution (v2).

## Two Organisms Living in Parallel

```
Private (ORCHESTRATOR)                  Public (ORCHESTRATORS_V2)
├─ $PROJECT_ROOT  ├─ PUBLIC_VERSION/ORCHESTRATORS_V2/
├─ Full power, identity-bound    ├─ Safe defaults, generic
├─ Recall frames, identity       ├─ Pattern library, no runtime state
├─ Production config             ├─ .env.example templates
└─ Never published               └─ GitHub-ready
```

## Pre-Publish Workflow

### 1. Scaffold (DONE ✅)
```bash
cd $PROJECT_ROOT
./scripts/make_orchestrators_v2.sh
```

Creates clean public structure with:
- ✅ Safe .gitignore (blocks secrets, state, frames)
- ✅ .env.example (no real tokens)
- ✅ Minimal server stub (OpenAI-compatible shape)
- ✅ Architecture + threat model docs

### 2. Mirror from Private (OPTIONAL - Manifest Controlled)
```bash
cd PUBLIC_VERSION/ORCHESTRATORS_V2
./scripts/import_patterns_from_private.sh
```

**Allowlist-only** mirror of safe architectural patterns (manifest-driven):
- DB maintenance scripts ✅
- Alert infrastructure ✅  
- Router logic (after sanitization) ⚠️
- Prompt templates (after sanitization) ⚠️

Manifest file:
- `scripts/mirror_manifest.txt` (format: `private_rel:public_rel`)

**Never imports:**
- ❌ .env files
- ❌ Database files
- ❌ Recall frames
- ❌ Instance/ runtime state
- ❌ Identity configuration
- ❌ Logs, backups, evidence

### 3. Sanitize Strings (REQUIRED if importing)
```bash
./scripts/sanitize_strings.sh
```

Removes private identifiers:
- ORCHESTRATOR → ORCHESTRATOR
- localhost → localhost
- /home/USER/... → $PROJECT_ROOT
- private domains → localhost
- private tokens → ORCH_*

### 4. Verify Public Boundary (REQUIRED before push)
```bash
./scripts/verify_public_boundary.sh
```

**Must pass all 5 checks:**
1. ✅ No forbidden patterns (keys, IPs, hostnames)
2. ✅ No runtime state in directories
3. ✅ No database files
grep -r "ORCHESTRATOR\|orchestrators_v2" . --exclude-dir=.git
5. ✅ .gitignore is comprehensive

### 5. Git Setup (In ORCHESTRATORS_V2 directory)
```bash
cd $PROJECT_ROOT/PUBLIC_VERSION/ORCHESTRATORS_V2
git init
git add .
git commit -m "initial: orchestrators_v2 reference implementation"
```

### 6. Push to GitHub (Fresh Repo Recommended)
```bash
# Create new repo on GitHub: orchestrators-v2 (public)
git remote add origin https://github.com/<your-username>/orchestrators-v2.git
git branch -M main
git push -u origin main
```

**Why fresh repo?** Your private repo has 13GB history (old recall frames). Fresh public repo starts clean (~10MB).

## What Gets Published

### ✅ Safe to Publish
- Router architecture (sanitized)
- Tool interface patterns
- Memory/recall design docs (no data)
- Hardening scripts (maintenance, alerts)
- .env.example (safe defaults)
- Threat model + architecture docs
- Quickstart guides

### ❌ Never Published
- Private ORCHESTRATOR identity/prompts
- Your .env with real tokens
- Database files (*.db)
- Recall frames (photographic memory)
- instance/ runtime state
- Logs, backups, evidence bundles
- Cloudflare tunnel configs
- Absolute paths (/home/USER/...)

## After Publishing

**Maintain both organisms:**
1. **Private ORCHESTRATOR** - Your production companion
   - Keep iterating freely
   - Logs, state, frames stay local
   - Deploy with existing hardening pack

2. **Public ORCHESTRATORS_V2** - Community reference
   - Extract patterns selectively
   - Run sanitization before each update
   - Keep "bring-your-own-identity" clean

## Safety Principles

**"Allowlist mirror, never bulk copy"**
- Mirror only files listed in `scripts/mirror_manifest.txt`
- Always run sanitize + verify before push
- When in doubt, leave it out

**"Runtime state is ephemeral, patterns are portable"**
- Database schemas → documented (no data included)
- Recall design → explained (no frames included)  
- Systemd patterns → templated (no hostnames included)

**"Feature flags default OFF in public"**
```bash
ORCH_MEMORY_ENABLED=0      # User must opt-in
ORCH_RECALL_ENABLED=0      # User must opt-in
ORCH_TOOL_CODE_EXEC=0      # User must opt-in
ORCH_REQUIRE_BEARER=0      # Demo mode safe
```

## Verification Commands

**Before every push:**
```bash
cd PUBLIC_VERSION/ORCHESTRATORS_V2
./scripts/verify_public_boundary.sh

# Manual double-check
grep -r "jay\|ORCHESTRATOR\|orchestrators_v2" . --exclude-dir=.git
```

**Expected:** Zero matches (except in this README explaining the sanitization).

## What ChatGPT Said

> "You want **two parallel organisms**: ORCHESTRATOR (private, production, identity-bound, full power) and ORCHESTRATORS_V2 (public, reproducible, 'bring-your-own-identity,' safe defaults)."

> "Because you already have a GitHub remote and you've had size issues: **do not ever put `instance/` under version control in V2**, even 'just for now.' It's the easiest way to accidentally publish someone's private life in pixels."

> "You already solved this instinctively. Keep that instinct."

---

**Current Status**: Scaffold complete ✅  
**Next Steps**: Import patterns (optional), sanitize, verify, publish
