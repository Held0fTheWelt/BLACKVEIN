# Acceptance Criteria and Open Risks

## Non-negotiable acceptance criteria

### Runtime
- runtime can load only approved compiled package versions
- runtime builds a typed scene packet for turn execution
- runtime validator strategy is inspectable and configurable
- invalid triggers and invalid responders are blocked before commit
- runtime produces actionable validation feedback on rejected outputs
- player never sees a raw validation failure or hung turn
- every playable scene has fallback content, whether authored or compiler-generated default
- preview sessions are isolated from active runtime sessions

### Package lifecycle
- preview build produces isolated preview artifact
- promotion appends immutable version history entry
- rollback to older version is possible without rebuilding source
- world-engine can reload active package after promotion or rollback

### Revisions
- revision candidates store target kind and target ref
- unresolved conflicts block draft apply
- workflow transitions are enforced
- batch grouping/filtering is available in admin

### Evaluation
- preview evaluation compares against active baseline
- promotion readiness is derived from validation + evaluation + workflow
- coverage report is available per evaluation run
- live quality metrics include first-pass success, corrective retry rate, and safe fallback rate


### Persistence and migrations
- new governance tables exist with required indexes
- additive migrations can be deployed before UI and workflow activation
- at least one existing compiled package can be backfilled into persistent package records
- admin UI tolerates empty governance tables without runtime errors

### Administration-tool
- operator can reach rollback from overview or packages
- revisions page shows conflicts inline
- package comparison combines manifest, effective policy diff, evaluation delta, and readiness
- runtime health highlights retry/fallback spikes without manual polling
- critical notifications surface without manual polling

## Open risks that remain after MVP

### 1. Semantic merge quality
Manual resolution is the default because reliable semantic auto-merge is not yet assumed.

### 2. Multi-module dependency graph
The revised MVP leaves room for dependency management but does not require it as first-class mandatory behavior.

### 3. Evaluation oracle limits
Even strong metrics do not fully prove dramatic quality.
Golden scenarios and delta metrics reduce risk but do not eliminate taste and edge-case uncertainty.

### 4. Authoring UI depth
The administration-tool will expose governance, not a full creative editing studio.
That remains a later layer.

### 5. Dramatic-quality layers remain staged
Emotional continuity, contradiction detection, proactive steering, and player-affect adaptation are documented as extension seams.
They should not be faked with shallow heuristics in the core MVP runtime.

## Recommended explicit follow-on after MVP
- dependency graph for multi-module continuity
- richer coverage guidance and scenario generation
- stronger semantic validator plug-ins
- emotional-state continuity and contradiction guard
- bounded branch simulation against preview packages
