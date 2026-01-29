# Operational Philosophy

This document captures the **principles** (not implementation) behind ORCHESTRATORS_V2's design decisions. These patterns emerged from production operation of the v1 system and represent lessons learned from running a sovereign AI system 24/7.

## Core Principles

### 1. Bounded Memory

**Philosophy**: Unbounded growth is unbounded risk.

- Memory systems must have **explicit retention policies** (TTL, disk caps, per-user limits)
- Default to ephemeral; opt-in to persistent
- Automated cleanup is not optional - it's part of the system contract
- Example: `MEMORY_TTL_DAYS=30`, `MAX_DISK_MB=500`, automated VACUUM on timer

**Why**: Systems that grow forever eventually fail. Entropy is a feature, not a bug.

### 2. Receipts Over Assertions

**Philosophy**: Trust, but verify. With evidence.

- Manual validation generates **evidence bundles** (logs, snapshots, checksums)
- Configuration changes must be **receipted** (release snapshots, git commits)
- "It works" → "Here's proof it works" (integrity checks, test outputs, sentinel logs)
- Example: Backup script validates SQLite integrity pre/post copy, logs checksums

**Why**: Assertions decay. Receipts don't.

### 3. Rehearsal Before Release

**Philosophy**: Dress rehearsals reveal what staging tests miss.

- Critical workflows run in **dry-run mode** first (capture, maintenance, backups)
- Evidence bundles reviewed before "execute mode" enabled
- Release candidates signed off with operator approval + snapshot
- Example: Maintenance script runs TTL enforcement in dry-run, operator reviews deletion list

**Why**: Surprises in production are expensive. Rehearsals are cheap.

### 4. Defaults Off

**Philosophy**: Power requires explicit consent.

- Sensitive features **disabled by default** (memory capture, code execution, web search, recall)
- Bearer auth **optional but recommended** (local-first doesn't mean no-auth)
- Feature flags control capability boundaries (`MEMORY_ENABLED=0`, `TOOL_EXEC=0`)
- Example: `.env.example` ships with all power tools off, localhost-only

**Why**: Safety by default. Power by choice.

### 5. Automation Over Heroics

**Philosophy**: Reliable systems don't depend on heroic operators.

- Daily backups run on **systemd timers** (not manual cron)
- Maintenance runs automatically (VACUUM, TTL enforcement, frame pruning)
- Alerting triggers on failures (systemd OnFailure hooks)
- Example: Backup @ 02:00, maintenance @ 03:00, both log to journalctl, operator just monitors

**Why**: Humans forget. Timers don't.

## Design Consequences

These principles create specific architectural choices:

### Privacy-First (not Privacy Theater)

- No phone-home analytics
- No cloud dependencies (unless you explicitly add them)
- Runtime state never committed (`.gitignore` is a security boundary)
- Secrets scrubbed before any persistence

### Local-First (not Cloud-First)

- Ollama for LLM inference (your machine, your weights)
- SQLite for persistence (file-based, no server)
- ComfyUI for image generation (local GPU)
- Network calls are **explicit opt-ins** (web search tool, external APIs)

### Boundary Verification (not Wishful Thinking)

- `verify_public_boundary.sh` runs 5 checks before any publish:
  1. No forbidden patterns (API keys, /home/user, private domains)
  2. No runtime state (instance/, logs/, backups/ must be empty)
  3. No database files (*.db excluded from git)
  4. Environment safety (.env.example exists, .env does not)
  5. .gitignore comprehensive (all critical patterns present)

### Modular Power (not Monolithic Trust)

- Router chooses models (tool vs chat vs vision)
- Tools are isolated (web search doesn't touch memory)
- Memory is opt-in (retrieve works, capture requires flag)
- Each layer can be audited independently

## What This Is NOT

This is not a philosophy of:

- **Move fast and break things** → We rehearse, then execute
- **Scale first, safety later** → We bound, then grow
- **Cloud-native by default** → We run local, opt-in to network
- **AI will figure it out** → We verify, with receipts

## Applying These Principles

When extending ORCHESTRATORS_V2, ask:

1. **Bounded?** - Does this feature have explicit limits (time, disk, memory)?
2. **Receipted?** - Can I prove it worked (logs, checksums, test output)?
3. **Rehearsed?** - Can I dry-run this before executing for real?
4. **Default off?** - Does this require explicit enablement?
5. **Automated?** - Can a timer do this instead of a human?

If you answer "no" to multiple questions, reconsider the design.

## Lineage

These principles evolved from operating the v1 (AIMEE_ORCHESTRATORS) system in production:

- **Bounded memory** - After hitting 13GB git repo from unbounded recall frames
- **Receipts** - After "I think backups ran" wasn't good enough for GO signoff
- **Rehearsal** - After maintenance script deleted wrong data in execute mode
- **Defaults off** - After realizing new features shouldn't auto-activate
- **Automation** - After manually running backups for 3 months (never again)

These aren't theoretical. They're scars.

## Further Reading

- [ARCHITECTURE.md](ARCHITECTURE.md) - Layer design (how components interact)
- [THREAT_MODEL.md](THREAT_MODEL.md) - Security posture (what we protect against)
- [PUBLIC_RELEASE_GUIDE.md](PUBLIC_RELEASE_GUIDE.md) - v1 → v2 workflow (two organisms doctrine)

---

**Meta**: This document is philosophy, not code. If you want implementation examples, see `scripts/` and `src/`. The philosophy explains *why* we wrote it this way.
