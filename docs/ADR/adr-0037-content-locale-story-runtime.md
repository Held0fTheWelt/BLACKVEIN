# ADR-0037: Content-Backed Locale for Story Runtime Shell

## Status

Accepted

## Context

Player-visible shell strings, greeting-imperative patterns, and non-opening model language directives were embedded in Python (`world-engine/app/story_runtime/manager.py`, `ai_stack/langgraph_runtime_executor.py`), which violates the product rule that **authorable prose and locale-specific patterns live in the content module**, not the engine.

## Decision

1. **Single resolver** — `story_runtime_core.content_locale` loads YAML/MD only from `content/modules/<module_id>/locale/` (see `resolve_string`, `load_session_language_model_directive`, greeting helpers).

2. **God of Carnage v1** — [`content/modules/god_of_carnage/locale/module_strings.yaml`](../../content/modules/god_of_carnage/locale/module_strings.yaml), [`player_input_rules.yaml`](../../content/modules/god_of_carnage/locale/player_input_rules.yaml), and [`locale/model_directives/session_output_language_{de,en}.md`](../../content/modules/god_of_carnage/locale/model_directives/) are listed in [`module.yaml`](../../content/modules/god_of_carnage/module.yaml) `files:`.

3. **Discovery** — `resolve_content_modules_root()` uses `WOS_REPO_ROOT` when set, else walks parents from `story_runtime_core` for a checkout containing `content/modules/`.

4. **Regression guard** — `scripts/check_runtime_shell_locale_drift.py` fails CI if banned legacy substrings reappear in the two engine paths above.

## Consequences

- **Positive:** Shell copy and model directives are diffable with module content; ADR-0036 remains the selector (`session_output_language`), not the string store.
- **Negative:** Runtime requires a resolvable `content/modules` tree (same constraint as other content-driven features).

## Relation

- [ADR-0036](adr-0036-player-session-output-language.md) — output language selection unchanged.
- Supersedes unused `story_runtime_core/player_input_intent.py` experiment (removed).
