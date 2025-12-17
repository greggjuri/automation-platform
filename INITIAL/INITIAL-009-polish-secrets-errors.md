# Feature Request: Polish, Secrets UI, Error Handling

> **Status:** Split into PRPs
> - **PRP-009:** Secrets Management UI (full-stack feature)
> - **PRP-010:** Frontend Polish (styling + error handling)

## Overview
Three improvements to make the platform more polished and usable:
1. Update frontend styling to match jurigregg.com dark glass aesthetic
2. Add secrets management UI for Discord webhooks and other credentials
3. Improve error handling with user-friendly messages

## Split Rationale
The original request was split into two PRPs:
- **PRP-009** handles the full-stack secrets management feature independently (new API endpoints, Lambda changes, new frontend pages)
- **PRP-010** bundles the two frontend-only concerns: styling updates and error handling improvements

## Feature 1: Glass Button Styling + Dark Theme

### Reference Files
Copy these to the project for reference:
- `examples/glassbutton/button.css` - Original glass button demo
- `examples/glassbutton/button.html` - Button HTML structure
- `examples/jurigregg/main.css` - Full site CSS with dark-adapted glass buttons
- `examples/jurigregg/index.html` - Site structure

### Color Palette (from jurigregg.com)
```css
:root {
  --color-bg: #000000;           /* Pure black background */
  --color-silver: #c0c0c0;       /* Primary text */
  --color-silver-light: #e8e8e8; /* Highlighted/hover text */
  --color-keyword: #333333;      /* Subtle backgrounds, borders */
  --font-primary: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
  --anim-hover-time: 400ms;
  --anim-hover-ease: cubic-bezier(0.25, 1, 0.5, 1);
}
```

### Glass Button CSS (dark-adapted version)
```css
.button {
  --border-width: clamp(1px, 0.0625em, 4px);
  all: unset;
  cursor: pointer;
  position: relative;
  display: inline-block;
  background: linear-gradient(
    -75deg,
    rgba(255, 255, 255, 0.03),
    rgba(255, 255, 255, 0.12),
    rgba(255, 255, 255, 0.03)
  );
  border-radius: 999vw;
  box-shadow:
    inset 0 0.125em 0.125em rgba(255, 255, 255, 0.05),
    inset 0 -0.125em 0.125em rgba(255, 255, 255, 0.1),
    0 0.25em 0.125em -0.125em rgba(0, 0, 0, 0.5),
    0 0 0.1em 0.25em inset rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(clamp(1px, 0.125em, 4px));
  transition: all var(--anim-hover-time) var(--anim-hover-ease);
}

.button:hover {
  transform: scale(0.975);
  backdrop-filter: blur(0.01em);
  box-shadow:
    inset 0 0.125em 0.125em rgba(255, 255, 255, 0.05),
    inset 0 -0.125em 0.125em rgba(255, 255, 255, 0.15),
    0 0.15em 0.05em -0.1em rgba(0, 0, 0, 0.5),
    0 0 0.05em 0.1em inset rgba(255, 255, 255, 0.1);
}

.button span {
  display: block;
  font-family: var(--font-primary);
  letter-spacing: 0.05em;
  font-weight: 400;
  color: var(--color-silver-light);
  text-shadow: 0 0.05em 0.1em rgba(0, 0, 0, 0.5);
  padding-inline: 2em;
  padding-block: 1em;
  transition: all var(--anim-hover-time) var(--anim-hover-ease);
}

.button:hover span {
  color: #ffffff;
  text-shadow: 0.025em 0.025em 0.05em rgba(0, 0, 0, 0.6);
}
```

### Components to Update

#### Buttons
- [ ] Primary button: Full glass effect as shown above
- [ ] Secondary button: More subtle, maybe just border + backdrop blur
- [ ] Danger button (delete): Subtle red tint in the gradient
- [ ] Ghost button: Transparent with silver border

#### Cards (WorkflowCard, ExecutionCard)
- [ ] Background: `rgba(255, 255, 255, 0.03)` or `--color-keyword`
- [ ] Border: `1px solid rgba(255, 255, 255, 0.1)`
- [ ] Subtle backdrop blur
- [ ] Hover: slight brighten

#### Form Inputs
- [ ] Background: transparent or very subtle
- [ ] Border: `1px solid rgba(192, 192, 192, 0.3)`
- [ ] Focus: border brightens to `--color-silver`
- [ ] Text: `--color-silver-light`

#### Navigation/Header
- [ ] Clean minimal header
- [ ] Glass effect on any nav buttons

#### Status Badges
- [ ] Keep functional colors (green success, red failed, yellow running)
- [ ] Add subtle glass/blur effect
- [ ] Ensure contrast meets accessibility

### Typography Updates
- [ ] Import Inter font: `https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&display=swap`
- [ ] Body text: weight 400, color `--color-silver`
- [ ] Headers: weight 300 or 500
- [ ] Subtle letter-spacing adjustments

### Simplification Notes
Skip these complex effects from the reference:
- 3D rotation on button active state
- Animated conic gradient border (::after pseudo-element)
- Separate shadow container div
- Shine sweep animation (span::after)

Focus on:
- Core glass background gradient
- Backdrop blur
- Box-shadow layers
- Hover scale effect
- Color transitions

## Feature 2: Secrets Management UI

### Requirements
- New route: `/secrets` (or `/settings/secrets`)
- List, create, delete secrets stored in SSM Parameter Store
- Never expose full secret values to frontend

### API Endpoints

```
GET    /secrets           - List secret metadata
POST   /secrets           - Create new secret
DELETE /secrets/{name}    - Delete secret
```

#### GET /secrets Response
```json
{
  "secrets": [
    {
      "name": "discord_webhook",
      "type": "discord_webhook",
      "created_at": "2025-12-17T10:00:00Z",
      "masked_value": "****abcd"
    }
  ]
}
```

#### POST /secrets Request
```json
{
  "name": "discord_webhook",
  "value": "https://discord.com/api/webhooks/...",
  "type": "discord_webhook"
}
```

### Backend Implementation

#### API Lambda Updates
Add to `lambdas/api/handler.py`:
- `GET /secrets` - List parameters under `/automations/{env}/secrets/`
- `POST /secrets` - Create SecureString parameter
- `DELETE /secrets/{name}` - Delete parameter

#### IAM Permissions Needed
```python
# Add to API Lambda role
ssm:GetParametersByPath  # For listing (already have from execution_starter)
ssm:PutParameter         # For creating
ssm:DeleteParameter      # For deleting
```

#### SSM Storage
- Path: `/automations/dev/secrets/{name}`
- Type: SecureString (encrypted)
- Store type as tag or in name convention

### Frontend Implementation

#### SecretsPage Component
```
/secrets
├── Header with "Add Secret" button
├── List of SecretCard components
│   └── Shows: name, type icon, masked value, delete button
└── Empty state if no secrets
```

#### AddSecretModal Component
- Type dropdown: Discord Webhook, Slack Webhook, API Key, Custom
- Name input (auto-filled based on type, editable)
- Value input (password field)
- Validation based on type:
  - Discord: Must match `https://discord.com/api/webhooks/...`
  - Slack: Must match `https://hooks.slack.com/...`
  - API Key/Custom: Any non-empty string

#### React Query Hooks
```typescript
// hooks/useSecrets.ts
useSecrets()           // GET /secrets
useCreateSecret()      // POST /secrets
useDeleteSecret()      // DELETE /secrets/{name}
```

### Workflow Integration
After creating a secret, user can reference it in workflows:
- Notify action: Leave webhook_url empty, it uses `{{secrets.discord_webhook}}`
- HTTP action: Use `{{secrets.api_key}}` in headers

### Security Considerations
- API never returns full secret values
- Masked value shows last 4 chars only: `****abcd`
- Use SecureString type in SSM (KMS encrypted)
- Frontend never sees or handles actual secret values
- Delete requires confirmation modal

## Feature 3: Error Handling Improvements

### Toast Notification Enhancements
Already have react-hot-toast. Ensure consistent usage:

```typescript
// Centralized error handler
const handleApiError = (error: unknown, context: string) => {
  const message = getErrorMessage(error);
  toast.error(`${context}: ${message}`);
};

const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.message || error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Something went wrong';
};
```

### React Query Error Handling
```typescript
// In QueryClient config or individual queries
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      onError: (error) => handleApiError(error, 'Failed to load data'),
    },
    mutations: {
      onError: (error) => handleApiError(error, 'Operation failed'),
    },
  },
});
```

### Execution Error Display
On ExecutionDetail page for failed executions:
- [ ] Highlight which step failed (red border/background)
- [ ] Show error message prominently
- [ ] Add "Retry" button that calls POST /workflows/{id}/execute
- [ ] Retry uses same trigger_data if available

### Form Validation
In WorkflowForm:
- [ ] Required field indicators (asterisk or text)
- [ ] Inline error messages below invalid fields
- [ ] Cron expression validation with helpful feedback
- [ ] Prevent submit if validation fails

### Network Error Handling
- [ ] Show "Connection lost" toast on network errors
- [ ] Add retry mechanism for failed fetches
- [ ] Graceful degradation when API unavailable

## Success Criteria

1. **Styling**: Buttons and cards match jurigregg.com glass aesthetic on dark background
2. **Secrets**: Can add Discord webhook at /secrets, use as `{{secrets.discord_webhook}}` in Notify action
3. **Errors**: Failed execution shows clear error + retry button, all API errors show friendly toasts

## Out of Scope
- Full animation suite (3D tilt, conic borders, shine sweeps)
- Secret rotation or versioning
- External API validation (checking if Discord webhook is valid)
- Secrets in multiple environments (just dev for now)

## File Changes Expected

### New Files
- `frontend/src/pages/SecretsPage.tsx`
- `frontend/src/components/AddSecretModal.tsx`
- `frontend/src/components/SecretCard.tsx`
- `frontend/src/hooks/useSecrets.ts`
- `frontend/src/styles/glass-button.css` (or update existing CSS)

### Modified Files
- `frontend/src/App.tsx` - Add /secrets route
- `frontend/src/index.css` - Color variables, typography
- `frontend/src/components/*.tsx` - Apply new button/card styles
- `lambdas/api/handler.py` - Add secrets endpoints
- `cdk/stacks/api_stack.py` - Add IAM permissions for SSM write/delete

## Testing
- [ ] Visual: Buttons look correct on dark background
- [ ] Secrets: Create, list, delete secrets via UI
- [ ] Secrets: Use in Notify action, verify interpolation works
- [ ] Errors: Trigger API error, verify toast appears
- [ ] Errors: View failed execution, verify retry button works
