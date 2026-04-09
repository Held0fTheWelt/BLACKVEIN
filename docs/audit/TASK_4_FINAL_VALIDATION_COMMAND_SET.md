# Task 4 — Final Validation Command Set

This command set validates Task 4 closure evidence and blocker enforcement.

## 1) GoC dependency sufficiency artifact presence

```bash
rg -n "NOT LIFTED|P0 dependency|Mandatory refusal rule" docs/audit/TASK_4_GOC_DEPENDENCY_SUFFICIENCY_RECORD.md
```

Pass condition:
- sufficiency record exists and states explicit blocker outcome and refusal logic.

## 2) Namespace pre/post classification and conflict rule

```bash
rg -n "Conflict-priority classification rule|runtime-consumed canonical GoC content|authoring-side GoC content" docs/audit/TASK_4_GOC_NAMESPACE_PRE_POST_MAP.md
```

Pass condition:
- conflict-priority rule and pre/post table are present.

## 3) Reference repair inventory and executed repairs

```bash
rg -n "Repair actions executed|RR-0|Deferred repairs" docs/audit/TASK_4_REFERENCE_REPAIR_INVENTORY.md
```

Pass condition:
- executed repairs and blocked/deferred classes are both explicit.

## 4) Cross-stack cohesion closure with tests-insufficient rule

```bash
rg -n "Passing tests are explicitly treated as insufficient|conditional|BLOCKED" docs/audit/TASK_4_CROSS_STACK_COHESION_CLOSURE_REPORT.md
```

Pass condition:
- report explicitly rejects tests-only closure and states seam-based result.

## 5) Residue criteria operationalization

```bash
rg -n "2-of-3|active-value omission test|durable-role displacement test|transitional/history logic test" docs/audit/TASK_4_RESIDUE_REMOVAL_REPORT.md
```

Pass condition:
- operational criteria and decisions are present.

## 6) Closure report and residual risk register presence

```bash
rg -n "Go/No-Go|no physical namespace move|Final decision" docs/audit/TASK_4_FINAL_CLEANUP_CLOSURE_REPORT.md
rg -n "Residual risk|Owner|Mitigation|Status" docs/audit/TASK_4_RESIDUAL_RISK_REGISTER.md
```

Pass condition:
- final closure outcome and residual-risk control entries are present.

