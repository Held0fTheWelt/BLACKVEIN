# Workstream B Checkpoint — Ready for Haiku Agent Delegation

**Date:** 2026-04-20
**Status:** Ready for delegation (5 tasks, detailed specifications complete)
**Predecessor:** Workstream A COMPLETE (54/54 tests passing)

---

## Workstream B Overview

**Goal:** Expose session tools without granting false authority. MCP (Model Context Protocol) surface provides safe, gated access to world-engine operations while maintaining runtime authority.

**Owner Components:**
- `tools/mcp_server/` — MCP registry and handlers
- `backend/app/mcp_client/` — Client integration
- `ai_stack/mcp_canonical_surface.py` — Tool specifications

**Key Principle:** MCP is a mirror/proxy. World-engine remains authoritative. Read tools return mirrors; execute tools delegate to world-engine.

---

## 5 Tasks for Haiku Agent

### Task 1: Define MCP Surface Contracts
**Deliverables:**
- `docs/contracts/mcp_surface_contract.md` — 5 tools: get, state, logs, diag, execute_turn
- `docs/contracts/mcp_authorization_contract.md` — 3 operating profiles: read_only, execute, admin
**Time:** ~30 minutes

### Task 2: Implement MCP Registry and Tool Handlers
**Deliverables:**
- `tools/mcp_server/registry.py` — MCPRegistry class for tool dispatch
- `tools/mcp_server/operating_profile.py` — Profile enforcement
- `tools/mcp_server/handlers.py` — 5 tool handlers
- `tools/mcp_server/tests/test_mcp_registry.py` — 4+ tests
**Time:** ~1 hour

### Task 3: Implement Backend MCP Client
**Deliverables:**
- `backend/app/mcp_client/client.py` — MCPClient class
- `backend/tests/mcp/test_mcp_client.py` — 3+ tests
**Time:** ~45 minutes

### Task 4: Implement AI Stack Canonical Surface
**Deliverables:**
- `ai_stack/mcp_canonical_surface.py` — Tool specs for AI
- `ai_stack/tests/test_mcp_canonical_surface.py` — 3+ tests
**Time:** ~45 minutes

### Task 5: Integration and MVP Validation
**Deliverables:**
- Integration test + MVP validation (37/37 still passing)
**Time:** ~30 minutes

---

## Success Criteria

- [ ] All 5 tasks complete with tests PASSING
- [ ] 4-5 commits made with law references
- [ ] MVP reference 37/37 still PASSING (zero regressions)
- [ ] Ready for Workstream C

---

## Resources

**Detailed Sub-Plan:** `.claude/plans/2026-04-20-mvp-workstream-b-mcp-surface.md` — Complete task specifications

**Predecessor:** Workstream A COMPLETE (world-engine + backend integration proven)

**Constitutional Laws:** Focus on Laws 1, 6, 7, 8 (authority, fail-closed, explicit errors)
