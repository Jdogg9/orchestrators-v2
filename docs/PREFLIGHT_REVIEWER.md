# Preflight Reviewer (Optional Module)

The Preflight Reviewer is an **optional** guardrail that runs *before* tool execution. It is not part of the default runtime. Enable only if you want a secondary “sanity check” for high-consequence tool calls.

## Purpose

- Provide a second-pass decision on risky tool calls.
- Capture a compact, non-sensitive rationale for why a tool call is allowed or blocked.
- Enforce a stricter policy layer for network or filesystem actions.

## Status

- **Not enabled by default.**
- **Not required** for core routing, approvals, or Trust Panel functionality.

## When to Use

- You want an extra safety net on write operations.
- You are operating in a highly regulated environment.
- You need an auditable preflight step before execution.

## Integration Notes

- The reviewer should run *after* intent routing and *before* tool execution.
- It should never emit chain-of-thought; only return short, structured verdicts.
- All outputs must be scrubbed before persistence.

## Related Docs

- [Tool Approval Contract](TOOL_APPROVAL_CONTRACT.md)
- [Threat Model](THREAT_MODEL.md)
- [Optional Modules](OPTIONAL_MODULES.md)
