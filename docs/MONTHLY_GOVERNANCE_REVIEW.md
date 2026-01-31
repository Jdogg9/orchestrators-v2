# Monthly Governance Review Template

## Scope
- Review window: [YYYY-MM-01 → YYYY-MM-DD]
- Prepared by: [Name]
- Reviewer: [Name]
- Next scheduled audit: 2026-03-01

## Evidence Sources
- Vulnerability log: instance/vulnerability_log.json
- Compliance export: reports/compliance_report.pdf
- JSON-LD export: reports/compliance_report.jsonld
- Trace DB (if applicable): instance/trace.db

## Vulnerability & Reachability Summary
- Total advisories tracked: [#]
- Reachable: [#]
- Theoretical/Non-reachable: [#]
- Mitigated (pinned): [#]
- Accepted (non-reachable): [#]

### Advisory Table
| Advisory ID | Dependency | Reachability | Decision | Notes |
| --- | --- | --- | --- | --- |
| CVE-YYYY-XXXX | example-lib | reachable | mitigated | Pinned to vX.Y.Z |

## NIST AI RMF Alignment
- Measure 2.1 (Verification): [evidence references]
- Govern 2.1 (Accountability): [policy/VDP evidence]

## Operational Checks
- Summary quality tests: [pass/fail]
- Tokenizer regression tests: [pass/fail]
- Boundary verification: [pass/fail]

### Reachability Verification (Required on Dependency Updates)
- [ ] Run `pytest tests/test_summary_quality.py` after any dependency update.
- [ ] Confirm summary confidence scores remain stable vs. last release notes.

## Actions & Follow-Ups
- [ ] Action item 1
- [ ] Action item 2

## Sign-Off
- Prepared by: ____________________  Date: __________
- Reviewed by: ____________________  Date: __________
