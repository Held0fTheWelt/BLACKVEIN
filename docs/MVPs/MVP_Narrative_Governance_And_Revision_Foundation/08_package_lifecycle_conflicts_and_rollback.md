# Package Lifecycle, Conflicts, and Rollback

## Storage layout

```text
content/
  compiled_packages/
    god_of_carnage/
      active -> versions/2.1.4/
      versions/
        2.1.3/
          manifest.json
          package.json
          validation_report.json
        2.1.4/
          manifest.json
          package.json
          validation_report.json
      previews/
        preview_0007/
          manifest.json
          package.json
          validation_report.json
          preview_metadata.json
      history.json
```

## Lifecycle rules

### Build preview
- preview build is created from draft workspace
- preview artifacts are stored under `previews/<preview_id>/`
- preview never overwrites active version

### Promote preview
- promotion creates or references an immutable version under `versions/<package_version>/`
- active pointer is updated
- history entry is appended
- world-engine is instructed to reload active package

### Rollback
- rollback selects an earlier immutable version
- active pointer is updated to target version
- rollback event is appended to history
- world-engine reloads target version
- optional rollback verification evaluation may run

## Conflict detection

Conflicts must be checked before draft apply and before grouped preview build.
At minimum, the system must detect:

- `target_overlap`
- `semantic_contradiction`
- `dependency_violation`

### Conflict sources
- two revisions target same `actor_mind/<actor_id>`
- one revision widens legality while another tightens same scene rule
- one revision depends on a draft change not yet applied

## Conflict resolution strategies

Allowed strategies:
- `manual_select_winner`
- `manual_merge_then_rebuild`
- `dismiss_loser`
- `archive_conflicting_batch`

The MVP should not pretend semantic auto-merge is reliable.
Default to explicit human resolution.

## Example conflict record

```json
{
  "conflict_id": "conf_0042",
  "module_id": "god_of_carnage",
  "candidate_ids": ["rev_103", "rev_109"],
  "conflict_type": "target_overlap",
  "target_kind": "actor_mind",
  "target_ref": "veronique",
  "resolution_status": "pending"
}
```

## Rollback safety rules

Rollback must be blocked when:
- target version missing
- package artifacts incomplete
- world-engine reload refused
- storage state inconsistent

Rollback should still be append-only from an audit perspective:
the history log grows even when the target version is old.

## Service ownership

### backend owns
- history log
- active version metadata
- promotion and rollback orchestration
- conflict records
- conflict resolution persistence

### world-engine owns
- in-memory package load/unload state
- active package reload acceptance/refusal
- preview package session isolation
## Preview session isolation

Preview execution must not contaminate active runtime behavior.

Allowed implementation modes:
- dedicated preview process/container
- dedicated in-memory preview loader with preview session namespace
- dedicated preview token that forces package resolution against preview storage only

Minimum rule set:
- active sessions never resolve preview packages
- preview sessions never write into active session state
- ending a preview session must unload or detach preview-scoped state cleanly
- admin UI must show whether diagnostics refer to active or preview scope
