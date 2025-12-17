# INITIAL-008: Frontend BucketDeployment Fix

## Overview

The frontend stack creates S3 bucket and CloudFront distribution but never uploads frontend files. This means `cdk deploy` doesn't actually deploy the frontend - requires manual `aws s3 sync`.

## Problem

`frontend_stack.py` is missing `BucketDeployment` construct. Currently:
- ✅ Creates S3 bucket
- ✅ Creates CloudFront distribution
- ✅ Creates Route 53 DNS record
- ❌ Does NOT upload frontend/dist/ files
- ❌ Does NOT invalidate CloudFront cache on deploy

## Solution

Add `BucketDeployment` to `frontend_stack.py` that:
1. Uploads `frontend/dist/` to S3 bucket on every `cdk deploy`
2. Automatically invalidates CloudFront distribution after upload

## Implementation

```python
from aws_cdk import aws_s3_deployment as s3_deployment

# Add after self.distribution creation:
s3_deployment.BucketDeployment(
    self,
    "DeployFrontend",
    sources=[s3_deployment.Source.asset("../frontend/dist")],
    destination_bucket=self.bucket,
    distribution=self.distribution,
    distribution_paths=["/*"],
)
```

## Files to Modify

- `cdk/stacks/frontend_stack.py` - Add BucketDeployment construct

## Testing

1. Build frontend: `cd frontend && npm run build`
2. Deploy: `cd cdk && cdk deploy dev-automation-frontend`
3. Verify S3 has new files: `aws s3 ls s3://dev-automation-frontend-490004610151/`
4. Verify site updates without manual cache invalidation
5. Check "New Workflow" button appears at https://automations.jurigregg.com/workflows

## Notes

- Path `../frontend/dist` is relative to `cdk/` directory
- `distribution_paths=["/*"]` ensures full cache invalidation
- BucketDeployment creates a Lambda behind the scenes for the upload
- First deploy after this change will upload all files

## Success Criteria

- `cdk deploy dev-automation-frontend` uploads new frontend build
- CloudFront automatically invalidated (no manual invalidation needed)
- Site reflects changes within 1-2 minutes of deploy
