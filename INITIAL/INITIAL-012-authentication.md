# INITIAL-012: Authentication with Read-Only Public Access

## Overview

Implement Cognito authentication for the automation platform with a "read-only public" strategy: visitors can view workflows and execution history, but create/edit/delete/run operations require authentication.

## Reference Files

Example files from Golf Ghost are in `examples/auth/`:
- `scripts/` — AWS setup scripts (adapt for this project)
- `src/lib/auth/` — Auth library (adapt env vars for Vite)
- `src/components/` — ProtectedRoute, Providers
- `src/app/login/page.tsx` — Login page (convert from Next.js to React Router)

## Access Control Design

### Public Routes (no auth)
| Method | Path | Purpose |
|--------|------|---------|
| GET | /workflows | List workflows |
| GET | /workflows/{id} | View workflow details |
| GET | /workflows/{id}/executions | View execution history |
| GET | /executions/{id} | View execution details |
| POST | /webhook/{workflow_id} | External webhook triggers |

### Protected Routes (require JWT)
| Method | Path | Purpose |
|--------|------|---------|
| POST | /workflows | Create workflow |
| PUT | /workflows/{id} | Update workflow |
| DELETE | /workflows/{id} | Delete workflow |
| PATCH | /workflows/{id}/enabled | Enable/disable workflow |
| POST | /workflows/{id}/run | Manual trigger |
| GET | /secrets | List secrets |
| POST | /secrets | Create secret |
| DELETE | /secrets/{name} | Delete secret |

## Implementation Tasks

### 1. Adapt Setup Scripts

Copy and modify scripts from `examples/auth/scripts/`:

**setup-cognito.sh**
- Change pool name: `automation-platform-users`
- Change client name: `automation-platform-web`
- Keep same region and account ID

**create-admin-user.sh**
- Change pool name reference
- Usage: `./scripts/create-admin-user.sh juri@example.com`

**setup-cognito-authorizer.sh**
- Change API name: `automation-platform-api`
- Change authorizer name: `automation-platform-cognito-auth`
- Change pool name: `automation-platform-users`
- Update protected routes list (see Protected Routes above)
- Update public routes verification list

**update-api-cors.sh** (if needed)
- Verify CORS allows Authorization header

### 2. Frontend Auth Library

Copy `examples/auth/src/lib/auth/` to `frontend/src/lib/auth/` with these changes:

**config.ts**
```typescript
// Change from NEXT_PUBLIC_ to VITE_
export const cognitoConfig: CognitoConfig = {
  region: import.meta.env.VITE_COGNITO_REGION || 'us-east-1',
  userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
  clientId: import.meta.env.VITE_COGNITO_CLIENT_ID || '',
};
```

**AuthContext.tsx**
- Remove `'use client'` directive (Next.js specific)
- Otherwise should work as-is

**cognito.ts**
- Should work as-is

**useAuth.ts** and **index.ts**
- Should work as-is

### 3. Install Dependency

```bash
cd frontend
npm install amazon-cognito-identity-js
```

### 4. Environment Variables

**frontend/.env.example**
```
VITE_API_URL=https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com
VITE_COGNITO_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=
VITE_COGNITO_CLIENT_ID=
```

**frontend/.env.local** (after running setup-cognito.sh)
```
VITE_API_URL=https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com
VITE_COGNITO_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXX
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 5. Auth Provider Setup

**frontend/src/main.tsx**
```typescript
import { AuthProvider } from './lib/auth';

// Wrap App with AuthProvider
root.render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>
);
```

### 6. Login Page (React Router version)

Create `frontend/src/pages/LoginPage.tsx`:
- Convert from Next.js (`useRouter`, `Link`) to React Router (`useNavigate`, `Link` from react-router-dom)
- Adapt styling to match automation platform theme (pure black background, silver text, glass effects)
- Redirect to `/` after successful login
- Show loading state while checking auth

### 7. Update Router

**frontend/src/App.tsx**
- Add `/login` route pointing to LoginPage
- No ProtectedRoute wrapper needed for pages (we're doing read-only public)

### 8. API Client Auth Headers

**frontend/src/lib/api.ts**

Add auth header helper:
```typescript
import { getAccessToken } from './auth';

async function getAuthHeaders(): Promise<HeadersInit> {
  const token = await getAccessToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}
```

Update mutation functions to include auth headers:
- `createWorkflow` — add auth headers
- `updateWorkflow` — add auth headers  
- `deleteWorkflow` — add auth headers
- `toggleWorkflowEnabled` — add auth headers
- `runWorkflow` — add auth headers
- `createSecret` — add auth headers
- `deleteSecret` — add auth headers
- `fetchSecrets` — add auth headers (secrets list is protected)

Read operations stay as-is (no auth needed).

### 9. Conditional UI Elements

Update components to show/hide actions based on auth state:

**WorkflowList.tsx**
- "Create Workflow" button: only show when authenticated

**WorkflowDetail.tsx**
- "Edit" button: only show when authenticated
- "Delete" button: only show when authenticated
- "Run Now" button: only show when authenticated
- Enable/disable toggle: only show when authenticated

**Navigation/Header**
- Show "Login" link when not authenticated
- Show "Logout" button + user email when authenticated

**SecretsPage.tsx**
- Redirect to login if not authenticated (entire page is protected)
- Or show "Login required to manage secrets" message

### 10. ProtectedRoute Component (for Secrets page)

Create `frontend/src/components/ProtectedRoute.tsx`:
```typescript
import { Navigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return <div>Loading...</div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
}
```

Wrap SecretsPage route with ProtectedRoute in App.tsx.

## Testing

### After setup-cognito.sh:
1. Note the User Pool ID and Client ID from output
2. Update frontend/.env.local

### After create-admin-user.sh:
1. Check email for temporary password
2. First login will require password change

### After setup-cognito-authorizer.sh:
```bash
# Test protected route without token (should return 401)
curl -X POST https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com/workflows \
  -H 'Content-Type: application/json' \
  -d '{"name":"Test"}'

# Test public route (should work)
curl https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com/workflows
```

### Frontend testing:
1. Visit site without logging in → can view workflows, executions
2. Create/Edit/Delete/Run buttons should not be visible
3. Navigate to /secrets → redirected to /login
4. Log in → buttons appear, can manage workflows
5. Log out → back to read-only mode

## Deployment Order

1. Run `./scripts/setup-cognito.sh` → get Pool ID and Client ID
2. Run `./scripts/create-admin-user.sh your@email.com`
3. Update `frontend/.env.local` with Cognito IDs
4. Run `./scripts/setup-cognito-authorizer.sh`
5. Deploy frontend: `cd cdk && cdk deploy AutomationFrontendStack`
6. Test end-to-end

## Files to Create/Modify

### New Files:
- `scripts/setup-cognito.sh`
- `scripts/create-admin-user.sh`
- `scripts/setup-cognito-authorizer.sh`
- `frontend/src/lib/auth/config.ts`
- `frontend/src/lib/auth/cognito.ts`
- `frontend/src/lib/auth/AuthContext.tsx`
- `frontend/src/lib/auth/useAuth.ts`
- `frontend/src/lib/auth/index.ts`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/components/ProtectedRoute.tsx`
- `frontend/.env.example` (update)

### Modified Files:
- `frontend/package.json` (add amazon-cognito-identity-js)
- `frontend/src/main.tsx` (wrap with AuthProvider)
- `frontend/src/App.tsx` (add /login route, protect /secrets)
- `frontend/src/lib/api.ts` (add auth headers to mutations)
- `frontend/src/pages/WorkflowList.tsx` (conditional Create button)
- `frontend/src/pages/WorkflowDetail.tsx` (conditional Edit/Delete/Run)
- `frontend/src/components/Header.tsx` or equivalent (Login/Logout)
- `frontend/src/pages/SecretsPage.tsx` (protect entire page)

## Notes

- The Golf Ghost login page uses GlassCard/GlassButton components — adapt to use automation platform's existing glass button styles
- Password change flow on first login is handled by cognito.ts
- Token refresh is handled automatically by amazon-cognito-identity-js
- Tokens are stored in localStorage by the Cognito SDK
