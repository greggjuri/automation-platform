# PRP-016: Claude AI Action Type

> **Status:** Complete
> **Created:** 2025-12-31
> **Author:** Claude
> **Priority:** P2 (Medium)

---

## Overview

### Problem Statement
The automation platform currently supports basic actions (HTTP requests, transforms, notifications), but lacks AI-powered capabilities. Users want to summarize content, analyze data, generate text, and make intelligent decisions within their workflows. A Claude AI action would differentiate this platform and enable compelling use cases like RSS-to-summary pipelines.

### Proposed Solution
Add a new `claude` action type that calls the Anthropic Claude API. The action accepts a prompt template with variable interpolation, sends it to Claude, and returns the AI-generated response for use in subsequent workflow steps.

### Out of Scope
- Streaming responses (unnecessary for automation)
- Vision/image input (future enhancement)
- Tool use/function calling (future enhancement)
- Conversation memory (each call is stateless)
- Model fine-tuning
- System prompts separate from user prompts (MVP uses single prompt)
- Temperature/top_p configuration (use defaults)

---

## Success Criteria

- [ ] Can add a Claude action step to a workflow via UI
- [ ] Claude action calls Anthropic API and returns response
- [ ] Response accessible via `{{steps.step_name.output.response}}`
- [ ] Token usage visible in execution details
- [ ] Large inputs truncated to prevent cost overruns
- [ ] Errors (missing API key, rate limits, invalid model) surfaced clearly in execution history
- [ ] Unit tests for all Lambda handler scenarios

**Definition of Done:**
- All success criteria met
- Tests written and passing (minimum 80% coverage)
- Code reviewed
- Documentation updated
- Deployed to dev/staging

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Action Types section lists "AI" as future enhancement (v0.2+)
- `docs/DECISIONS.md` - ADR-008 (aws-xray-sdk), ADR-009 (sequential loop pattern)
- `INITIAL/INITIAL-016-claude-action.md` - Original feature request with detailed specs

### Related Code
- `lambdas/action_notify/handler.py` - Similar action pattern (external API calls, error handling)
- `lambdas/shared/interpolation.py` - Variable substitution utility
- `cdk/stacks/execution_stack.py` - Where new action Lambda is added
- `frontend/src/components/WorkflowForm/steps/` - Step config component pattern
- `frontend/src/types/workflow.ts` - StepType and config interfaces

### Dependencies
- **Requires:** `anthropic` Python package (new dependency)
- **Requires:** Secrets management (PRP-009, complete) for API key storage
- **Blocks:** Nothing

### Assumptions
1. User has an Anthropic API key stored in SSM Parameter Store
2. Haiku model is sufficient for most use cases (cheap and fast)
3. Single prompt field (no separate system/user prompts) is acceptable for MVP
4. 4000 character default truncation limit is reasonable for inputs

---

## Technical Specification

### Data Models

```python
# Action Configuration
class ClaudeActionConfig(BaseModel):
    """Configuration for Claude AI action."""
    model: str = "claude-3-haiku-20240307"  # Default to cheap/fast model
    max_tokens: int = 500
    prompt: str  # Required: prompt template with {{variables}}
    api_key_secret: str = "anthropic_api_key"  # SSM secret name
    truncate_input: int = 4000  # Max chars for interpolated prompt

# Action Output
class ClaudeActionOutput(BaseModel):
    """Output from Claude AI action."""
    response: str  # The AI-generated text
    model: str  # Model actually used
    usage: dict  # {"input_tokens": N, "output_tokens": N}
    truncated: bool  # Whether input was truncated
```

### Supported Models

| Model | Model ID | Use Case |
|-------|----------|----------|
| Claude 3 Haiku | `claude-3-haiku-20240307` | Fast, cheap (default) |
| Claude 3.5 Sonnet | `claude-3-5-sonnet-20241022` | More capable |
| Claude 3.5 Haiku | `claude-3-5-haiku-20241022` | Newer fast model |

### API Changes

No new API endpoints. The action is executed within the existing Step Functions workflow.

### Architecture Diagram
```
StepFunctions (RouteByStepType)
    │
    ├── type == "claude"
    │       ↓
    │   ExecuteClaude Lambda
    │       │
    │       ├── Get API key from SSM
    │       ├── Interpolate prompt template
    │       ├── Truncate if over limit
    │       ├── Call Anthropic API
    │       └── Return {status, output, error, duration_ms}
    │
    └── (other action types...)
```

### Frontend Types

```typescript
// Add to StepType union
export type StepType = 'http_request' | 'transform' | 'log' | 'notify' | 'claude';

// Claude step config
export interface ClaudeConfig {
  model: 'claude-3-haiku-20240307' | 'claude-3-5-sonnet-20241022' | 'claude-3-5-haiku-20241022';
  max_tokens: number;
  prompt: string;
  api_key_secret?: string;
  truncate_input?: number;
}
```

---

## Implementation Steps

### Phase 1: Backend Lambda

#### Step 1.1: Create Claude Action Lambda
**Files:** `lambdas/action_claude/handler.py`, `lambdas/action_claude/requirements.txt`
**Description:** Create the Lambda function that calls the Anthropic API

```python
# lambdas/action_claude/handler.py
from anthropic import Anthropic
from shared.interpolation import interpolate, InterpolationError

ALLOWED_MODELS = [
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
]

def execute_claude(config: dict, context: dict) -> dict:
    """Execute Claude API call with interpolated prompt."""
    # 1. Get API key from context.secrets
    # 2. Interpolate prompt template
    # 3. Truncate if needed
    # 4. Call Anthropic API
    # 5. Return response with usage stats
```

```
# lambdas/action_claude/requirements.txt
aws-lambda-powertools>=2.0.0
anthropic>=0.39.0
aws-xray-sdk>=2.12.0
```

**Validation:** Lambda can be invoked locally with test event

#### Step 1.2: Add Lambda to CDK Execution Stack
**Files:** `cdk/stacks/execution_stack.py`
**Description:** Add Claude Lambda function and wire it into state machine

Changes:
1. Add `_create_action_lambdas()` entry for `action_claude`
2. Create `tasks.LambdaInvoke` for `ExecuteClaude`
3. Add `route_by_type.when(...)` for `type == "claude"`
4. Chain to `check_step_result`
5. Grant SSM read permission for API key secret

**Validation:** `cdk synth` succeeds, state machine definition includes claude route

### Phase 2: Frontend UI

#### Step 2.1: Add Claude Step Type
**Files:** `frontend/src/types/workflow.ts`
**Description:** Add `claude` to StepType union and ClaudeConfig interface

**Validation:** TypeScript compiles without errors

#### Step 2.2: Create ClaudeConfig Component
**Files:** `frontend/src/components/WorkflowForm/steps/ClaudeConfig.tsx`
**Description:** Form component for configuring Claude action

Fields:
- Model dropdown (3 options)
- Max tokens number input (default 500, max 4096)
- Prompt textarea with variable helper
- API key secret input (default "anthropic_api_key")
- Truncate limit input (optional, default 4000)

**Validation:** Component renders in StepEditor when type="claude"

#### Step 2.3: Wire Up StepEditor
**Files:**
- `frontend/src/components/WorkflowForm/StepEditor.tsx`
- `frontend/src/components/WorkflowForm/steps/index.ts`

**Description:** Add claude to STEP_TYPE_LABELS and renderConfig switch

**Validation:** Can create workflow with Claude step in UI

### Phase 3: Testing

#### Step 3.1: Unit Tests
**Files:** `lambdas/action_claude/tests/test_handler.py`
**Description:** Test all handler scenarios

Test cases:
- Successful API call with valid response
- Prompt interpolation with variables
- Input truncation when over limit
- Missing API key error
- Invalid model error
- Rate limit (429) handling
- API error (4xx/5xx) handling
- Timeout handling

**Validation:** `pytest lambdas/action_claude/tests/ --cov=. --cov-report=term-missing` shows 80%+ coverage

#### Step 3.2: Integration Test
**Files:** Manual testing procedure
**Description:** End-to-end workflow execution

1. Create workflow with poll trigger + claude action + notify action
2. Manually execute workflow
3. Verify execution completes successfully
4. Check execution details show Claude response and token usage

**Validation:** Full workflow executes without errors

---

## Testing Requirements

### Unit Tests
- [ ] `test_handler_success()` - Successful API call returns response with usage
- [ ] `test_interpolation()` - Variables substituted correctly in prompt
- [ ] `test_truncation()` - Long inputs truncated to limit with flag set
- [ ] `test_missing_api_key()` - Returns failed status with clear error
- [ ] `test_invalid_model()` - Returns failed status with model error
- [ ] `test_rate_limit()` - 429 response handled gracefully
- [ ] `test_api_error()` - 4xx/5xx handled with error message
- [ ] `test_timeout()` - Timeout returns failed status

### Integration Tests
- [ ] `test_claude_in_workflow()` - Claude step executes within Step Functions
- [ ] `test_context_accumulation()` - Claude output available in subsequent steps

### Manual Testing
1. Create workflow: Manual trigger -> Claude (summarize text) -> Log result
2. Execute workflow and verify:
   - Execution status: success
   - Step output contains response text
   - Token usage displayed in details
3. Test error cases:
   - Remove API key secret -> clear error message
   - Set invalid model -> clear error message

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| `API key not found` | Secret doesn't exist in SSM | Fail step with "API key not found in secrets. Add 'anthropic_api_key' to Secrets page." |
| `Invalid model` | Model ID not in allowed list | Fail step with "Invalid model: {model}. Use claude-3-haiku-20240307, claude-3-5-sonnet-20241022, or claude-3-5-haiku-20241022" |
| `Rate limited (429)` | Too many requests | Fail step with "Rate limited by Anthropic API. Try again later." |
| `API error (4xx)` | Bad request to Anthropic | Fail step with API error message |
| `API error (5xx)` | Anthropic server error | Fail step with "Anthropic API error. Try again later." |
| `Interpolation error` | Missing variable in context | Fail step with interpolation error message |
| `Timeout` | Lambda timeout (30s) | Fail step with "Request timed out" |

### Edge Cases
1. **Empty prompt after interpolation:** Return empty response (don't fail)
2. **Very long response:** Let Anthropic handle via max_tokens limit
3. **Non-ASCII characters in prompt:** Handle UTF-8 correctly
4. **Concurrent requests:** Each Lambda invocation is independent

### Rollback Plan
If deployment fails:
1. Run `cdk destroy AutomationExecutionStack` (only if partial deploy)
2. Redeploy previous version from git
3. State machine will route unknown types to SkipUnknown (graceful degradation)

---

## Performance Considerations

- **Expected latency:** 1-5 seconds (Haiku), 3-10 seconds (Sonnet)
- **Lambda timeout:** 30 seconds (sufficient for API call)
- **Memory:** 256 MB (same as other action Lambdas)
- **Cold start:** ~1s additional (acceptable)

---

## Security Considerations

- [x] API key stored in SSM Parameter Store (SecureString)
- [x] API key never logged or returned in output
- [x] Input validation: model must be in allowed list
- [x] Truncation prevents excessive API costs
- [x] Lambda role has minimal permissions (SSM read only for secrets path)

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Lambda | +N invocations | ~$0.01 (negligible) |
| Anthropic API | ~500 input + 100 output tokens/call | ~$0.00025/call |

**Usage estimate:** 10 calls/day = 300 calls/month
- Input: 150,000 tokens/month
- Output: 30,000 tokens/month
- **Anthropic cost:** ~$0.08/month (Haiku pricing)

**Total estimated monthly impact:** < $0.10 (well within budget)

---

## Open Questions

1. [x] **System prompts:** Not needed for MVP - single prompt field is sufficient
2. [x] **Temperature/top_p:** Use Anthropic defaults - not exposed in MVP
3. [x] **Truncation:** Per-action config with 4000 char default
4. [ ] **Future:** Should we cache API responses for identical prompts? (Not for MVP)

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements well-defined in INITIAL-016; clear config schema |
| Feasibility | 9 | Follows established action pattern; simple API integration |
| Completeness | 8 | All components covered; minor uncertainty on error message wording |
| Alignment | 9 | Listed in PLANNING.md roadmap; within budget; uses existing patterns |
| **Overall** | **8.75** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-31 | Claude | Initial draft |
