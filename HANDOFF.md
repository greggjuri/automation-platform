# Handoff Guide: Claude.ai ↔ Claude Code Workflow

This document explains how to coordinate between Claude.ai (planning/architecture) and Claude Code (implementation) for this project.

## The Split

| Claude.ai (this chat) | Claude Code |
|-----------------------|-------------|
| Architecture decisions | Write code |
| Feature planning | Execute PRPs |
| Generate INITIAL files | Run tests |
| Review PRPs before execution | Deploy infrastructure |
| Troubleshoot blockers | Git operations |
| Update PLANNING.md | Create files and directories |

## Workflow

### 1. Plan Here (Claude.ai)
- Discuss what you want to build
- I'll help define requirements
- We'll create/update INITIAL files together
- Review and refine before implementation

### 2. Generate PRP (Claude Code)
```bash
# In Claude Code, from project root:
/generate-prp INITIAL/feature-name.md
```
Claude Code will:
- Read all context files (CLAUDE.md, PLANNING.md, etc.)
- Research the codebase
- Generate a detailed PRP

### 3. Review PRP (Claude.ai)
- Bring the generated PRP back here if you want review
- We can refine requirements or approach
- Ensure nothing is missing before implementation

### 4. Execute PRP (Claude Code)
```bash
# In Claude Code:
/execute-prp PRPs/feature-name.md
```
Claude Code will:
- Implement step by step
- Validate each step
- Run tests
- Update TASK.md

### 5. Handle Issues (Either)
- Simple bugs → Claude Code can fix
- Architecture questions → Bring back here
- Blockers → Discuss approach here, fix in Claude Code

## Key Files Both Must Read

**Claude Code reads these automatically:**
- `CLAUDE.md` - Project rules and conventions
- `docs/PLANNING.md` - Architecture overview
- `docs/TASK.md` - Current work status
- `docs/DECISIONS.md` - Past decisions

**You should reference these in conversations:**
- When discussing architecture, mention PLANNING.md context
- When starting new features, reference relevant DECISIONS.md entries
- When checking status, look at TASK.md

## Keeping Things in Sync

### After Claude Code work:
1. Review what was created/changed
2. If architecture evolved, update PLANNING.md
3. If new decisions were made, add to DECISIONS.md
4. Mark tasks complete in TASK.md

### Before starting new features:
1. Check TASK.md for current state
2. Review PLANNING.md for context
3. Create INITIAL file with full requirements

## Example Session

**You (to Claude.ai):**
> "I want to add the HTTP Request action to workflows"

**Claude.ai:**
> "Let's define that. Based on PLANNING.md, we need... [creates INITIAL/http-request-action.md]"

**You (to Claude Code):**
```bash
/generate-prp INITIAL/http-request-action.md
```

**Claude Code:**
> "Generated PRPs/http-request-action.md with confidence 8/10..."

**You (optionally, back to Claude.ai):**
> "Here's the PRP, does this look right?"

**Claude.ai:**
> "Looks good, but consider adding retry logic for transient failures..."

**You (to Claude Code):**
```bash
/execute-prp PRPs/http-request-action.md
```

**Claude Code:**
> "Step 1 complete... Step 2 complete... All tests passing..."

## Tips

1. **Don't skip the INITIAL step** - Well-defined requirements = better PRPs
2. **Review PRPs for complex features** - Catch issues before implementation
3. **Keep TASK.md updated** - Both AI and human need to know current state
4. **Document decisions** - Future you (and Claude) will thank you
5. **Use examples/** - Add patterns that work, Claude Code will follow them

## Getting Started

Your first task is ready:

```bash
# In Claude Code:
/generate-prp INITIAL/01-project-foundation.md
```

This will set up the CDK infrastructure foundation. Once that's done, we can move to API and execution engine features.
