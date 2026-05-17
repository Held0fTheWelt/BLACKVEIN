# God of Carnage — Current Contract

**Status:** Active contract — 2026-05-18

---

## Canonical Content Module

Location: `content/modules/god_of_carnage/`

The canonical God of Carnage content module is the sole authority for story truth.
It is not a runtime module — it is a content module loaded by the engine at session start.

### Required Authority Surfaces

| Surface | Purpose |
|---------|---------|
| `module.yaml` | Module metadata, versioning, file registry, runtime policy switches |
| `canonical_path/` | Numbered directed story spine; references places, objects, characters, themes, quote anchors, and handover points |
| `locations/` | Place authority: rooms, exits, prevented actions, inventory refs, privacy, and adjacency |
| `objects/` | One-file-per-object authority, grouped by location folders where useful |
| `characters/definitions/` | Character identity and canonical profile documents |
| `characters/details/` | Relationship axes, pressure profiles, interaction patterns |
| `characters/voices/` | Character voice guidance and machine-readable `voice_consistency` policy |
| `knowledge/` | Premise, opening event coverage, quote anchors, hard-forbidden rules, content-access policy |
| `direction/` | System prompt, opening brief/sequence, subtext policy, beat library |
| `scene_graph.yaml` | Runtime node index over canonical path/location ids; not a second scene-description database |
| `phase_beat_policy.yaml` | Coarse dramatic pacing and allowed/blocked beat policy |
| `memory_policy.yaml` / `information_disclosure_policy.yaml` / `narrative_aspect_policy.yaml` | Runtime governance policy surfaces |

The old flat files (`characters.yaml`, `relationships.yaml`, `scenes.yaml`,
`triggers.yaml`, `transitions.yaml`, `endings.yaml`) are not the current GoC
content shape. Their concepts now live in modular folders and policy files.

### module_id

`god_of_carnage` — NOT `god_of_carnage_solo`

---

## Playable Roles

| Role | Type | Description |
|------|------|-------------|
| `annette` | Human-playable | Guest (Alain's wife) |
| `alain` | Human-playable | Guest (Annette's husband) |
| `veronique` | NPC | Host (Michel's wife) |
| `michel` | NPC | Host (Veronique's husband) |

**`visitor` is permanently prohibited as a role.**

### Role Selection Rules

- A player session MUST select either `annette` or `alain` as the human role
- The unselected human role is converted to an NPC participant at session bootstrap
- No other role selection is valid

---

## Runtime Profile: `god_of_carnage_solo`

`god_of_carnage_solo` is a **runtime/session profile** — NOT canonical content.

| Property | Value |
|----------|-------|
| `id` | `god_of_carnage_solo` |
| Role | Runtime bootstrap configuration only |
| Story truth | NONE — sourced from `god_of_carnage` canonical module at runtime |
| beats | EMPTY |
| actions | EMPTY |
| props | EMPTY |
| roles | Runtime structure only (annette, alain, veronique, michel) |
| rooms | Runtime navigation skeleton only; detailed place truth comes from canonical `locations/` files |

A session start request uses `runtime_profile_id="god_of_carnage_solo"` with `selected_player_role=annette|alain`.

---

## NPC Behavior

NPCs (veronique, michel) act autonomously. They are NOT limited to responding only after being addressed.
NPC free dramatic agency is defined in ADR-mvp3-012.

---

## Prohibited Patterns

| Pattern | Status |
|---------|--------|
| `visitor` as actor, role, or lane | FORBIDDEN globally |
| `god_of_carnage_solo` as canonical content module_id | FORBIDDEN |
| Story truth (beats/actions/props) in runtime profile | FORBIDDEN |
| Built-in/demo content as canonical GoC proof | FORBIDDEN |
| Session start without selected_player_role | REJECTED by engine |
| Selected role other than annette/alain | REJECTED by engine |

---

## ADR References

- ADR-mvp1-003: Role selection and actor ownership
- ADR-mvp1-005: Canonical content authority
- ADR-mvp3-012: NPC free dramatic agency
- ADR-0029: Residue removal policy (visitor)
- ADR-0025: Canonical authored content model
