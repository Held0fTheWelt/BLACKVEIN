# Reading order and authority model

## Why this document exists

The current package contains real canon, real source lineage, real proof evidence, and real mirrors.
The package becomes much easier to use when these lanes are separated explicitly.

## The four authority lanes

### 1. Active canonical MVP lane
This is the lane a human reader should use first when asking:

- what World of Shadows is,
- what the MVP canonically claims,
- what the current proof-bearing center is,
- and what remains visibly open.

Primary source family:
- `docs/MVPs/world_of_shadows_canonical_mvp/`

### 2. Normative slice-contract lane
This is the lane to use when implementing God of Carnage slice behavior precisely.

Primary source family:
- `docs/MVPs/MVP_VSL_And_GoC_Contracts/`
- `content/modules/god_of_carnage/`

### 3. Source-lineage and proof-preserving lane
This lane preserves broader WoS target truth and executable minimum proof slices that must not be silently forgotten.

Primary source family:
- `mvp/docs/`
- `mvp/reference_scaffold/`

### 4. Evidence, audit, and support lane
This lane proves or explains package reality, but does not itself define product canon.

Primary source family:
- `validation/`
- `tests/reports/`
- `docs/audit/`
- `governance/`
- `docs/technical/`
- `docs/user/`, `docs/admin/`, `docs/start-here/`

## Explicit non-canonical or support-only lanes

### Root GoC contract mirrors
- `docs/CANONICAL_TURN_CONTRACT_GOC.md`
- `docs/VERTICAL_SLICE_CONTRACT_GOC.md`
- `docs/GATE_SCORING_POLICY_GOC.md`

Useful as stable entrypoints, but not an independent normative lane.

### Embedded `repo/` tree
Useful only as packaged mirror / distribution / comparison lane.
It must not be treated as an equal live source tree.

### `'fy'-suites/`
Important for governed implementation tooling.
Not part of World of Shadows product canon.

### Runtime residue and cached observations
Useful for diagnosis and continuity only.
Never canonical authored or committed truth.

## Reading rule

Read the package in this order:

1. active canonical MVP lane,
2. normative GoC contract lane,
3. source-lineage lane when broader target or older details matter,
4. evidence/audit/support lane when proof or implementation reality matters.

## Anti-loss rule

A concept is not discarded merely because it sits in the source-lineage lane.
It must receive one of these explicit outcomes:

- preserved directly in active canon,
- carried as enduring target,
- kept as proof-preserving companion material,
- bounded as mirror/support,
- or kept as open tension.
