# MVP D1 — Repository Surface, Truth, and Structure Cleanup

**Project:** World of Shadows  
**Document type:** Execution-ready MVP plan  
**Status:** Revised planning baseline  
**Language:** English  
**Primary use:** Control document for later AI execution and review  

> This document is not part of the curated human-facing technical documentation surface. It is an execution-control artifact used to derive and constrain later implementation tasks. Precision, anti-drift structure, and verifiable acceptance take priority over prose elegance.

---

## 1. Executive judgment

This MVP is realistic as one bounded cleanup assignment.

It is broad, but it is still a normalization task rather than a product redesign. The repository already has enough architectural identity to support disciplined cleanup. The main problem is not absence of structure. The main problem is that current truth, old process sediment, weak path semantics, and historically encoded tests are mixed together in a way that makes the repository harder to understand and harder to maintain.

The MVP should score well only if it is executed with the following posture:

- cleanup is treated as a repository semantics task, not a cosmetic rewrite
- documentation claims are checked against repository truth rather than restyled in place
- test names are rewritten around behavior and contract, not merely shortened
- folder names and path layout are treated as part of the meaning system
- God of Carnage normalization is treated as a first-class structural concern
- path relocations are not performed before dependency mapping proves them safe

This MVP is **not** complete if later execution cleans only documentation, only tests, or only folders.

---

## 2. Objective and completion rule

### 2.1 Objective

Produce and later execute a cleanup that makes the repository structurally legible and technically trustworthy across five connected surfaces:

1. active technical documentation
2. truthfulness and precision of active documentation claims
3. readability and semantic naming of tests
4. folder and path taxonomy
5. module-content layout, especially God of Carnage and future multi-module coexistence

### 2.2 Hard completion rule

This MVP is complete only when all five surfaces are addressed together.

Later execution may refine migration order, but it may not substitute one surface for another. A result that improves naming while leaving claim truth unchecked, or that rewrites docs while leaving path semantics misleading, does not satisfy this plan.

### 2.3 Out of scope

- product feature expansion
- core runtime redesign
- speculative runtime changes unrelated to cleanup
- preservation of obsolete plans, gates, audits, or closure artifacts in a new visible archive tree
- broad rewrites of already healthy code or already healthy docs
- creation of a new process bureaucracy

---

## 3. Current-state diagnosis

This section captures the planning baseline. Later execution must verify exact file-level facts before moving or removing anything.

### 3.1 Confirmed planning inputs

The following issues are explicit and should be treated as confirmed planning inputs:

- the active documentation surface is too process-heavy and too AI-shaped for its intended long-term role
- old gate, closure, audit, and plan artifacts should not simply be moved into a new archive tree
- active documentation claims must be checked for truth, precision, and completeness, not merely rewritten stylistically
- tests contain opaque names derived from area, task, workstream, final, closure, and similar historical labels
- test internals also contain historical naming residue
- some test suites are mixed aggregations and cannot be fixed by renaming alone
- folder structure does not clearly separate generic structures, templates, concrete module content, fixtures, reports, and generated artifacts
- God of Carnage content currently appears to sit under a path such as `models`, which is semantically weak and does not clearly distinguish module truth from generic structures or templates
- the current layout does not visibly scale to additional modules beside God of Carnage

### 3.2 Repository-level implications

The repository is known to contain at least the following major surfaces:

- `backend/`
- `world-engine/`
- `frontend/`
- `administration-tool/`
- `writers-room/`
- `docs/`
- `tests/`

The project also already has meaningful architectural truths that the cleanup must preserve and make easier to see:

- the World-Engine is the authoritative live runtime
- AI does not independently own committed story truth
- published content is intended to be the primary path where that distinction exists
- builtin or fallback content exists in at least some flows
- God of Carnage is the current canonical proving-ground module

### 3.3 Core diagnosis

The repository problem is not only naming noise. It is a meaning-system problem.

Current technical truth is likely mixed with:

- historical process artifacts
- generated or evidentiary outputs
- generic structures
- concrete module content
- test fixtures
- weak or overloaded path names
- documentation claims that are partly true, historically true, too absolute, or too vague

That mixture makes the repository appear fuller while making it harder for humans and later AI executors to understand what is actually authoritative.

### 3.4 Preview diagnosis for God of Carnage normalization

God of Carnage is not just a naming cleanup concern. It is a structural scaling concern.

Current likely condition:

- God of Carnage content appears under a semantically overloaded path such as `models`
- the path does not clearly say whether the files are generic models, templates, concrete GoC content, fixtures, or runtime-consumed truth
- future modules would not have an obvious neighboring namespace
- loader code may currently depend on existing path assumptions

This makes GoC relocation the highest technical-risk area in the plan.

**Mandatory implication:** later implementation must begin GoC normalization with a loader-dependency mapping pass before any relocation, renaming, or path cleanup affecting GoC content.

---

## 4. Classification model

Nothing should be renamed, moved, rewritten, or removed before it is classified.

### 4.1 Documentation classes

- **Durable technical truth** — current architecture, responsibilities, boundaries, contracts, runtime flows, or module structure
- **Operational runbook** — active instructions for running, debugging, validating, or troubleshooting the system
- **Contract/interface document** — request/response shapes, lifecycle rules, schema constraints, ownership boundaries
- **Module-specific technical document** — technical explanation for a concrete module
- **Temporary process artifact** — old plans, gates, closure reports, audits, convergence writeups, acceptance writeups
- **Evidence/generated artifact** — generated reports, run outputs, proof artifacts, environment residue

### 4.2 Technical-claim truth classes

Each material claim in active technical docs must be classified as one of the following:

- **Confirmed** — materially supported by repository evidence
- **Partially confirmed** — core idea is true, but wording is too broad, too narrow, too vague, or incomplete
- **Outdated/contradicted** — current repository state disagrees with the claim
- **Unverifiable** — claim cannot be justified from code, config, tests, structure, or service boundaries
- **Missing but necessary** — a developer needs the truth, but active docs do not currently state it

### 4.3 Test classes

- **Unit behavior test** — proves a specific behavior under a specific condition
- **Component contract test** — proves a component boundary, contract, or invariant
- **Integration test** — spans multiple components or layers
- **Cross-system acceptance gate** — explicit named check for a real cross-system flow or contract
- **Historical aggregation suite** — mixed or legacy suite organized by project-history lineage rather than technical subject

### 4.4 Path and content classes

- **Active technical documentation path**
- **Operational path**
- **Report/evidence path**
- **Generated artifact path**
- **Generic schema/model path**
- **Template path**
- **Concrete module-content path**
- **Fixture path**
- **Published/canonical content path**, if such a category exists in-repo
- **Builtin/fallback/demo content path**, if such a category exists in-repo

### 4.5 Source-of-truth map principles

Later execution must produce an explicit source-of-truth map for the affected surfaces.

At minimum:

- active technical docs must live only in the curated docs surface
- process artifacts must not masquerade as active technical truth
- generic schemas/models must not be confused with concrete module content
- templates must not be confused with concrete module truth
- fixtures must not be confused with runtime-consumed truth
- reports/generated outputs must not be confused with documentation
- if published and builtin paths both exist, they must remain visibly distinct

---

## 5. Target-state principles

The target state is defined by semantics, not by one forced directory diagram. Later execution may adapt path shapes to actual repository reality, but the following semantic rules are mandatory.

### 5.1 Active documentation

The active docs surface must describe the current system, not the history of how previous tasks evaluated it.

It should center on:

- system overview
- component responsibilities
- authority boundaries
- contracts and interfaces
- main request/runtime flows
- module publishing and consumption
- operational assumptions and failure modes
- world-engine runtime flows
- ai decision tree runtime-flows
- ai integrated architecture
- mcp and external connection
- user experienced behavior
- user management
- session management
- story driven runtime flow
- story decision runtime flow

Old process artifacts may be mined for durable truth, but they must not remain visible as if they were current architectural authority.

### 5.2 Tests

A test path and file name must communicate subject matter before the file is opened.

A test function name should communicate:

- the system part
- the condition
- the expected behavior or contract

Allowed naming uses concrete technical concepts. Disallowed active naming uses historical labels such as `area`, `task`, `workstream`, `phase`, `final`, `closure`, or `convergence`, unless one of those is proven to be a current technical concept rather than project history.

### 5.3 Paths and folders

Folder structure must visibly separate the following categories wherever they exist:

- curated docs
- process/evidence artifacts
- generated outputs
- generic schemas/models
- templates
- concrete module content
- fixtures
- published/canonical content
- builtin/fallback/demo content

### 5.4 Module namespace

Concrete modules must have first-class structural boundaries.

Mandatory semantic result:

- God of Carnage is unmistakably a concrete module
- future modules can coexist beside it
- generic structures are not stored in the same category as module truth unless the distinction is explicit
- templates are visibly distinct from module truth
- fixtures are visibly distinct from module truth

### 5.5 Truth handling

No active technical claim survives solely because it already exists.

Every material claim retained in the curated docs surface must be confirmed, narrowed, corrected, removed, or supplemented based on repository evidence.

---

## 6. Workstreams

Use the workstreams below as the single control structure for later implementation. Do not introduce a second parallel stage model.

### Workstream A — Repository inventory and truth map

**Purpose:** establish repository-grounded classification before any cleanup action.

**Required actions:**

- inventory documentation-like files, report-like files, generated outputs, module-content candidates, template candidates, fixture candidates, and opaque test suites
- classify each relevant item using the model in Section 4
- produce an explicit source-of-truth map for docs, schemas/models, templates, module content, fixtures, reports, generated outputs, and published/builtin content where present
- identify all material active-doc claims that require truth classification

**Required outputs:**

- inventory matrix
- truth-map matrix
- claim-audit candidate list
- opaque-test inventory
- GoC path and ownership inventory

**Gate A:**

Later execution may not rename, relocate, rewrite, or remove anything before the inventory and truth map exist.

### Workstream B — Active documentation and claim correction

**Purpose:** replace process-heavy active docs with current technical truth and correct active claims.

**Required actions:**

- identify the curated active docs surface
- identify obsolete process artifacts currently occupying that surface
- extract durable technical truth from old process materials where needed
- rewrite or replace active docs around current architecture, boundaries, contracts, flows, and operational assumptions
- classify each material retained claim as confirmed, partially confirmed, outdated/contradicted, unverifiable, or missing but necessary
- narrow, expand, correct, remove, or supplement claims accordingly
- remove obsolete process artifacts from the active surface rather than moving them into a new visible archive tree

**Writing rule for this workstream:**

This plan document itself is AI-control-oriented. The curated docs surface created by later implementation is human-oriented. Those are different roles and must not be conflated.

**Required outputs:**

- rewritten/normalized active docs surface
- claim-audit log or cleanup report section describing corrected, narrowed, removed, and added claims
- list of obsolete documents removed from the active surface

**Gate B:**

No document may remain in the curated active docs surface if its main purpose is historical process tracking rather than current technical explanation.

For this gate, a document is a removal candidate when its primary useful content is historical execution/process context whose practical value does not depend on being stated as current technical truth and could instead be inferred from code, tests, git history, or superseding technical documents.

### Workstream C — Test suite normalization

**Purpose:** replace historically encoded test naming with behavior- and contract-oriented test structure.

**Required actions:**

- inventory active test files with opaque or historical naming
- classify each affected test file as unit behavior, component contract, integration, cross-system acceptance gate, or historical aggregation suite
- rename files to technical subject names
- split mixed suites where one file covers multiple unrelated concerns
- rename internal test functions, fixtures, helpers, comments, and local identifiers that still expose historical plan lineage
- preserve gate-style naming only where the file is a real cross-system acceptance gate and the name states the actual technical gate
- repair imports, pytest discovery, CI references, and documentation references affected by renames or splits

**Disallowed active naming patterns:**

- `area*`
- `task*`
- `workstream*`
- `phase*`
- `final*`
- `closure*`
- `convergence*`

This prohibition applies to active affected test filenames and to newly touched internal test naming unless the repository proves one of these terms is a current technical domain concept.

**Required outputs:**

- renamed and, where necessary, split test files
- normalized internal naming in affected tests
- reference repair for discovery and CI
- a mapping from old test file names to new technical names

**Gate C:**

A file rename alone is insufficient where the file is still a mixed historical aggregation suite.

### Workstream D — Folder and path taxonomy normalization

**Purpose:** make folder structure itself communicate category, ownership, and meaning.

**Required actions:**

- identify semantically overloaded paths such as `models`, `docs`, `reports`, or any path currently mixing incompatible categories
- define the target path semantics actually supported by repository reality
- separate curated docs from reports/evidence artifacts and generated outputs
- separate generic schemas/models from templates, concrete modules, and fixtures
- make published vs builtin/fallback distinctions visible where those categories exist
- update path references, loader references, docs links, config assumptions, and tests after any approved relocation

**Required outputs:**

- path taxonomy decision record
- normalized path layout for the affected areas
- reference repair list

**Gate D:**

No path relocation is allowed if the target category remains semantically ambiguous after the move.

### Workstream E — God of Carnage module normalization

**Purpose:** make God of Carnage a first-class module namespace and remove ambiguity between GoC truth, generic structures, templates, fixtures, and fallback content.

**Mandatory Step E0 — Loader dependency mapping before any movement:**

Before any GoC content relocation, later execution must map every code path, loader, config, registry, import, test, and document assumption that currently depends on the existing GoC path layout.

This is the highest technical-risk step in the plan.

**Required actions after E0 is complete:**

- determine whether current GoC placement under `models` or equivalent is semantically misleading
- define the future-proof module namespace for GoC and neighboring modules
- distinguish generic schema/model content from GoC-specific content
- distinguish template material from GoC-specific content
- distinguish fixture/demo/fallback content from GoC truth
- distinguish published/canonical vs builtin/fallback content if both exist in-repo
- relocate GoC material only after dependency mapping proves the relocation set and reference repair scope
- add a small module-structure explanation document if needed to make the new layout self-explanatory

**Required outputs:**

- GoC dependency map
- GoC normalization decision record
- normalized GoC module namespace
- repaired loaders/imports/tests/docs/config references

**Gate E:**

No GoC relocation may begin before the dependency map exists and identifies all affected consumers.

---

## 7. Single execution sequence

Use this sequence for later implementation. Do not create a second independent stage system.

### Step 0 — Risk map first

Execute Workstream A inventory.

Within that workstream, treat GoC loader-dependency mapping as a blocker for all GoC path changes. If the dependency map is incomplete, GoC relocation remains blocked.

### Step 1 — Freeze the active-surface candidate set

From the inventory, determine:

- which docs are candidates for the curated active docs surface
- which docs are process artifacts
- which files are reports/evidence/generated outputs
- which test files are active cleanup targets
- which paths are semantically overloaded

### Step 2 — Build the truth map

Create the source-of-truth map and classify material documentation claims.

This step must explicitly answer, for each affected surface, what it is and what it must not be confused with.

### Step 3 — Clean the docs surface

Execute Workstream B.

Order of action:

1. extract durable truth from old process material where needed
2. rewrite/replace active docs around current technical truth
3. correct/narrow/remove/supplement claims
4. remove obsolete process artifacts from the active surface

### Step 4 — Normalize tests

Execute Workstream C.

Order of action:

1. classify affected test files
2. split historical aggregation suites where required
3. rename files and internal symbols
4. repair imports, discovery, CI references, and docs references

### Step 5 — Normalize folder and path taxonomy

Execute Workstream D for the non-GoC affected areas.

Do not use this step to perform speculative global reshuffling. Limit changes to paths whose current semantics materially obstruct repository legibility.

### Step 6 — Normalize GoC module layout

Execute Workstream E only after Step 0 dependency mapping is complete.

The order inside Workstream E is:

1. prove current path consumers
2. define final category boundaries
3. relocate only the approved GoC set
4. repair all references
5. validate loader and runtime assumptions

### Step 7 — Remove residue

Delete dead active-surface process artifacts, obsolete historical test files replaced by normalized equivalents, and any path residue left behind by approved relocations.

Do not leave duplicate truth in place.

### Step 8 — Validate and record evidence

Run the validation set in Section 8 and produce the required cleanup report and mapping artifacts.

---

## 8. Validation and acceptance

Validation must prove both technical integrity and cleanup intent.

### 8.1 Technical validation

Later execution must run the affected test suites and any relevant repository checks after renames, splits, moves, and document cleanup.

At minimum validate:

- pytest discovery still works in the affected areas
- imports and loader paths still resolve
- CI or local commands that rely on renamed tests still function
- docs links and path references remain valid where applicable
- GoC loaders and runtime consumers still resolve the normalized content layout

### 8.2 Readability and semantics acceptance

The cleanup is acceptable only if all of the following are true:

- a developer can infer the purpose of an affected test file from its path and filename
- active docs can be read without knowing old gates, tasks, workstreams, or closure history
- active docs no longer present stale or overstated claims as current truth
- path structure materially distinguishes docs, reports, generated outputs, schemas/models, templates, module content, fixtures, and fallback/canonical content where those categories exist
- God of Carnage is visibly a module rather than an ambiguous bucket of files under a generic label

### 8.3 Machine-readable acceptance checks for tests

At least one acceptance check must be executable rather than interpretive.

#### Check T1 — no historical naming residue in active test filenames

Run:

```bash
git ls-files | grep -E '(^|/)(tests|[^/]+/tests)/.*test_.*(area[0-9]+|task[0-9]+|workstream|phase[0-9]+|final|closure|convergence).*\.py$'
```

Expected result:

- no output for active test files after cleanup

If output remains, later execution must either rename those files or document a narrow repository-grounded exception.

#### Check T2 — no historical naming residue in newly touched active test internals

Run:

```bash
git grep -nE 'def test_(area|task|workstream|phase|final|closure|convergence)|\b(area|task|workstream|phase|final|closure|convergence)_(fixture|env|case|payload|input)\b' -- ':(glob)**/tests/**/*.py'
```

Expected result:

- no output in the affected active test surface after cleanup

Narrow exceptions are allowed only if the word is part of an actual current technical concept rather than historical task lineage.

### 8.4 Documentation truth acceptance

Later execution must produce evidence that material active-doc claims were reviewed and dispositioned.

Minimum acceptable evidence:

- claim list with truth classifications
- list of corrected/narrowed/removed/supplemented claims
- explanation of any intentionally retained strong claims and their evidence basis

### 8.5 GoC normalization acceptance

GoC normalization is acceptable only if all of the following are true:

- a dependency map was produced before relocation
- final GoC location clearly represents a module namespace
- generic structures, templates, fixtures, and fallback content are not confused with GoC truth
- all path consumers affected by the relocation were repaired
- relevant loaders/tests still work after normalization

---

## 9. Risks, constraints, and anti-failure rules

### 9.1 Main risks

- hidden loader/path assumptions tied to current GoC placement
- stale CI or tooling references to renamed tests
- old docs still linked from current docs or scripts
- over-cleaning a historically named file that still encodes a current technical gate
- accidental conflation of generic templates with module truth during relocation
- duplicate truth left behind after partial migration

### 9.2 Constraints

- repository truth outranks prior wording
- cleanup must remain bounded
- healthy code and healthy docs should not be rewritten without cause
- path moves must be justified by semantic clarity, not aesthetic preference
- GoC relocation is blocked by unresolved dependency ambiguity

### 9.3 Anti-failure rules

Later execution is insufficient if it does any of the following:

- rewrites docs without auditing truth claims
- renames test files without splitting mixed historical aggregation suites where needed
- moves obsolete process artifacts into a visible archive tree instead of removing them from the active surface
- relocates GoC content before mapping loaders and path consumers
- claims template/module/fixture separation without making that distinction visible in structure
- keeps semantically overloaded paths such as `models` unchanged while merely documenting around them
- preserves duplicate truth in old and new locations

---

## 10. Deliverables and required evidence

Later execution must produce all of the following.

### 10.1 Repository deliverables

- normalized active docs surface
- claim-audit evidence for active docs
- normalized affected tests
- normalized affected path taxonomy
- normalized God of Carnage module namespace
- repaired references, discovery, imports, config assumptions, and docs links

### 10.2 Reporting deliverables

A single concise cleanup report must record:

- which obsolete docs were removed from the active surface
- which durable truths were migrated into current docs
- which material claims were corrected, narrowed, removed, or added
- which test files were renamed
- which test suites were split
- which paths were normalized
- which GoC dependencies were mapped before relocation
- any intentionally retained exceptions and why

### 10.3 Mapping deliverables

- old-to-new test filename mapping
- source-of-truth map
- GoC dependency map

---

## 11. Recommended execution assignment shape

Later implementation should be framed as one bounded assignment with five enforced workstreams and explicit gates.

### Suggested workstream order

1. Workstream A — inventory and truth map
2. Workstream B — docs and claim correction
3. Workstream C — test normalization
4. Workstream D — path taxonomy normalization
5. Workstream E — GoC normalization, gated by dependency mapping

### Suggested closure condition

The assignment is complete only when:

- all five workstreams have delivered their required outputs
- all workstream gates have been satisfied
- the machine-readable test acceptance checks pass or have narrow documented exceptions
- the claim-audit evidence exists
- GoC relocation, if performed, was preceded by dependency mapping and followed by successful repair and validation

### Minimum evidence pack

- cleanup report
- source-of-truth map
- claim-audit list
- old-to-new test mapping
- GoC dependency map
- exact validation commands and results

---

## 12. Final implementation guidance

This plan should be executed conservatively and concretely.

The later implementer should prefer the following verbs over vague improvement language.

Overarching rule: **classify before doing anything else**. The list below is not an execution priority list except for that rule.

- classify
- narrow
- correct
- remove
- replace
- split
- rename
- relocate
- separate
- repair
- validate

The later implementer must not use cleanup language to hide uncertainty. Where ambiguity exists, it should be turned into an explicit inspection or decision point inside the workstream rather than hand-waved.

The repository should end this MVP with fewer ambiguous paths, fewer historical test relics, fewer stale documents, and a much clearer distinction between active technical truth and everything else.
