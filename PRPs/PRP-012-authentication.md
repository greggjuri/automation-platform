# PRP-012: Authentication with Read-Only Public Access

> **Status:** Complete
> **Created:** 2025-12-19
> **Author:** Claude
> **Priority:** P1 (High)

---

## Overview

### Problem Statement
The automation platform is publicly hosted at automations.jurigregg.com but has no authentication. Anyone can create, edit, delete workflows and access secrets. This is a security risk for a production-exposed API.

### Proposed Solution
Implement AWS Cognito authentication with a "read-only public" strategy:
- **Public access:** Visitors can view workflows and execution history without logging in
- **Protected access:** Create, edit, delete, run, and secrets operations require JWT authentication
- Adapt existing auth patterns from Golf Ghost examples in `examples/auth/`

### Out of Scope
- Multi-user registration (single admin user for MVP)
- Role-based access control (admin-only for now)
- OAuth social login providers
- Password reset via email (use AWS Console if needed)

---

## Success Criteria

- [ ] Cognito User Pool and App Client created via setup script
- [ ] Admin user created and can log in
- [ ] API Gateway routes protected with Cognito JWT authorizer
- [ ] Public routes (GET workflows, executions) work without auth
- [ ] Protected routes return 401 without valid token
- [ ] Frontend shows Login/Logout in header
- [ ] Login page with glass styling matches app theme
- [ ] Authenticated users see Create/Edit/Delete/Run buttons
- [ ] Unauthenticated users see read-only view
- [ ] Secrets page requires authentication to access
- [ ] Auth tokens refresh automatically

**Definition of Done:**
- All success criteria met
- Manual end-to-end testing complete
- Documentation updated
- Deployed to production

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Lists auth strategy as open question (line 317)
- `INITIAL/INITIAL-012-authentication.md` - Detailed implementation guide

### Related Code
- `examples/auth/` - Golf Ghost auth implementation (reference patterns)
- `frontend/src/api/client.ts` - Axios client needs auth headers
- `frontend/src/main.tsx` - Wrap app with AuthProvider
- `frontend/src/App.tsx` - Add login route, protect secrets
- `frontend/src/components/layout/Header.tsx` - Add Login/Logout buttons

### Dependencies
- **Requires:** Nothing - can be implemented independently
- **Blocks:** Public launch of the platform

### Assumptions
1. Single admin user is sufficient for MVP
2. AWS Cognito is acceptable (vs. Auth0, Firebase Auth)
3. JWT tokens in localStorage is acceptable security trade-off
4. Read-only public access is desirable (showcase portfolio)

---

## Technical Specification

### Access Control Matrix

| Method | Path | Auth Required |
|--------|------|---------------|
| GET | /health | No |
| GET | /workflows | No |
| GET | /workflows/{id} | No |
| GET | /workflows/{id}/executions | No |
| GET | /workflows/{id}/executions/{eid} | No |
| POST | /webhook/{workflow_id} | No |
| POST | /workflows | **Yes** |
| PUT | /workflows/{id} | **Yes** |
| DELETE | /workflows/{id} | **Yes** |
| PATCH | /workflows/{id}/enabled | **Yes** |
| POST | /workflows/{id}/execute | **Yes** |
| GET | /secrets | **Yes** |
| POST | /secrets | **Yes** |
| DELETE | /secrets/{name} | **Yes** |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    COGNITO USER POOL                        │
│                 automation-platform-users                   │
│                                                             │
│  ┌─────────────┐    ┌─────────────────────────────────┐    │
│  │  Admin User │    │  App Client (no secret)          │    │
│  │  juri@...   │    │  automation-platform-web         │    │
│  └─────────────┘    └─────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ JWT Token
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   API GATEWAY HTTP API                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           COGNITO JWT AUTHORIZER                      │   │
│  │  (attached to protected routes only)                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Public Routes:          Protected Routes:                   │
│  GET /workflows          POST /workflows                     │
│  GET /workflows/{id}     PUT /workflows/{id}                │
│  GET /executions         DELETE /workflows/{id}              │
│  POST /webhook/*         POST /execute, GET/POST/DEL secrets │
└─────────────────────────────────────────────────────────────┘
```

### Frontend Auth Flow

```
┌────────────┐    ┌────────────┐    ┌────────────┐
│   App.tsx  │───▶│ AuthProvider│───▶│  useAuth   │
└────────────┘    └────────────┘    └────────────┘
                        │                  │
                        ▼                  ▼
                  ┌──────────┐      ┌────────────┐
                  │ Cognito  │      │ isAuthenticated
                  │   SDK    │      │ user
                  └──────────┘      │ login()
                                    │ logout()
                                    └────────────┘
```

### Environment Variables

```bash
# frontend/.env.local
VITE_API_URL=https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com
VITE_COGNITO_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXX
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Implementation Steps

### Phase 1: AWS Infrastructure (Scripts)

#### Step 1.1: Create Cognito Setup Script
**Files:** `scripts/setup-cognito.sh`
**Description:** Adapt Golf Ghost script to create Cognito User Pool and App Client.

Changes from example:
- Pool name: `automation-platform-users`
- Client name: `automation-platform-web`
- Output Pool ID and Client ID for `.env.local`

**Validation:** Script outputs User Pool ID and Client ID

#### Step 1.2: Create Admin User Script
**Files:** `scripts/create-admin-user.sh`
**Description:** Script to create admin user in Cognito.

Usage: `./scripts/create-admin-user.sh your@email.com`

**Validation:** Email received with temporary password

#### Step 1.3: Create Cognito Authorizer Script
**Files:** `scripts/setup-cognito-authorizer.sh`
**Description:** Attach JWT authorizer to protected API Gateway routes.

Protected routes to configure:
- POST /workflows
- PUT /workflows/{workflow_id}
- DELETE /workflows/{workflow_id}
- PATCH /workflows/{workflow_id}/enabled
- POST /workflows/{workflow_id}/execute
- GET /secrets
- POST /secrets
- DELETE /secrets/{name}

**Validation:** `curl -X POST /workflows` returns 401

### Phase 2: Frontend Auth Library

#### Step 2.1: Install Cognito SDK
**Files:** `frontend/package.json`
**Description:** Add amazon-cognito-identity-js dependency.

```bash
cd frontend && npm install amazon-cognito-identity-js
```

**Validation:** Package installed, no errors

#### Step 2.2: Create Auth Config
**Files:** `frontend/src/lib/auth/config.ts`
**Description:** Cognito configuration with Vite env vars.

```typescript
export interface CognitoConfig {
  region: string;
  userPoolId: string;
  clientId: string;
}

export const cognitoConfig: CognitoConfig = {
  region: import.meta.env.VITE_COGNITO_REGION || 'us-east-1',
  userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
  clientId: import.meta.env.VITE_COGNITO_CLIENT_ID || '',
};
```

**Validation:** TypeScript compiles

#### Step 2.3: Create Cognito Wrapper
**Files:** `frontend/src/lib/auth/cognito.ts`
**Description:** Wrap Cognito SDK with typed functions.

Functions:
- `signIn(email, password)` - Returns tokens or NEW_PASSWORD_REQUIRED
- `completeNewPassword(email, oldPassword, newPassword)` - First login flow
- `signOut()` - Clear session
- `getCurrentUser()` - Get authenticated user
- `getAccessToken()` - Get JWT for API calls
- `refreshSession()` - Refresh tokens

**Validation:** Functions exported correctly

#### Step 2.4: Create Auth Context
**Files:** `frontend/src/lib/auth/AuthContext.tsx`
**Description:** React context for auth state.

State:
- `isLoading: boolean`
- `isAuthenticated: boolean`
- `user: { email: string } | null`

Actions:
- `login(email, password)`
- `logout()`
- `completeNewPasswordChallenge(newPassword)`

**Validation:** Context renders without error

#### Step 2.5: Create useAuth Hook
**Files:** `frontend/src/lib/auth/useAuth.ts`
**Description:** Convenience hook to access auth context.

**Validation:** Hook returns auth state

#### Step 2.6: Export Auth Library
**Files:** `frontend/src/lib/auth/index.ts`
**Description:** Re-export all auth utilities.

**Validation:** Can import from `./lib/auth`

### Phase 3: Frontend Integration

#### Step 3.1: Add AuthProvider to App
**Files:** `frontend/src/main.tsx`
**Description:** Wrap app with AuthProvider.

```typescript
import { AuthProvider } from './lib/auth';

<AuthProvider>
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </QueryClientProvider>
</AuthProvider>
```

**Validation:** App renders with AuthProvider

#### Step 3.2: Create Login Page
**Files:** `frontend/src/pages/LoginPage.tsx`
**Description:** Login form with glass styling.

Features:
- Email/password form
- Loading state during login
- Error display
- New password challenge handling (first login)
- Redirect to /workflows on success
- Glass card styling matching app theme

**Validation:** Can log in with valid credentials

#### Step 3.3: Add Login Route
**Files:** `frontend/src/App.tsx`
**Description:** Add /login route.

```typescript
import { LoginPage } from './pages';

<Route path="/login" element={<LoginPage />} />
```

**Validation:** /login page renders

#### Step 3.4: Create ProtectedRoute Component
**Files:** `frontend/src/components/auth/ProtectedRoute.tsx`
**Description:** HOC to protect routes that require auth.

```typescript
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return <>{children}</>;
}
```

**Validation:** Unauthenticated users redirected to /login

#### Step 3.5: Protect Secrets Route
**Files:** `frontend/src/App.tsx`
**Description:** Wrap SecretsPage with ProtectedRoute.

```typescript
<Route path="/secrets" element={
  <ProtectedRoute>
    <SecretsPage />
  </ProtectedRoute>
} />
```

**Validation:** /secrets redirects to /login when not authenticated

#### Step 3.6: Add Auth Headers to API Client
**Files:** `frontend/src/api/client.ts`
**Description:** Add request interceptor to include JWT token.

```typescript
import { getAccessToken } from '../lib/auth';

apiClient.interceptors.request.use(async (config) => {
  const token = await getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

**Validation:** Protected API calls include Authorization header

#### Step 3.7: Update Header with Login/Logout
**Files:** `frontend/src/components/layout/Header.tsx`
**Description:** Show Login link or user email + Logout button.

When not authenticated:
- Show "Login" link

When authenticated:
- Show user email
- Show "Logout" button

**Validation:** Header shows correct auth state

#### Step 3.8: Conditional UI in WorkflowsPage
**Files:** `frontend/src/pages/WorkflowsPage.tsx`
**Description:** Show/hide "Create Workflow" button based on auth.

```typescript
const { isAuthenticated } = useAuth();

{isAuthenticated && (
  <Link to="/workflows/new">
    <Button>Create Workflow</Button>
  </Link>
)}
```

**Validation:** Create button only visible when authenticated

#### Step 3.9: Conditional UI in WorkflowDetailPage
**Files:** `frontend/src/pages/WorkflowDetailPage.tsx`
**Description:** Show/hide Edit, Delete, Run, Toggle based on auth.

Buttons to conditionally render:
- Edit button
- Delete button
- Run Now button
- Enable/Disable toggle

**Validation:** Action buttons only visible when authenticated

#### Step 3.10: Export Login Page
**Files:** `frontend/src/pages/index.ts`
**Description:** Export LoginPage from pages index.

**Validation:** Can import LoginPage

### Phase 4: Environment & Documentation

#### Step 4.1: Update .env.example
**Files:** `frontend/.env.example`
**Description:** Add Cognito env vars to example file.

```bash
VITE_API_URL=https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com
VITE_COGNITO_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=
VITE_COGNITO_CLIENT_ID=
```

**Validation:** File updated

#### Step 4.2: Update TASK.md
**Files:** `docs/TASK.md`
**Description:** Add authentication task and examples cleanup task.

Add to backlog:
- [ ] Authentication (PRP-012)
- [ ] Clean up examples/auth files after implementation (delete or add to .gitignore)

**Validation:** TASK.md updated

---

## Testing Requirements

### Manual Testing Checklist

1. **Setup Scripts:**
   - [ ] `setup-cognito.sh` creates pool and outputs IDs
   - [ ] `create-admin-user.sh` sends email with temp password
   - [ ] `setup-cognito-authorizer.sh` attaches authorizer

2. **API Protection:**
   - [ ] `curl GET /workflows` - works without auth
   - [ ] `curl POST /workflows` - returns 401 without auth
   - [ ] `curl POST /workflows` with valid JWT - works

3. **Frontend Auth Flow:**
   - [ ] Visit site without logging in - can view workflows
   - [ ] Create/Edit/Delete buttons not visible
   - [ ] Navigate to /secrets - redirected to /login
   - [ ] Log in with temp password - prompted for new password
   - [ ] Set new password - logged in successfully
   - [ ] Buttons now visible, can manage workflows
   - [ ] Log out - back to read-only mode

4. **Token Refresh:**
   - [ ] Stay logged in > 1 hour - session still works

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| 401 Unauthorized | Missing/invalid token | Redirect to login |
| NotAuthorizedException | Wrong password | Show error message |
| UserNotFoundException | Email not in pool | Show error message |
| NewPasswordRequired | First login | Show password change form |

### Edge Cases
1. **Token expired during request:** Intercept 401, refresh token, retry once
2. **User logs out in another tab:** Detect on next API call, redirect to login
3. **Cognito service unavailable:** Show friendly error, allow retry

### Rollback Plan
1. Remove Cognito authorizer from API Gateway routes
2. All routes become public again
3. No data migration needed

---

## Security Considerations

- [x] No secrets in frontend code (env vars only)
- [x] JWT tokens validated server-side by Cognito
- [x] HTTPS only (API Gateway default)
- [x] App Client has no secret (public client)
- [ ] Consider adding CAPTCHA for login if abuse detected
- [ ] Consider rate limiting login attempts

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Cognito | 1 user (free tier) | $0 |
| API Gateway | Authorizer calls | ~$0.01 |

**Total estimated monthly impact:** ~$0

---

## Open Questions

1. [x] **Password reset flow?** → Use AWS Console for MVP, can add email flow later
2. [x] **Token storage?** → localStorage via Cognito SDK (standard approach)
3. [ ] **Add examples/auth to .gitignore?** → Or delete after implementation - add to TASK.md

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | INITIAL-012 provides detailed implementation guide |
| Feasibility | 9 | Pattern proven in Golf Ghost, adapting to Vite |
| Completeness | 9 | Covers all auth flows and UI changes |
| Alignment | 10 | Uses AWS native service, $0 cost, answers PLANNING.md open question |
| **Overall** | **9.25** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-19 | Claude | Initial draft |
