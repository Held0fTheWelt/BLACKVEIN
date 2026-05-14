# Gate Oracle Tightness Inventory

**Phase:** inventory + tracked refactor waves (gates must stay contract-strict per ADR-0039).  
**Normative guidance:** [ADR-0039](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md), [ADR-0033](../ADR/adr-0033-live-runtime-commit-semantics.md).  
**Path:** `docs/governance/gate_oracle_tightness_inventory.md` (confirmed per plan).

## 1. Purpose and classification

This inventory maps **gate entry points** and classifies **oracle quality** (not “how strict” a gate is).

| Label | Meaning |
|-------|---------|
| **Strict-contractual** | Enforces ADR/MVP safety, typed invariants, canonical IDs, or published score/trace contracts. |
| **Oracle-tight (ADR-0039 risk)** | Primary pass/fail signal is example prose, UI copy, duplicated YAML truth, or brittle source-layout substring checks. |

**A–D rubric**

| Class | Description |
|-------|-------------|
| **A** | Structure / invariant (keys, types, enums, hashes, defined semantics). |
| **B** | Product / contract constant (e.g. `visitor` prohibition, `god_of_carnage_solo`, score names from ADR). |
| **C** | Example oracle (long literals, narrator/model substrings, magic counts without schema link). |
| **D** | Duplicated truth (same string as canonical content but test does not load canonical source). |

---

## 2. Gate entry inventory

### 2.1 `tests/gates/` (canonical suite: `python tests/run_tests.py --suite gates`)

| File | Role |
|------|------|
| `tests/gates/conftest.py` | `sys.path` for backend vs world-engine; `REPO_ROOT` helpers. |
| `tests/gates/test_goc_mvp01_mvp02_foundation_gate.py` | Canonical module / runtime profile / visitor prohibition. |
| `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | LDSS live envelope, actor lanes, narrator/affordance validators, manager wiring. |
| `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py` | Diagnostics envelope, narrative gov, runner/CI registration, route/AST/integration oracles (wave 02), regression storage mocks. |
| `tests/gates/gate_contract_constants.py` | Published GoC / deterministic model ID constants for gates (wave 03; avoids scattered literals without weakening checks). |
| `tests/gates/we_contract_helpers.py` | AST + import helpers for world-engine HTTP routes and manager wiring (waves 02–03). |
| `tests/gates/gate_fixtures.py` | Versioned YAML loader for gate fixtures (wave 01). |
| `tests/gates/test_adr_live_runtime_commit_semantics_gate.py` | ADR-0033 `evaluate_live_turn_success_gate` payloads and degradation signals. |

Runner wiring: `tests/run_tests.py` maps suite `"gates"` to `target="tests/gates"` (see `SUITE_CONFIG` around lines 299–302).

### 2.2 CI workflows invoking `tests/gates/`

| Workflow | Job / step | Command |
|----------|------------|---------|
| `.github/workflows/engine-tests.yml` | `architecture-gates` | `python -m pytest tests/gates/ -v --tb=short --no-cov` |
| `.github/workflows/pre-deployment.yml` | `Run architecture enforcement gates` | `python -m pytest tests/gates/ -v --tb=short --no-cov` |

Other workflows reference `tests/gates/**` as **path triggers** (e.g. `engine-tests.yml`) but do not necessarily run the gate folder in every job.

### 2.3 ADR-0033 “hard gate” surfaces outside `tests/gates/`

ADR-0033 explicitly names backend live-trace contract tests (e.g. `backend/tests/test_observability/test_langfuse_live_c640_gate.py`, `_assert_positive_live_trace_contract`, required score names, `actor_lane_validation_status` whitelist). These are **contractual** and must not be loosened; they are **not** under `tests/gates/` but are part of the same semantic gate family.

Cross-reference: `docs/MVPs/capability_matrix_status_and_adr_relations.md` links capabilities to ADRs including live-runtime semantics.

---

## 3. Strict and contractual — do not loosen

Treat the following categories as **keep / do not soften** unless an ADR explicitly changes the contract:

- **ADR-0033** mock vs real adapter, `fallback_used`, empty visible output, missing real generation observation, opening leniency, `live_success` and degradation signal membership when tied to `evaluate_live_turn_success_gate` and published score names.
- **Actor-lane safety:** human actor must not be AI speaker; `visitor` absent from envelopes, NPC lists, and packaged responses.
- **Visitor prohibition** wherever encoded as identity / role / character absence (not as incidental UI copy).
- **Canonical module / runtime-profile boundaries** (MVP foundation): module exists, required keys, playable character set aligned with **single source of truth** when loaded from YAML (the *check* should stay strict; duplication of literals is the refactor target, not the rule).
- **Numeric / enum semantics** for quality dimensions, hash prefixes (`sha256:`), structured error codes returned by validators (e.g. `narrator_dialogue_summary_rejected`) when those codes are the published API of the validator.
- **False-green / static fixture guards** in MVP04 (e.g. `validate_not_static_fixture`, rejection of mock-only traces as final) — safety-oriented.

**Contract constants — do not “relax” by deleting checks**

Examples: `visitor`, `GOD_OF_CARNAGE_MODULE_ID`, score names required by ADR-0033 §13.7, `QualityDimension.*` enum members, LDSS function names that are import contracts (`run_ldss`, `build_scene_turn_envelope_v2`). Changing these checks without an ADR is a contract break, not an oracle cleanup.

---

## 4. Evidence-backed triage matrix (refactor candidates and mixed cases)

Each row satisfies the plan’s evidence fields. **N = 22** findings in this wave (C/D primary; B where “prose in disguise”; A where called out as ambiguous).

| # | Gate file | Test or block | Lines (approx.) | Assertion / oracle excerpt | A–D | strict-contractual vs oracle-tight | Why not “merely strict” (if flagged) | safe_to_refactor | suggested_replacement_oracle |
|---|-------------|---------------|-------------------|-----------------------------|-------|-----------------------------------|--------------------------------------|------------------|------------------------------|
| 1 | `test_goc_mvp01_mvp02_foundation_gate.py` | (method testing builtin template title) | 45 | `assert template.title == "God of Carnage"` | D | oracle-tight | Duplicates display title that likely already lives in canonical module YAML; drift if marketing copy changes. | yes | Load `module.yaml` (or template loader) and assert equality to `doc["content"]["title"]` (or documented field path). |
| 2 | `test_goc_mvp01_mvp02_foundation_gate.py` | playable roles / characters | 72–74, 138–139 | playable ids derived from runtime-profile contract and canonical `characters.yaml` | B | **addressed wave 04** | IDs match GoC authority; assertions now compare runtime-profile-derived playable humans to canonical content instead of restating actor ids in the gate. | done | **Wave 04:** `GOD_OF_CARNAGE_PLAYABLE_HUMAN_IDS` / `GOD_OF_CARNAGE_RUNTIME_ACTOR_IDS` derived from `goc_solo_role_templates()`, then checked against canonical module YAML. |
| 3 | `test_goc_mvp01_mvp02_foundation_gate.py` | visitor prohibition | 59, 74, 147, 179, 185 | `assert "visitor" not in ...` | B | strict-contractual | Hard ID check tied to ADR/MVP safety. | no | Keep; optionally centralize constant `FORBIDDEN_ACTOR_ID = "visitor"`. |
| 4 | `test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | `_primary_human_ldss_input` / NPC autonomous turn | — | `player_input` from `tests/gates/fixtures/mvp3_ldss_player_inputs.yaml` (keys `primary_human_ldss_input`, `secondary_human_ldss_input`, `npc_autonomous_scene_turn`) | C | **addressed wave 03 + 04** | Same prose, versioned fixture + `copy.deepcopy` load; wave 04 also removed actor-name key coupling from the Python gate. | done | **Wave 03:** `mvp3_ldss_player_inputs.yaml` via `gate_fixtures.load_yaml`; **Wave 04:** actor lanes derive from runtime role helpers. |
| 5 | `test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | `test_narrator_rejects_dialogue_recap` | 528–531 | `bad_text = "Véronique and Alain argue..."` then `status`/`error_code` | C | oracle-tight | Validator contract is **error_code**; prose is arbitrary example — brittle if heuristics tighten/loosen on different wording. | yes | Move strings to `tests/fixtures/narrator_voice_negative_cases.json` or generate minimal counterexamples from rules table documented next to validator. |
| 6 | `test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | `test_narrator_modal_language_does_not_force_player_state` | 537–540 | `bad_text = "You decide that Alain is right..."` | C | oracle-tight | Same as row 5. | yes | Shared fixture file + parameterized test. |
| 7 | `test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | `test_narrator_cannot_reveal_hidden_npc_intent` | 546–549 | `bad_text = "You can see through Alain's composure;..."` | C | oracle-tight | Same as row 5. | yes | Same. |
| 8 | `test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | `test_valid_narrator_inner_perception` | 555–557 | `good_text = "You notice the pause before Alain answers;..."` | C | oracle-tight | “Good” path still tied to one prose sample; risk of false red if style rules evolve. | yes | Golden “approved” set in fixture; or assert structural properties if validator exposes features. |
| 9 | `test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | `test_similar_allowed_requires_similarity_reason` | 567–585 | `text="Alain turns his phone face down."` / similarity_reason string | C | oracle-tight | Scene text + reason are narrative examples; error_code is the real contract. | partial | Keep validator API checks; isolate prose in `yaml` fixtures. |
| 10 | `test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | `test_rejects_unadmitted_plausible_object` | 591–602 | `text="Véronique places a knife on the table."` | C | oracle-tight | Object ID `knife` is structural; **display name / sentence** is example prose. | partial | Keep `object_id` / tier; shorten or neutralize text (or load from fixture). |
| 11 | `test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | `test_canonical_object_affordance_approved` | 608–614 | `text="Alain glances at his phone."` | C | oracle-tight | Same as row 9. | yes | Neutral fixture text `actor X manipulates admitted object Y`. |
| 12 | `test_goc_mvp03_live_dramatic_scene_simulator_gate.py` | `test_mvp3_gate_ldss_invoked_through_finalize_committed_turn` | — | **Wave 02:** `assert_ldss_import_and_module_wiring` + AST on `manager.py` / `_build_ldss_scene_envelope` / `_finalize_committed_turn` (`we_contract_helpers.py`) | A / B | **strict-contractual** | Replaces source substring grep; still fails if `run_ldss` / `build_scene_turn_envelope_v2` unwired or `_build_ldss_scene_envelope` removed. | done | **Addressed wave 02:** import-oracle + AST call graph + module symbol checks. |
| 13 | `test_goc_mvp04_observability_diagnostics_gate.py` | `test_mvp04_diagnostics_endpoint_returns_last_turn_evidence` | — | **Wave 02:** `extract_router_get_paths` + `assert_diagnostics_and_narrative_gov_routes_registered` on `http.py` AST; `assert_story_runtime_manager_exposes_diagnostics_api` | A / B | **strict-contractual** | Route path + handler name parsed from decorators (not raw substring scan of file). | done | **Addressed wave 02:** FastAPI route AST + manager public API surface (method names). |
| 14 | `test_goc_mvp04_observability_diagnostics_gate.py` | `test_mvp04_narrative_gov_surface_returns_runtime_evidence` | — | **Wave 02:** `NarrativeGovSummary.to_dict()` panels + `assert_narrative_gov_template_renders_panel_contract` (`data-testid="narrative-gov-summary"`, proxy URL `/_proxy/api` + route suffix from contract helper, JS references panel keys); admin template gained `runtime_module_health` panel for parity | A / B | **strict-contractual** | UI path derived from same route suffix as §row 13; machine keys + stable selector vs incidental copy. | done | **Addressed wave 02:** selector + JSON key contract + minimal template panel for `runtime_module_health`. |
| 15 | `test_goc_mvp04_observability_diagnostics_gate.py` | `test_mvp04_runner_registration_exists` | 562 | `assert "--mvp4" in source` | B | strict-contractual | Tooling gate for canonical runner flag. | no | Keep (document in ADR if flag renamed). |
| 16 | `test_goc_mvp04_observability_diagnostics_gate.py` | `test_mvp04_workflow_registration_exists` | 571–573 | `assert "world-engine" in content` | C | oracle-tight | Very weak signal — word could appear for unrelated reasons. | yes | Parse YAML job matrix and assert `pytest tests/gates` or `tests/gates/` in **architecture-gates** job only. |
| 17 | `test_goc_mvp04_observability_diagnostics_gate.py` | `test_mvp04_execute_turn_includes_diagnostics_envelope` | — | **Wave 02:** `assert_finalize_committed_turn_assigns_diagnostics_envelope` + `assert_goc_module_gate_in_finalize` (AST) + subprocess pytest of `test_execute_turn_produces_diagnostics_envelope_annette` | A / B | **strict-contractual** | Subprocess proves real `execute_turn` response includes `diagnostics_envelope`; AST proves wiring in `_finalize_committed_turn`. | done | **Addressed wave 02:** AST assign + world-engine integration subprocess (stricter than source quote match). |
| 18 | `test_goc_mvp04_observability_diagnostics_gate.py` | envelope / dict guards | 471–477, 198–223 | `assert "content_module_health" in d` | A | strict-contractual | Panel keys are schema-like contract for `NarrativeGovSummary`. | no | Optional: JSON Schema for summary. |
| 19 | `test_goc_mvp04_observability_diagnostics_gate.py` | `test_mvp04_phase_b_narrator_block_span_instrumentation` | 873 | `assert any(kind in ("narrator_block", ...) for kind in event_kinds)` | B | strict-contractual | Kind tokens name instrumentation contract for deterministic narrator path. | no | If renamed, update ADR + all producers in one change. |
| 20 | `test_goc_mvp04_observability_diagnostics_gate.py` | same test cost dict | 876–878 | `assert narrator_cost["model"] == "narrative_runtime_agent_deterministic"` | B | strict-contractual | Billing/model token encodes deterministic path contract. | no | Treat as named constant exported from production module and imported by test. |
| 21 | `test_goc_mvp04_observability_diagnostics_gate.py` | MagicMock storage blocks | ~1013–1231 | `storage.get.return_value = { ... }` nested dicts | C | oracle-tight | Large literal “trace-like” payloads duplicate trace shape; drift when envelope evolves. | yes | Load JSON fixture from `tests/fixtures/...`; validate against schema; only mutate fields under test. |
| 22 | `test_adr_live_runtime_commit_semantics_gate.py` | `_live_turn_claim` payload | 29–31, 42–43 | Same narrator text in `visible_scene_output` and `trace.observations[].output` | D | oracle-tight | Duplicated string in two branches of same synthetic payload — not loading real trace. | yes | Helper `sample_visible_block()` or load minimal JSON fixture once. |

**Additional notes (no extra table row):** `test_adr_live_runtime_commit_semantics_gate.py` lines 80–161 asserting membership of degradation signal strings in `result["degradation_signals"]` are **strict-contractual** (A/B) **provided** those strings match the canonical set in `ai_stack` — they are not “narrator prose oracles.”

---

## 5. Prioritization (P0 / P1 / P2)

### P0 — Highest refactor value (prose, UI paths, fragile layout)

- Rows **1, 5–11, 21–22** (and **16** addressed wave 01): example prose, duplicated payload prose, large mock JSON literals. Rows **14, 17** addressed wave 02 (see §9).

### P1 — Structural / integration smell without player-facing prose

- Rows **12, 13** — **addressed wave 02** (AST / route registry / integration subprocess). Row **4** — **addressed wave 03** (LDSS `player_input` YAML fixture; see §9).

### P2 — Verify before change (constants / IDs)

- Rows **2, 15, 19–20**: may look like “magic strings” but trace to **product or telemetry contracts**; refactor by **centralizing constants** or schema, not by deleting checks.

---

## 6. Strategy sketches (follow-up phase only)

1. **Single source of truth:** For GoC IDs, titles, and prompts, always load from canonical `content/modules/god_of_carnage/...` (or existing loader APIs) inside gates; tests should not re-list character display names.
2. **Validator suites:** Move narrator/affordance positive/negative strings to versioned fixture files; keep assertions on `status` + `error_code` + optional structured `features`.
3. **Structural wiring:** Prefer `world-engine/tests/test_mvp3_ldss_integration.py`-style execution proof over `read_text()` substring checks for `manager.py` / `http.py`.
4. **Admin UI:** Split “data contract” tests (summary dict) from “template contains string” tests; latter belong in frontend/admin test harness with stable selectors.
5. **Trace mocks:** Store baseline JSON under `tests/fixtures/` with schema validation to catch drift explicitly.

---

## 7. Screening commands used (first pass only)

Heuristic greps as suggested in the plan were applied under `tests/gates/` for: `assert .* in `, character names, `title`/`description`, `MagicMock`/`return_value`. All hits were manually triaged per ADR-0039 (strict vs oracle-tight distinction).

---

## 8. Success criteria checklist

| Criterion | Status |
|-----------|--------|
| Full inventory of `tests/gates/` files + CI mapping | Done (§2) |
| ADR-0033 / capability matrix cross-reference | Done (§2.3, §3) |
| N evidence-complete C/D (and mixed) rows with strategies | Done (§4, **N=22**) |
| Initial inventory phase: zero edits | Done (superseded by refactor waves; see §9) |
| Explicit “do not loosen” contractual list | Done (§3) |

---

## 9. Refactor wave status

### Wave 1 (completed)

**Rows addressed:** 1, 5–11, 16, 21, 22  

**Summary:** Canonical `module.yaml` title oracle; MVP3 narrator/affordance prose in `tests/gates/fixtures/*.yaml`; CI workflow YAML parse for `architecture-gates`; MVP4 mock/cost payloads in YAML; ADR-0033 synthetic narration single fixture. Contractual strictness preserved (same strings / semantics, centralized sources).

### Wave 2 (completed)

**Rows addressed:** 12, 13, 14, 17  

**Rows deferred:** none  

**Summary:**

- **12:** LDSS wiring — import contract (`run_ldss`, `build_scene_turn_envelope_v2` callable) + AST on `manager.py` (`_build_ldss_scene_envelope` calls, `_finalize_committed_turn` → `_build_ldss_scene_envelope`, `event['scene_turn_envelope']`, `GOD_OF_CARNAGE_MODULE_ID`). No `read_text()` substring for import lines.
- **13:** Diagnostics + narrative gov — AST extraction of `@router.get` paths on `world-engine/app/api/http.py` with handler name checks; manager AST for `get_last_diagnostics_envelope` / `get_narrative_gov_summary` on `StoryRuntimeManager`.
- **14:** Narrative Gov admin surface — `data-testid="narrative-gov-summary"` on template root; proxy fetch URL built as `/_proxy/api` + `/story/runtime/narrative-gov-summary`; JS references all `NarrativeGovSummary` top-level panel keys (template extended with **Runtime Module Health** panel so `runtime_module_health` is covered).
- **17:** `execute_turn` diagnostics — AST proves `build_diagnostics_envelope` call + `event['diagnostics_envelope']` assign in `_finalize_committed_turn`; subprocess runs `world-engine/tests/test_mvp4_diagnostics_integration.py::test_execute_turn_produces_diagnostics_envelope_annette` with `PYTHONPATH` including world-engine, repo root, backend, story_runtime_core.

**Test results (authoritative run after wave 02 implementation):**

- `python tests/run_tests.py --suite gates` — **93 passed, 0 failed** in ~33s.
- `python tests/run_tests.py --suite engine --quick` — **1286 passed, 0 failed** in ~210s.
- Admin template touch: `cd administration-tool; python -m pytest tests/test_manage_routes.py -q --no-cov` — **96 passed, 0 failed**.

**Remaining risks / follow-up:** Subprocess in row 17 adds ~seconds to gates suite; acceptable for contract strength.

### Wave 3 (completed)

**Rows addressed:** 4 (LDSS `player_input` fixture); Narrative Gov `test_mvp04_narrative_gov_summary_from_manager` (manager `read_text` substring → AST + full `to_dict` key contract); contract constant centralization (`tests/gates/gate_contract_constants.py`) for GoC IDs, `visitor`, deterministic model tokens where duplicated across MVP01/03/04 gates.

**Rows deferred:** none (optional future: import production-exported constants for `ldss_deterministic` if a stable module-level symbol exists — deferred to avoid coupling gates to non-contract internal layout).

**Summary:**

- **Row 4:** `tests/gates/fixtures/mvp3_ldss_player_inputs.yaml` holds Annette/Alain/NPC-autonomous player lines and MVP04-shared LDSS/diagnostics prose; MVP03 and MVP04 load via `gate_fixtures.load_yaml` + `copy.deepcopy`.
- **Narrative Gov manager test:** `assert_story_runtime_manager_exposes_diagnostics_api` + `assert_manager_get_narrative_gov_summary_calls_builder` (AST) replace raw `read_text` substring checks; `set(d.keys()) == set(NARRATIVE_GOV_SUMMARY_TO_DICT_KEYS)` pins `NarrativeGovSummary.to_dict()` surface to `ai_stack/diagnostics_envelope.py`.
- **Constants:** `FORBIDDEN_RUNTIME_ACTOR_ID`, `GOD_OF_CARNAGE_*`, `LDSS_DETERMINISTIC_MODEL_ID`, `NARRATIVE_RUNTIME_AGENT_DETERMINISTIC_MODEL_ID` — assertions still explicit against forbidden/contract IDs (not tautological).

**Test results (authoritative run after wave 03 implementation):**

- `python tests/run_tests.py --suite gates` — **93 passed, 0 failed** in ~33s (`============================= 93 passed in 32.65s =============================`).
- `python tests/run_tests.py --suite engine --quick` — **1286 passed, 0 failed** in ~210s (`1286 passed in 209.52s`).
- `cd administration-tool; python -m pytest tests/test_manage_routes.py -q --no-cov` — **not run** (no `administration-tool` changes this wave).

### Wave 4 (completed)

**Rows addressed:** 2; MVP3 non-GoC LDSS guard; MVP4 runner / marker registration probes.

**Rows deferred:** none.

**Summary:**

- **Row 2:** GoC playable-human and runtime-actor expectations now derive from `goc_solo_role_templates()` and are checked against canonical `module.yaml` / `characters.yaml`; the foundation gate no longer repeats concrete actor ids as local oracles.
- **MVP3:** Actor-lane assertions now derive the selected human, non-selected AI actors, and display names from the runtime profile contract. The non-GoC LDSS guard test uses AST helpers for `_build_ldss_scene_envelope` and `build_ldss_input_from_session`, replacing raw `read_text()` substring probes.
- **MVP4:** Diagnostics gates derive actor ownership from the same runtime-profile helpers. `tests/run_tests.py --mvp4` is checked via AST argparse/preset structure, and marker registration is checked by parsing pytest INI files instead of substring matching.

**Test results:** see current implementation run notes for the latest green gate subset.

---

## 10. Staging provider readiness and credential discipline (repair / audit prompts)

Use this section for **staging verification**, **live Langfuse gates**, and **repair/audit prompts** when a real provider call is required. It replaces ad-hoc instructions such as “set `OPENAI_API_KEY` manually” in chat or runbooks.

### Required behavior

1. **Fetch** provider/runtime credentials only through the **approved backend path** (Operational Governance provider store, internal runtime credential handoff). Runtime code resolves secrets via backend (`GET /api/v1/internal/provider-credential/<provider_id>` with internal auth), not via ad-hoc `.env` assumptions in agent instructions. Where tooling exposes the same contract, use the **repo MCP → backend** credential path instead of asking operators to paste keys.
2. **Verify** OpenAI (or selected provider) readiness using **boolean / fingerprint / health** signals only — never print, log, summarize, or embed secret material in reports, fixtures, docs, test output, Langfuse metadata, or screenshots.
3. **Run** the staging session with **real** model credentials **only when** the readiness check confirms they are available; otherwise classify as `provider_credential_missing` and keep LDSS / fallback posture **degraded** (do not assert live success).
4. If credentials are **missing or invalid**, the audit must keep **`non_mock_generation_pass=0`**, **`fallback_absent=0`**, and **`live_opening_contract_pass=0`**. **`non_mock_generation_pass` may only become `1.0` when a real upstream provider call succeeds** (not when a mock path or oracle bypass would pass).

### Operator and agent constraints

- **Do not** ask users to paste API keys into chat or tickets.
- **Do not** write secrets into fixtures, documentation, test output, or Langfuse fields.
- **Only** report non-secret readiness fields (see below).

### Allowed report fields (example)

```json
{
  "openai_api_key_present": true,
  "credential_source": "backend_internal_credentials",
  "provider_ready": true,
  "selected_provider": "openai",
  "selected_model": "gpt-4.1-mini",
  "secret_exposed": false
}
```

(`selected_model` should name the configured model id string; omit or redact if your surface does not expose it safely.)

### Forbidden report fields (non-exhaustive)

```json
{
  "api_key": "...",
  "authorization_header": "...",
  "secret_value": "..."
}
```

### Prompt line to use in repair / audit checklists

Replace:

```text
Set OPENAI_API_KEY manually
```

With:

```text
Use MCP/backend credential retrieval. Do not expose secrets.
```

*Inventory living document: matrix rows §4 reflect latest gate oracles; refactor waves documented in §9; staging credential rules in §10.*
