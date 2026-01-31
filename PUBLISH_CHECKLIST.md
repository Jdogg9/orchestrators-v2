# Publish Checklist (V2.0 Stable)

- [ ] Run pytest one last time (Confirm 58/58 passing).
- [ ] Run ./scripts/verify_public_boundary.sh (Confirm ✅).
- [ ] Check instance/ folder (Ensure it is empty).
- [ ] Check requirements.txt (Verify tiktoken and Flask versions are pinned).
- [ ] Tag the commit: git tag -a v2.0.0 -m "V2.0 Stable Release".
- [ ] Push tags: git push origin v2.0.0.
