---
name: Feature Request
about: Propose a new feature (read philosophy doc first!)
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

## Feature Description
<!-- What do you want to add? -->

## Use Case
<!-- Why is this needed? What problem does it solve? -->

## Proposed Implementation
<!-- High-level approach (optional) -->

## Philosophy Alignment (REQUIRED)
**Before proposing, answer these 5 questions from [Operational Philosophy](../../docs/OPERATIONAL_PHILOSOPHY.md):**

1. **Is it bounded?**
   <!-- Does this feature have explicit limits (size, time, count)? -->
   - [ ] Yes - Limits: ___________
   - [ ] No - Why not: ___________

2. **Is it receipted?**
   <!-- Does it produce verifiable evidence (logs, checksums, snapshots)? -->
   - [ ] Yes - Evidence type: ___________
   - [ ] No - Why not: ___________

3. **Is it rehearsed?**
   <!-- Can it run in dry-run mode before committing? -->
   - [ ] Yes - Dry-run mode: ___________
   - [ ] No - Why not: ___________

4. **Is it default-off?**
   <!-- Does it require explicit enablement (not auto-activated)? -->
   - [ ] Yes - Env var: ___________
   - [ ] No - Why auto-on: ___________

5. **Is it automated?**
   <!-- Can it run without human intervention (timers, webhooks)? -->
   - [ ] Yes - Automation: ___________
   - [ ] No - Manual steps: ___________

## Boundary Impact
Does this feature:
- [ ] Introduce new secrets/tokens?
- [ ] Create persistent state (files, DBs)?
- [ ] Make network calls?
- [ ] Require new dependencies?

**If any checked**: How will boundary verification catch violations?

## Anti-Patterns to Avoid
This feature should NOT:
- [ ] "Move fast and break things"
- [ ] "Scale first, safety later"
- [ ] "Cloud-native by default"
- [ ] "AI will figure it out"

## Additional Context
<!-- Anything else we should know? -->
