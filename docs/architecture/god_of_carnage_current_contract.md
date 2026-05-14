# God of Carnage — Current Contract

**Status:** Active contract — 2026-04-26

---

## Canonical Content Module

Location: `content/modules/god_of_carnage/`

The canonical God of Carnage content module is the sole authority for story truth.
It is not a runtime module — it is a content module loaded by the engine at session start.

### Required Files

| File | Purpose |
|------|---------|
| `module.yaml` | Module metadata, versioning, file registry |
| `characters.yaml` | Character definitions: veronique, michel, annette, alain |
| `relationships.yaml` | Relationship axes and dynamics |
| `scenes.yaml` | Scene phases (5 phases) |
| `transitions.yaml` | Scene transition conditions |
| `triggers.yaml` | Trigger types with recognition markers |
| `endings.yaml` | End state conditions |
| `direction/system_prompt.md` | LLM system prompt guidance |
| `direction/scene_guidance.yaml` | Per-scene constraints |
| `direction/character_voice.yaml` | Character voice guidance plus machine-readable `voice_consistency` marker policy |

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
| rooms | Runtime navigation structure (hallway, living_room, bathroom) |

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
