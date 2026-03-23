# API Consistency Analysis

# API Endpoint Analysis: News vs Wiki Suggested Threads

## 1. Consistency Analysis

### Current State Assessment

| Aspect | News Endpoint | Wiki Endpoint | Consistency Status |
|--------|--------------|---------------|-------------------|
| HTTP Method | GET | GET | ✅ Consistent |
| Endpoint Pattern | `/api/v1/news/<id>/suggested-threads` | `/api/v1/wiki/<id>/suggested-threads` | ✅ Consistent |
| Response Schema | `{items, total}` | `{items, total}` | ✅ Consistent |
| Versioning | v1 | v1 | ✅ Consistent |

### Potential Inconsistencies to Investigate

```
⚠️ Questions requiring validation:
├── Are `items` array structures identical?
│   ├── Item schema (fields, types)
│   ├── Item relationships (nested objects)
│   └── Item metadata (timestamps, IDs)
├── Are `total` semantics identical?
│   ├── Total count (all results vs. filtered)
│   ├── Pagination behavior
│   └── Max total limits
├── Query Parameters
│   ├── Available filters (date, category, etc.)
│   ├── Sorting options
│   └── Pagination params (page, limit, offset)
├── Authentication & Authorization
│   ├── Permission requirements
│   ├── Rate limiting rules
│   └── IP restrictions
└── Error Handling
    ├── HTTP status codes
    ├── Error response schema
    └── Error codes/messages
```

### Recommendation: Create Shared Schema Contract

```yaml
# Shared Response Schema (Draft)
SuggestedThreadsResponse:
  items:
    type: array
    items:
      type: object
      required: [id, title, type, url, created_at]
  total:
    type: integer
    minimum: 0
  pagination:
    type: object
    properties:
      page: integer
      limit: integer
      has_more: boolean
```

---

## 2. Breaking Changes Analysis

### Risk Assessment Matrix

| Change Type | Impact Level | Detection Method | Mitigation Strategy |
|-------------|-------------|------------------|-------------------|
| Response schema change | 🔴 Critical | Schema validation tests | Version bump, deprecation period |
| Endpoint path change | 🔴 Critical | Integration tests | Redirect with 301, maintain old endpoint |
| Query param removal | 🟠 High | Contract tests | Keep deprecated params, warn in docs |
| Field type change | 🟠 High | Type validation | Backward compatible changes |
| Error code change | 🟡 Medium | Error handling tests | Document changes, maintain old codes |
| Rate limit change | 🟡 Medium | Load testing | Communicate in changelog |

### Breaking Change Detection Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                    Breaking Change Detection            │
├─────────────────────────────────────────────────────────┤
│  1. Schema Diff Tool                                    │
│     ├── Compare v1 vs v2 response schemas              │
│     ├── Flag required field additions/removals         │
│     └── Flag type changes                              │
│                                                         │
│  2. Contract Tests                                      │
│     ├── Consumer-driven contracts (Pact)               │
│     ├── Backward compatibility tests                   │
│     └── Forward compatibility tests                    │
│                                                         │
│  3. Deprecation Workflow                                │
│     ├── Deprecation header (Deprecation: true)         │
│     ├── Sunset header (Sunset: <date>)                 │
│     └── 90-day minimum deprecation period              │
└─────────────────────────────────────────────────────────┘
```

### Migration Strategy

```
Timeline for Breaking Changes:
├── Phase 1: Deprecation Announcement (Day 0)
│   └── Add deprecation headers, update docs
│
├── Phase 2: Dual Support (Days 1-90)
│   ├── Old endpoint remains functional
│   ├── New endpoint available
│   └── Monitoring of old endpoint usage
│
├── Phase 3: Sunset (Day 91+)
│   ├── Return 410 Gone for old endpoint
│   └── Remove from documentation
│
└── Phase 4: Cleanup
    └── Remove old code, update all references
```

---

## 3. Postman Collection Updates

### Required Postman Updates

```
┌─────────────────────────────────────────────────────────┐
│                  Postman Collection Structure           │
├─────────────────────────────────────────────────────────┤
│  API Collection (v1)                                    │
│  ├── Environment Variables                             │
│  │   ├── BASE_URL (dev/staging/prod)                  │
│  │   ├── API_KEY / AUTH_TOKEN                          │
│  │   └── NEWS_ID / WIKI_ID (test data)                │
│  │                                                    │
│  ├── Folders                                           │
│  │   ├── News Endpoints                                │
│  │   │   └── Suggested Threads (GET)                   │
│  │   ├── Wiki Endpoints                                │
│  │   │   └── Suggested Threads (GET)                   │
│  │   └── Shared Tests                                  │
│  │       ├── Response Schema Validation                │
│       ├── Error Handling Tests                        │
│       └── Performance Tests                           │
│  │                                                    │
│  ├── Pre-request Scripts                               │
│  │   ├── Token refresh logic                           │
│  │   └── Dynamic ID injection                          │
│  │                                                    │
│  └── Tests                                             │
│      ├── Status code validation (200, 400, 401, 404)  │
│      ├── Response schema validation (JSON Schema)      │
│      ├── Response time checks (<500ms)                 │
│      └── Pagination validation                         │
└─────────────────────────────────────────────────────────┘
```

### Postman Update Checklist

| Update Item | Priority | Action Required |
|-------------|----------|-----------------|
| Environment variables | 🔴 High | Add/verify NEWS_ID, WIKI_ID |
| Collection version | 🔴 High | Update to v1.1 (or new version) |
| Test scripts | 🟠 High | Add schema validation tests |
| Documentation | 🟠 High | Update endpoint descriptions |
| Example requests | 🟡 Medium | Add realistic test data |
| Mock servers | 🟡 Medium | Set up for offline testing |

### Schema Validation Test Script (Postman)

```javascript
// Postman test script for response validation
pm.test("Response schema is valid", function() {
    var schema = {
        "type": "object",
        "required": ["items", "total"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "title", "type"]
                }
            },
            "total": {
                "type": "integer",
                "minimum": 0
            }
        }
    };
    
    pm.response.to.have.jsonSchema(schema);
});

pm.test("Items array is not empty", function() {
    var jsonData = pm.response.json();
    pm.expect(jsonData.items).to.be.an('array');
    pm.expect(jsonData.items.length).to.be.greaterThan(0);
});

pm.test("Total matches items count", function() {
    var jsonData = pm.response.json();
    pm.expect(jsonData.total).to.equal(jsonData.items.length);
});
```

---

## 4. Design Decisions & Recommendations

### Architectural Considerations

```
┌─────────────────────────────────────────────────────────┐
│                    Architecture Options                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Option A: Separate Services (Current)                  │
│  ├── News Service → /news/*                            │
│  ├── Wiki Service → /wiki/*                            │
│  └── Pros: Isolation, independent scaling               │
│  └── Cons: Duplication, consistency challenges         │
│                                                         │
│  Option B: Unified Content Service                      │
│  ├── Content Service → /content/{type}/{id}/...        │
│  └── Pros: Single source of truth, easier maintenance  │
│  └── Cons: More complex routing, tighter coupling      │
│                                                         │
│  Option C: Shared Library Pattern                       │
│  ├── Common service layer for both endpoints           │
│  ├── News-specific logic in News module                │
│  ├── Wiki-specific logic in Wiki module                │
│  └── Pros: Balance of consistency and separation       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Recommended Design Decisions

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| **Endpoint Structure** | ✅ Keep separate endpoints | Clearer ownership, independent evolution |
| **Response Schema** | 📋 Standardize via shared contract | Ensures consistency, easier testing |
| **Versioning** | 🔢 Use URL versioning (v1, v2) | Clear, explicit, backward compatible |
| **Documentation** | 📚 OpenAPI/Swagger spec | Auto-generate Postman collections |
| **Testing** | 🧪 Consumer-driven contracts | Prevent breaking changes |
| **Caching** | ⚡ Implement at API gateway | Reduce load, improve performance |

### Implementation Roadmap

```
Phase 1: Standardization (Week 1-2)
├── Create shared response schema
├── Update both endpoints to use shared schema
├── Add deprecation warnings for inconsistencies
└── Update Postman collection with validation tests

Phase 2: Documentation (Week 3)
├── Generate OpenAPI spec from endpoints
├── Auto-generate Postman collection from spec
├── Update API documentation
└── Add endpoint comparison matrix

Phase 3: Testing Infrastructure (Week 4)
├── Implement contract tests (Pact)
├── Set up CI/CD breaking change detection
├── Add performance benchmarks
└── Create regression test suite

Phase 4: Monitoring (Week 5)
├── Add endpoint usage metrics
├── Monitor response time differences
├── Track error rates per endpoint
└── Set up alerts for inconsistencies
```

---

## 5. Critical Dependencies & Risk Mitigation

### Dependency Map

```
┌─────────────────────────────────────────────────────────┐
│                    Dependency Analysis                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  External Dependencies                                  │
│  ├── Database (News DB vs Wiki DB)                     │
│  ├── Authentication Service                            │
│  ├── Rate Limiting Service                             │
│  └── Caching Layer (Redis/Memcached)                   │
│                                                         │
│  Internal Dependencies                                  │
│  ├── Shared Schema Registry                            │
│  ├── API Gateway                                       │
│  ├── Logging/Monitoring Service                        │
│  └── CI/CD Pipeline                                    │
│                                                         │
│  Critical Path                                          │
│  1. Schema validation → 2. Endpoint execution →        │
│  3. Response serialization → 4. Caching →              │
│  5. Client consumption                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Risk Mitigation Strategies

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Schema drift between endpoints | Medium | High | Automated schema validation |
| Breaking change in production | Low | Critical | Feature flags, gradual rollout |
| Postman collection outdated | High | Medium | Auto-generation from OpenAPI |
| Performance degradation | Medium | Medium | Load testing, monitoring |
| Authentication inconsistency | Low | High | Centralized auth service |

---

## Summary & Action Items

### Immediate Actions (This Sprint)

1. **Schema Audit**: Verify `items` structure is identical across both endpoints
2. **Postman Update**: Add schema validation tests to collection
3. **Documentation**: Create comparison matrix in API docs
4. **Contract Tests**: Implement basic consumer-driven contracts

### Short-term Actions (Next Sprint)

1. **OpenAPI Spec**: Generate from endpoints, auto-update Postman
2. **Deprecation Headers**: Add for any inconsistencies found
3. **Monitoring**: Set up endpoint comparison dashboards

### Long-term Actions (Q2)

1. **Shared Library**: Evaluate Option C architecture
2. **Breaking Change Pipeline**: Full CI/CD integration
3. **Version Strategy**: Define v2 migration path if needed

### Key Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Response schema consistency | 100% | Automated validation |
| Postman collection freshness | <1 day from change | Version tracking |
| Breaking change detection | 100% | CI/CD pipeline |
| API documentation accuracy | 100% | Auto-generated from spec |

---

**Final Recommendation**: Maintain separate endpoints for News and Wiki but enforce strict schema consistency through shared contracts and automated testing. This balances service isolation with API consistency while minimizing breaking change risks.