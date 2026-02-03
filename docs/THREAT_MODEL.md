# Threat Model (ORCHESTRATORS_V2)

## Assets

* User prompts / outputs
* Local files (if tools enabled)
* Memory / recall data (if enabled)

## Default stance

* Memory and recall OFF
* Code execution OFF
* Web search OFF
* Require explicit enablement + bearer auth for exposure

## Risks

* Prompt injection via tools
* Data leakage via logs
* Unbounded disk growth
* Supply-chain compromise (dependencies, container images)
* Trust panel misuse (metadata correlation)
* Sandbox escape (when code-exec tools are enabled)

## Mitigations

* Feature flags + allowlists
* Log scrubbing
* Retention policies (TTL + disk cap)
* Dependency scanning + signed releases
* Redacted Trust Panel payloads
* Sandbox isolation + minimal permissions
