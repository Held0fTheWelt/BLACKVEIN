# Validation record

## Commands run

### 1. Relative markdown link check for changed files

```bash
cd /mnt/data/MVP_full_post_repair_2026-04-21 && python - <<'PY'
from pathlib import Path
import re
changed = [
    Path('docs/README.md'),
    Path('docs/audit/README.md'),
    Path('docs/MVPs/world_of_shadows_canonical_mvp/README.md'),
    Path('docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/06_implementation_and_proof_posture.md'),
    Path('docs/MVPs/world_of_shadows_canonical_mvp/09_implementation_reality_runtime_maturity_and_proof.md'),
    Path('docs/audit/world_of_shadows_canonical_mvp_repair_2026-04-20/README.md'),
]
link_re = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
missing=[]
for path in changed:
    text = path.read_text()
    for raw in link_re.findall(text):
        if raw.startswith('http') or raw.startswith('#'):
            continue
        target = raw.split('#',1)[0]
        tgt = (path.parent / target).resolve()
        if not tgt.exists():
            missing.append((str(path), raw, str(tgt)))
print('MISSING_COUNT', len(missing))
for item in missing:
    print(item)
PY
```

Result:
- `MISSING_COUNT 0`
- all changed-file relative markdown targets resolved successfully

### 2. Search for stale current-entry wording in the targeted current surfaces

```bash
cd /mnt/data/MVP_full_post_repair_2026-04-21
grep -RInE "Active repair package|active reviewer-facing repair package|preferred first-stop review package|world_of_shadows_canonical_mvp_repair_2026-04-20|Primary canonical spine" \
  docs/README.md \
  docs/audit/README.md \
  docs/MVPs/world_of_shadows_canonical_mvp/README.md \
  docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/06_implementation_and_proof_posture.md \
  docs/MVPs/world_of_shadows_canonical_mvp/09_implementation_reality_runtime_maturity_and_proof.md \
  docs/audit/world_of_shadows_canonical_mvp_repair_2026-04-20/README.md || true
```

Result:
- no remaining `Primary canonical spine` occurrences in the targeted current surfaces
- no remaining “active reviewer-facing repair package” wording in the old bundle README
- one intentional match remains in `docs/audit/README.md`, where the 2026-04-20 bundle is listed explicitly as **historical support**

### 3. Search for normalized current-route wording

```bash
cd /mnt/data/MVP_full_post_repair_2026-04-21
grep -RInE "only current|current repair / evidence route|current canonical first-pass route|historical support" \
  docs/README.md \
  docs/audit/README.md \
  docs/MVPs/world_of_shadows_canonical_mvp/README.md \
  docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/06_implementation_and_proof_posture.md \
  docs/MVPs/world_of_shadows_canonical_mvp/09_implementation_reality_runtime_maturity_and_proof.md \
  docs/audit/world_of_shadows_canonical_mvp_repair_2026-04-20/README.md || true
```

Result:
- normalized current-route wording is present in the expected route-entry files
- the old 2026-04-20 bundle is now explicitly described as historical support

## Environment notes

- This pass was documentation-only.
- No runtime or frontend replay suite was invoked.
- No environment-bounded application-test limitations changed during this delta repair.
