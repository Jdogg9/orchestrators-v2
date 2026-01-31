# Tools (src/tools)

This directory contains tool implementations used by the orchestrator.

## orch_tokenizer

Local tokenizer tool backed by the ORCH_TOKENIZER package, with a safe fallback
when the tokenizer dependency is unavailable.

**Modes:**
- `encode`: Convert text to token IDs.
- `decode`: Convert token IDs to text.
- `count`: Return token count for text.
- `info`: Return tokenizer metadata.

### Example (API)

```json
{
  "name": "orch_tokenizer",
  "args": {"action": "count", "text": "Hello"}
}
```
