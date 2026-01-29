---
name: Bug Report
about: Report a bug (boundary violations, runtime errors, test failures)
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
<!-- Clear description of what went wrong -->

## Reproduction Steps
1. 
2. 
3. 

## Expected Behavior
<!-- What should have happened? -->

## Actual Behavior
<!-- What actually happened? -->

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.10.12]
- ORCHESTRATORS_V2 commit: [e.g., 6dc6162]

## Boundary Check
**Did you run boundary verification before reporting?**
```bash
./scripts/verify_public_boundary.sh
```
Result: [ ] PASS / [ ] FAIL

## Logs / Traces
<!-- Paste relevant logs, error messages, or traces -->
```
(paste here)
```

## Philosophy Alignment Check
Does this bug violate any core principles?
- [ ] Bounded Memory (unbounded growth)
- [ ] Receipts (missing evidence/logs)
- [ ] Rehearsal (no dry-run mode)
- [ ] Defaults Off (unwanted auto-activation)
- [ ] Automation (manual intervention required)

## Additional Context
<!-- Anything else we should know? -->
