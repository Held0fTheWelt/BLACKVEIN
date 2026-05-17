# Prompt Store Seeds

This folder is the repository-level seed collection for the database-backed
Prompt Store.

JSON files may be split by domain (`ai_stack`, `world_engine`, evaluators, and
future agent lanes). The backend seeds every `*.json` file recursively. Existing
database rows are preserved by default so live environment edits survive
container rebuilds.

Set `WOS_PROMPT_STORE_SEED_OVERWRITE=true` or run `flask seed-prompt-store
--overwrite` to refresh existing rows from these files. Use overwrite mode for
deterministic test fixtures or deliberate prompt refreshes only.

Each prompt should define:

- `prompt_key`: stable runtime lookup key.
- `name`: human-readable label for the Admin Prompt Store.
- `category`: grouping in the Admin Prompt Store.
- `prompt_type`: filterable kind such as `runtime_prompt`, `runtime_fragment`,
  `game_text`, or `readout_text`.
- `domain`: owning runtime area such as `ai_stack` or `world_engine`.
- `tags`: operator filters such as `important`, `actor-lane`, `localization`,
  `readout`, or `player-shell`.
- `description`: operator-facing explanation.
- `template` or `template_lines`: the actual template.
- `variables`: optional explicit template variables.
- `source_path` and `source_symbol`: where the prompt was centralized from.

Runtime services should read prompts through `ai_stack.prompt_store`, receiving
the database bundle from backend resolved runtime config when available and
falling back to these seed files for tests/bootstrap.
