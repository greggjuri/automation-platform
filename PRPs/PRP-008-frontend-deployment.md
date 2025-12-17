# PRP-008: Frontend BucketDeployment Fix

> **Status:** Ready
> **Created:** 2025-12-17
> **Author:** Claude
> **Priority:** P1 (High)

---

## Overview

### Problem Statement
The `frontend_stack.py` creates S3 bucket, CloudFront distribution, and Route 53 DNS record but does NOT upload frontend files. This means `cdk deploy` requires a separate manual `aws s3 sync` step to actually deploy frontend changes.

Currently:
- ✅ Creates S3 bucket
- ✅ Creates CloudFront distribution
- ✅ Creates Route 53 DNS record
- ❌ Does NOT upload `frontend/dist/` files
- ❌ Does NOT invalidate CloudFront cache on deploy

### Proposed Solution
Add `BucketDeployment` construct to `frontend_stack.py` that:
1. Uploads `frontend/dist/` to S3 bucket on every `cdk deploy`
2. Automatically invalidates CloudFront distribution after upload

### Out of Scope
- GitHub Actions CI/CD pipeline
- Multiple environment deployments
- Build step automation (manual `npm run build` still required)

---

## Success Criteria

- [ ] `cdk deploy dev-automation-frontend` uploads new frontend build
- [ ] CloudFront automatically invalidated (no manual invalidation needed)
- [ ] Site reflects changes within 1-2 minutes of deploy
- [ ] "New Workflow" button visible at https://automations.jurigregg.com/workflows

**Definition of Done:**
- BucketDeployment added to frontend_stack.py
- Tested with fresh frontend build
- Changes visible on production site

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Frontend hosting architecture
- `INITIAL/INITIAL-008-frontend-deployment.md` - Original requirements

### Related Code
- `cdk/stacks/frontend_stack.py` - Stack to modify
- `frontend/dist/` - Build output to deploy

### Dependencies
- **Requires:** Frontend build exists (`npm run build`)
- **Blocks:** None

### Assumptions
1. `frontend/dist/` directory exists from prior build
2. Path `../frontend/dist` is relative to CDK directory
3. AWS credentials have S3 and CloudFront permissions

---

## Technical Specification

### Changes to frontend_stack.py

Add import:
```python
from aws_cdk import aws_s3_deployment as s3_deployment
```

Add BucketDeployment after distribution creation:
```python
# Deploy frontend assets
s3_deployment.BucketDeployment(
    self,
    "DeployFrontend",
    sources=[s3_deployment.Source.asset("../frontend/dist")],
    destination_bucket=self.bucket,
    distribution=self.distribution,
    distribution_paths=["/*"],
)
```

### How BucketDeployment Works
- Creates a Lambda function behind the scenes
- Uploads assets to S3 during CloudFormation deployment
- Triggers CloudFront invalidation for specified paths
- `distribution_paths=["/*"]` ensures full cache invalidation

---

## Implementation Steps

### Phase 1: Add BucketDeployment

#### Step 1.1: Update frontend_stack.py
**Files:** `cdk/stacks/frontend_stack.py`
**Description:** Add s3_deployment import and BucketDeployment construct

**Validation:** `cdk synth` succeeds

---

## Testing Requirements

### Manual Testing
1. Build frontend: `cd frontend && npm run build`
2. Deploy: `cd cdk && cdk deploy dev-automation-frontend`
3. Verify S3 has files: `aws s3 ls s3://dev-automation-frontend-{account}/`
4. Visit https://automations.jurigregg.com/workflows
5. Verify "New Workflow" button appears
6. Verify no manual cache invalidation needed

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| `frontend/dist` not found | Build not run | Run `npm run build` first |
| S3 access denied | IAM permissions | Check CDK role permissions |

### Edge Cases
1. **Empty dist folder:** CDK will fail - ensure build runs first
2. **Large files:** BucketDeployment handles files up to 128MB by default

---

## Performance Considerations

- BucketDeployment Lambda adds ~30-60s to deployment
- Full cache invalidation (`/*`) may take 1-2 minutes
- Subsequent deploys only upload changed files

---

## Security Considerations

- [x] No secrets in deployed files
- [x] S3 bucket blocks public access (OAC handles access)
- [x] HTTPS enforced via CloudFront

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Lambda | BucketDeployment Lambda | ~$0.01 (minimal invocations) |
| CloudFront Invalidations | Full invalidation on deploy | First 1000/month free |

**Total estimated monthly impact:** ~$0 (negligible)

---

## Open Questions

None - implementation is straightforward.

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Exact code provided in INITIAL |
| Feasibility | 10 | Standard CDK pattern, well-documented |
| Completeness | 10 | Single file change, no edge cases |
| Alignment | 10 | Fixes existing gap in deployment |
| **Overall** | **10.0** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-17 | Claude | Initial draft |
