# PRP-010: Frontend Polish (Styling + Error Handling)

> **Status:** Ready
> **Created:** 2025-12-17
> **Author:** Claude
> **Priority:** P2 (Medium)

---

## Overview

### Problem Statement
The current frontend uses default Tailwind styling with a generic dark theme. It lacks the polished, professional appearance of jurigregg.com with its glass button aesthetic. Additionally, error handling is inconsistent - API errors don't always show user-friendly messages, and failed executions don't have a retry option.

### Proposed Solution
Two improvements bundled together (both frontend-focused):

1. **Glass Button Styling + Dark Theme:**
   - Update color palette to match jurigregg.com (pure black background, silver text)
   - Add glass button effect (gradient, backdrop blur, box shadows)
   - Update cards, inputs, and badges with subtle glass effects
   - Import Inter font for consistent typography

2. **Error Handling Improvements:**
   - Centralize API error handling with consistent toast messages
   - Add "Retry" button to failed executions
   - Highlight which step failed in ExecutionDetail
   - Add better form validation feedback in WorkflowForm

### Out of Scope
- Complex animations (3D tilt, conic gradient borders, shine sweeps)
- Backend error handling changes
- Loading skeleton states
- Accessibility audit (a11y) - keep functional but don't overhaul

---

## Success Criteria

### Styling
- [ ] Background is pure black (#000000)
- [ ] Text is silver (#c0c0c0) with light silver (#e8e8e8) for highlights
- [ ] Primary buttons have glass effect (gradient, blur, shadows)
- [ ] Cards have subtle glass effect and hover brightening
- [ ] Inputs have transparent background with silver borders
- [ ] Inter font is used for all text

### Error Handling
- [ ] API errors show user-friendly toast messages
- [ ] Network errors show "Connection lost" toast
- [ ] Failed executions show "Retry" button
- [ ] Failed step is highlighted with red border in ExecutionDetail
- [ ] Form validation shows inline errors below fields

**Definition of Done:**
- All success criteria met
- Visual comparison with jurigregg.com glass buttons
- Manual testing of error scenarios

---

## Context

### Related Documentation
- `INITIAL/INITIAL-009-polish-secrets-errors.md` - Original feature request with CSS specs
- `examples/glassbutton/` - Reference CSS and HTML for glass button effect
- `examples/jurigregg/` - Full site CSS with dark-adapted glass buttons

### Related Code
- `frontend/src/index.css` - Global styles and CSS variables
- `frontend/src/components/common/StatusBadge.tsx` - Status badge styling
- `frontend/src/components/workflows/WorkflowCard.tsx` - Card component
- `frontend/src/components/executions/ExecutionDetail.tsx` - Execution detail with steps
- `frontend/src/App.tsx` - QueryClient configuration
- `frontend/tailwind.config.js` - Tailwind theme customization

### Dependencies
- **Requires:** Existing frontend (Phase 1-3 complete)
- **Blocks:** None

### Assumptions
1. Using existing Tailwind + custom CSS approach (not switching to CSS-in-JS)
2. Glass effects work well on pure black background
3. Status badge functional colors (green/red/yellow) remain unchanged

---

## Technical Specification

### Design Tokens (CSS Variables)

```css
/* frontend/src/index.css */
:root {
  /* Colors */
  --color-bg: #000000;
  --color-silver: #c0c0c0;
  --color-silver-light: #e8e8e8;
  --color-keyword: #333333;

  /* Glass effect values */
  --glass-bg: linear-gradient(
    -75deg,
    rgba(255, 255, 255, 0.03),
    rgba(255, 255, 255, 0.12),
    rgba(255, 255, 255, 0.03)
  );
  --glass-border: rgba(255, 255, 255, 0.1);
  --glass-shadow:
    inset 0 0.125em 0.125em rgba(255, 255, 255, 0.05),
    inset 0 -0.125em 0.125em rgba(255, 255, 255, 0.1),
    0 0.25em 0.125em -0.125em rgba(0, 0, 0, 0.5);

  /* Animation */
  --anim-hover-time: 400ms;
  --anim-hover-ease: cubic-bezier(0.25, 1, 0.5, 1);

  /* Typography */
  --font-primary: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
}
```

### Component Style Updates

#### Buttons
```tsx
// Base glass button classes
const buttonBase = `
  relative inline-flex items-center justify-center
  px-6 py-3 rounded-full font-medium
  bg-[var(--glass-bg)] backdrop-blur-sm
  border border-[var(--glass-border)]
  shadow-[var(--glass-shadow)]
  text-[var(--color-silver-light)]
  transition-all duration-[var(--anim-hover-time)] ease-[var(--anim-hover-ease)]
  hover:scale-[0.975] hover:text-white
`;

// Variants
const buttonPrimary = `${buttonBase} ...`;
const buttonSecondary = `${buttonBase} bg-transparent border-[var(--color-silver)]`;
const buttonDanger = `${buttonBase} border-red-500/30 text-red-400 hover:text-red-300`;
const buttonGhost = `bg-transparent border border-[var(--color-silver)]/30 text-[var(--color-silver)]`;
```

#### Cards
```tsx
// Glass card classes
const cardBase = `
  bg-[rgba(255,255,255,0.03)] backdrop-blur-sm
  border border-[rgba(255,255,255,0.1)]
  rounded-lg p-6
  transition-all duration-300
  hover:bg-[rgba(255,255,255,0.05)] hover:border-[rgba(255,255,255,0.15)]
`;
```

#### Inputs
```tsx
// Glass input classes
const inputBase = `
  bg-transparent
  border border-[var(--color-silver)]/30 rounded-lg
  px-4 py-2 text-[var(--color-silver-light)]
  placeholder:text-[var(--color-silver)]/50
  focus:border-[var(--color-silver)] focus:outline-none
  transition-colors duration-200
`;
```

### Error Handling Architecture

```typescript
// frontend/src/utils/errorHandler.ts

import { toast } from 'react-hot-toast';
import axios from 'axios';

export function handleApiError(error: unknown, context: string): void {
  const message = getErrorMessage(error);
  toast.error(`${context}: ${message}`);
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    // Network error
    if (!error.response) {
      return 'Connection lost. Please check your network.';
    }
    // API error with message
    return error.response.data?.message || error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Something went wrong';
}
```

```typescript
// frontend/src/App.tsx - QueryClient configuration

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      onError: (error) => handleApiError(error, 'Operation failed'),
    },
  },
});
```

---

## Implementation Steps

### Phase 1: Design System Setup

#### Step 1.1: Add CSS Variables and Inter Font
**Files:** `frontend/src/index.css`, `frontend/index.html`
**Description:** Set up design tokens and import Inter font

```css
/* Add Google Font import */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

/* Update :root with new variables */
```

**Validation:** Page renders with Inter font, new background color

#### Step 1.2: Create Button Component Library
**Files:** `frontend/src/components/common/Button.tsx`
**Description:** Reusable Button component with glass effect variants

```tsx
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  // ... other props
}
```

**Validation:** Button component renders with glass effect

#### Step 1.3: Update Tailwind Config
**Files:** `frontend/tailwind.config.js`
**Description:** Extend theme with custom colors and font

```javascript
export default {
  theme: {
    extend: {
      colors: {
        silver: '#c0c0c0',
        'silver-light': '#e8e8e8',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
    },
  },
};
```

**Validation:** Tailwind classes work with new theme values

### Phase 2: Component Updates

#### Step 2.1: Update WorkflowCard
**Files:** `frontend/src/components/workflows/WorkflowCard.tsx`
**Description:** Apply glass card styling

**Validation:** Cards have glass effect, hover brightens

#### Step 2.2: Update ExecutionRow/ExecutionList
**Files:** `frontend/src/components/executions/ExecutionRow.tsx`
**Description:** Apply consistent card styling

**Validation:** Execution rows match card styling

#### Step 2.3: Update StatusBadge
**Files:** `frontend/src/components/common/StatusBadge.tsx`
**Description:** Add subtle backdrop blur, keep functional colors

**Validation:** Badges look polished but colors still readable

#### Step 2.4: Update Form Inputs
**Files:** `frontend/src/components/WorkflowForm/*.tsx`
**Description:** Apply glass input styling to all form fields

**Validation:** Inputs have transparent bg, silver borders

#### Step 2.5: Update Header/Layout
**Files:** `frontend/src/components/layout/Header.tsx`, `Layout.tsx`
**Description:** Update nav buttons, ensure black background

**Validation:** Header buttons have glass effect

#### Step 2.6: Replace Inline Buttons
**Files:** Multiple component files
**Description:** Replace inline button classes with Button component

**Validation:** All buttons use consistent styling

### Phase 3: Error Handling

#### Step 3.1: Create Error Handler Utility
**Files:** `frontend/src/utils/errorHandler.ts`
**Description:** Centralized error handling functions

**Validation:** Can import and use handleApiError

#### Step 3.2: Configure QueryClient Defaults
**Files:** `frontend/src/App.tsx`
**Description:** Add default error handling to mutations

**Validation:** Mutation errors show toast

#### Step 3.3: Add Retry Button to ExecutionDetail
**Files:** `frontend/src/components/executions/ExecutionDetail.tsx`
**Description:** Show "Retry" button for failed executions

```tsx
{execution.status === 'failed' && (
  <Button
    variant="primary"
    onClick={() => retryMutation.mutate()}
    disabled={retryMutation.isPending}
  >
    Retry Execution
  </Button>
)}
```

**Validation:** Button appears on failed executions, triggers new execution

#### Step 3.4: Highlight Failed Step
**Files:** `frontend/src/components/executions/ExecutionDetail.tsx`
**Description:** Add red border/background to failed step

**Validation:** Failed step visually distinct

#### Step 3.5: Improve Form Validation Feedback
**Files:** `frontend/src/components/WorkflowForm/WorkflowForm.tsx`
**Description:** Show inline errors below invalid fields

**Validation:** Validation errors appear below fields

### Phase 4: Final Polish

#### Step 4.1: Test All Components Visually
**Description:** Review all pages, ensure consistent styling

**Validation:** Visual consistency across app

#### Step 4.2: Test Error Scenarios
**Description:** Test API errors, network errors, form validation

**Validation:** All error scenarios show appropriate feedback

---

## Testing Requirements

### Unit Tests
- [ ] Button component renders all variants
- [ ] handleApiError extracts correct messages
- [ ] getErrorMessage handles all error types

### Manual Testing
1. **Styling:**
   - [ ] View workflow list - cards have glass effect
   - [ ] View execution detail - consistent styling
   - [ ] Fill out workflow form - inputs look correct
   - [ ] Hover buttons - scale animation works

2. **Error Handling:**
   - [ ] Disconnect network - shows "Connection lost" toast
   - [ ] Create invalid workflow - shows validation errors
   - [ ] View failed execution - shows retry button
   - [ ] Click retry - triggers new execution

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| Network error | No connection | "Connection lost" toast |
| API 400 | Validation error | Show API message |
| API 404 | Resource not found | Show "not found" toast |
| API 500 | Server error | "Something went wrong" toast |

### Edge Cases
1. **Very long error message:** Truncate in toast
2. **Multiple rapid errors:** Toast queue handles stacking
3. **Retry while pending:** Button disabled during retry

---

## Performance Considerations

- **Glass effects:** backdrop-filter can be expensive on low-end devices
- **Mitigation:** Keep blur values small (blur-sm), avoid stacking many glass elements
- **Font loading:** Use `display=swap` to avoid FOUT

---

## Security Considerations

- [x] No sensitive data exposed in error messages
- [x] No XSS vectors in error display

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| CloudFront | Slightly larger CSS | ~$0 |
| Google Fonts | External request | ~$0 |

**Total estimated monthly impact:** $0

---

## Open Questions

1. [x] Should we use CSS-in-JS instead of Tailwind? **Decision:** No, keep current approach
2. [x] Should error toasts auto-dismiss? **Decision:** Yes, keep react-hot-toast defaults
3. [ ] Should we add loading skeletons? **Decision:** Defer to future PRP

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 8 | Clear specs from INITIAL file |
| Feasibility | 9 | Straightforward CSS/React changes |
| Completeness | 8 | Covers main components, defers edge cases |
| Alignment | 8 | Matches jurigregg.com aesthetic |
| **Overall** | **8.25** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-17 | Claude | Initial draft from INITIAL-009 |
