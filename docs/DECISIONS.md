# DECISIONS.md - Architecture Decision Records

> This document records significant architecture decisions.
> Check here before proposing alternatives to existing patterns.

---

## ADR-001: Use AWS CDK with Python

**Date:** 2025-01-XX  
**Status:** Accepted

### Context
Need to define and manage AWS infrastructure as code.

### Options Considered
1. **AWS CDK (Python)** - Type-safe, programmatic, good Python support
2. **Terraform** - Cloud-agnostic, large community, HCL syntax
3. **CloudFormation** - Native AWS, but verbose YAML/JSON
4. **Pulumi** - Similar to CDK, multi-cloud

### Decision
Use AWS CDK with Python.

### Rationale
- Python is the primary backend language, keeps everything consistent
- CDK provides higher-level constructs that reduce boilerplate
- Better IDE support and type checking than raw CloudFormation
- Easier to refactor and compose stacks
- Juri has Python expertise

### Consequences
- Team must learn CDK concepts (constructs, stacks, synthesis)
- Locked into AWS (acceptable for this project)
- CDK version updates may require code changes

---

## ADR-002: Use DynamoDB with Single-Table Design

**Date:** 2025-01-XX  
**Status:** Accepted

### Context
Need persistent storage for workflows, executions, and poll state.

### Options Considered
1. **DynamoDB** - Serverless, pay-per-request, fast
2. **RDS PostgreSQL** - Relational, complex queries, $15+/month minimum
3. **S3 + Athena** - Cheap storage, complex queries, high latency

### Decision
Use DynamoDB with on-demand capacity.

### Rationale
- Truly serverless with zero idle cost
- On-demand pricing fits low-volume personal use (~$1-2/month)
- Fast reads/writes for API responses
- Integrates well with Lambda and Step Functions
- Access patterns are known and limited (no ad-hoc queries needed)

### Consequences
- Must design access patterns upfront
- Complex queries require GSIs or application-side joins
- Learning curve for DynamoDB data modeling

---

## ADR-003: Use Step Functions Express for Workflow Execution

**Date:** 2025-01-XX  
**Status:** Accepted

### Context
Need to orchestrate multi-step workflows with error handling and logging.

### Options Considered
1. **Step Functions Express** - Cheap ($1/million), max 5 min, sync/async
2. **Step Functions Standard** - More expensive, max 1 year, durable
3. **Custom orchestration** - Lambda calling Lambda, manage state ourselves
4. **SQS-based chain** - Each step queues next, eventual consistency

### Decision
Use Step Functions Express workflows.

### Rationale
- Most workflows will complete in seconds/minutes
- Express is ~10x cheaper than Standard for short executions
- Built-in error handling, retries, and logging
- Visual debugging in AWS Console
- Can upgrade to Standard later if needed for long-running workflows

### Consequences
- 5-minute execution limit (sufficient for MVP actions)
- No built-in pause/resume (acceptable for personal use)
- Execution history not persisted beyond 90 days (we log to DynamoDB anyway)

---

## ADR-004: API Gateway HTTP API (not REST API)

**Date:** 2025-01-XX  
**Status:** Accepted

### Context
Need to expose API endpoints for frontend and webhooks.

### Options Considered
1. **HTTP API** - Simpler, cheaper, faster, supports JWT
2. **REST API** - More features (caching, WAF), more expensive
3. **Function URLs** - Simplest, but no routing/middleware

### Decision
Use HTTP API.

### Rationale
- ~70% cheaper than REST API
- Faster (lower latency)
- Sufficient features for this project
- Easy JWT integration if needed later
- Built-in CORS support

### Consequences
- No API caching (acceptable, most responses are dynamic)
- No usage plans/API keys built-in (can add Lambda authorizer)
- Some advanced features not available (not needed)

---

## ADR-005: React with TypeScript for Frontend

**Date:** 2025-01-XX  
**Status:** Accepted

### Context
Need a frontend for managing workflows and viewing executions.

### Options Considered
1. **React + TypeScript** - Mature, large ecosystem, type safety
2. **Vue 3** - Simpler, good DX
3. **Svelte** - Smaller bundle, less boilerplate
4. **Server-rendered (HTMX)** - Simple, but less interactive

### Decision
Use React with TypeScript, built with Vite.

### Rationale
- Juri has some React experience from existing projects
- Large ecosystem and component libraries
- TypeScript catches errors early
- Vite provides fast dev experience
- Easy to deploy as static site to S3/CloudFront

### Consequences
- Larger bundle than Svelte (acceptable)
- More boilerplate than Vue/Svelte
- Must maintain TypeScript types

---

## ADR-006: Powertools for AWS Lambda

**Date:** 2025-01-XX  
**Status:** Accepted

### Context
Lambda functions need logging, tracing, and metrics.

### Options Considered
1. **Powertools for AWS Lambda** - Official AWS, batteries-included
2. **Manual logging** - Print statements + CloudWatch
3. **Datadog/custom APM** - Powerful, but $$

### Decision
Use Powertools for AWS Lambda (Python).

### Rationale
- Structured logging out of the box
- X-Ray tracing integration
- API Gateway event parsing
- Idempotency utilities
- Well-documented, AWS-maintained
- Free

### Consequences
- Additional dependency in Lambdas
- Learning curve for Powertools conventions
- Slightly larger deployment package

---

## ADR-007: Form-Based Workflow Creation for MVP

**Date:** 2025-01-XX  
**Status:** Accepted

### Context
Users need to create workflows. Could be simple form or visual builder.

### Options Considered
1. **Form-based** - Simple dropdowns and inputs
2. **Visual node builder** - Drag-drop, like n8n
3. **YAML/JSON editor** - Technical, flexible

### Decision
Start with form-based creation for MVP.

### Rationale
- Much faster to implement
- Sufficient for simple linear workflows
- Visual builder is complex (weeks of work)
- Can add visual builder in v0.2+

### Consequences
- Limited to linear workflows initially
- Less intuitive than visual builder
- Will need migration path when visual builder added

---

## ADR-008: aws-xray-sdk as Explicit Lambda Dependency

**Date:** 2025-12-12
**Status:** Accepted

### Context
When using AWS Lambda Powertools Tracer, the Lambda function failed to deploy/run because `aws-xray-sdk` was not available in the Lambda runtime.

### Options Considered
1. **Add aws-xray-sdk to requirements.txt** - Explicit dependency bundled with Lambda
2. **Use Lambda Layer** - Powertools provides a layer with all dependencies
3. **Disable tracing** - Remove Tracer usage entirely

### Decision
Add `aws-xray-sdk>=2.0.0` explicitly to each Lambda's `requirements.txt`.

### Rationale
- Powertools Tracer requires aws-xray-sdk for X-Ray integration
- The sdk is NOT included in the Lambda Python runtime by default
- Bundling with the function ensures version control and works with CDK bundling
- Lambda Layer alternative adds complexity and layer version management

### Consequences
- Slightly larger Lambda deployment package
- Must remember to add aws-xray-sdk when using Powertools Tracer
- Added to CLAUDE.md Known Gotchas for future reference

---

## ADR-009: Sequential Step Functions Loop Pattern

**Date:** 2025-12-14
**Status:** Accepted

### Context
Workflow steps need to reference outputs from previous steps using variable interpolation like `{{steps.step_1.output.body}}`. The state machine must accumulate context as it processes each step sequentially.

### Options Considered
1. **Map state** - Process all steps in parallel/sequence, but each iteration is independent
2. **Sequential loop with Pass states** - Use step_index counter, loop back after each step
3. **Chained Lambda calls** - Each Lambda calls the next, passing context

### Decision
Use a sequential loop pattern with Pass states and intrinsic functions.

### Implementation
```
InitializeExecution (set step_index=0, total_steps)
    ↓
HasMoreSteps (Choice: step_index < total_steps?)
    ↓ yes
GetCurrentStep (ArrayGetItem to get current step)
    ↓
RouteByStepType (Choice: http_request/transform/log)
    ↓
ExecuteAction (Lambda task)
    ↓
CheckStepResult (Choice: failed? → StepFailed)
    ↓ success
UpdateContext (JsonMerge step output, MathAdd index)
    ↓
→ back to HasMoreSteps
```

Key intrinsic functions used:
- `States.ArrayLength` - Get total steps count
- `States.ArrayGetItem` - Get step at current index
- `States.JsonMerge` - Accumulate step outputs into context
- `States.MathAdd` - Increment step index

### Rationale
- Map state processes items independently, cannot accumulate context between iterations
- Sequential loop allows each step to access all previous step outputs
- Intrinsic functions avoid extra Lambda invocations for simple operations
- Choice-based fail-fast ensures step failures propagate to execution status

### Consequences
- More complex state machine definition than Map state
- Limited to intrinsic function capabilities for data manipulation
- Must pre-compute array length (Choice can't use intrinsic functions directly)
- Clear execution flow visible in Step Functions console

---

## Template for New Decisions

```markdown
## ADR-XXX: [Title]

**Date:** YYYY-MM-DD  
**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-XXX

### Context
[What is the issue that we're seeing that motivates this decision?]

### Options Considered
1. **Option A** - Brief description
2. **Option B** - Brief description

### Decision
[What is the change that we're proposing and/or doing?]

### Rationale
[Why is this decision being made? What factors weighed in?]

### Consequences
[What becomes easier or harder as a result of this decision?]
```
