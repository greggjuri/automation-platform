# PRP-XXX: [Feature Title]

> **Status:** Draft | Ready | In Progress | Complete | Abandoned
> **Created:** YYYY-MM-DD
> **Author:** [Name]
> **Priority:** P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)

---

## Overview

### Problem Statement
[What problem does this solve? Why is it needed?]

### Proposed Solution
[High-level description of the solution]

### Out of Scope
[What this PRP explicitly does NOT cover]

---

## Success Criteria

- [ ] [Measurable outcome 1]
- [ ] [Measurable outcome 2]
- [ ] [Measurable outcome 3]

**Definition of Done:**
- All success criteria met
- Tests written and passing
- Code reviewed
- Documentation updated
- Deployed to dev/staging

---

## Context

### Related Documentation
- `docs/PLANNING.md` - [Relevant section]
- `docs/DECISIONS.md` - [Relevant ADRs]

### Related Code
- `path/to/related/file.py` - [Description of relation]
- `path/to/another/file.ts` - [Description of relation]

### Dependencies
- **Requires:** [Other PRPs, infrastructure, or features that must exist first]
- **Blocks:** [What is waiting on this PRP to complete]

### Assumptions
1. [Assumption about environment, data, or behavior]
2. [Another assumption]

---

## Technical Specification

### Data Models

```python
# Example model
class ExampleModel(BaseModel):
    id: str
    name: str
    created_at: datetime
```

### API Changes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /example | [Description] |
| POST | /example | [Description] |

### Architecture Diagram
```
[ASCII diagram showing component relationships]
```

### Configuration
```python
# Environment variables or config needed
EXAMPLE_CONFIG = "value"
```

---

## Implementation Steps

### Phase 1: [Phase Name]

#### Step 1.1: [Step Title]
**Files:** `path/to/file.py`
**Description:** [What this step accomplishes]

```python
# Key code snippet or pseudocode
```

**Validation:** [How to verify this step is complete]

#### Step 1.2: [Step Title]
**Files:** `path/to/another/file.py`
**Description:** [What this step accomplishes]

**Validation:** [How to verify this step is complete]

### Phase 2: [Phase Name]

#### Step 2.1: [Step Title]
...

---

## Testing Requirements

### Unit Tests
- [ ] `test_example_function()` - Tests [specific behavior]
- [ ] `test_edge_case()` - Tests [edge case]

### Integration Tests
- [ ] `test_api_endpoint()` - Tests [full API flow]
- [ ] `test_lambda_handler()` - Tests [Lambda with mocked dependencies]

### E2E Tests (if applicable)
- [ ] [User flow to test]

### Manual Testing
1. [Step to manually verify]
2. [Another step]

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| ValidationError | Invalid input | Return 400 with details |
| NotFoundError | Resource missing | Return 404 |

### Edge Cases
1. **[Edge case]:** [How it's handled]
2. **[Another edge case]:** [How it's handled]

### Rollback Plan
[How to undo changes if deployment fails]

---

## Performance Considerations

- **Expected latency:** [Target response time]
- **Expected throughput:** [Requests/sec]
- **Resource limits:** [Memory, timeout, connections]

---

## Security Considerations

- [ ] Input validation implemented
- [ ] No secrets in code
- [ ] Least privilege IAM
- [ ] [Other security concerns]

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Lambda | +X invocations | ~$Y |
| DynamoDB | +X RCUs/WCUs | ~$Y |

**Total estimated monthly impact:** $X

---

## Open Questions

1. [ ] [Question that needs answering before or during implementation]
2. [ ] [Another question]

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | X | [Brief explanation] |
| Feasibility | X | [Brief explanation] |
| Completeness | X | [Brief explanation] |
| Alignment | X | [Brief explanation] |
| **Overall** | **X.X** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| YYYY-MM-DD | [Name] | Initial draft |
