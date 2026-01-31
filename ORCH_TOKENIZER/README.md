# ORCH_TOKENIZER

Public tokenizer tool for ORCHESTRATORS_V2.

## Overview

ORCH_TOKENIZER exposes a local tokenizer tool with simple operations:

- `encode`: text → token IDs
- `decode`: token IDs → text
- `count`: count tokens in text
- `info`: tokenizer metadata

## Configuration

Set the tokenizer directory via environment variable:

```
ORCH_TOKENIZER_DIR=/path/to/orchestrators_v2/ORCH_TOKENIZER/tokenizers
```

Defaults to the local ORCH_TOKENIZER/tokenizers directory if not set.

## Tool Name

Registered tool name: `orch_tokenizer`

## Example Payloads

Encode:

```
{"action":"encode","text":"Hello"}
```

Decode:

```
{"action":"decode","tokens":[15496, 995]}
```

Count:

```
{"action":"count","text":"Hello"}
```

Info:

```
{"action":"info"}
```
