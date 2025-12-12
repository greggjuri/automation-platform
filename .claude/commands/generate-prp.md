# Generate PRP

Generate a comprehensive Project Requirement Plan (PRP) for a new feature or task.

## Arguments
- `$ARGUMENTS` - Initial file path or feature description

## Instructions

You are generating a PRP (Project Requirement Plan) for this automation platform project.

### Step 1: Gather Context

Read and internalize the following project documentation:
1. `CLAUDE.md` - Project-specific instructions and conventions
2. `docs/PLANNING.md` - Architecture overview and goals
3. `docs/DECISIONS.md` - Past architecture decisions (don't contradict these)
4. `docs/TASK.md` - Current task status

### Step 2: Research Codebase

Based on the feature description `$ARGUMENTS`, research the codebase:
1. Search for related existing implementations
2. Identify files that will need modification
3. Check `examples/` folder for patterns to follow
4. Look for existing similar patterns in `lambdas/`, `cdk/`, or `frontend/`

### Step 3: Generate PRP

Create a new PRP file at `PRPs/PRP-XXX-{feature-slug}.md` where:
- XXX is the next sequential number (check existing PRPs)
- feature-slug is a kebab-case short description

Use the template at `PRPs/templates/prp_base.md` as the structure.

Fill in all sections:
1. **Overview**: Clear problem statement and proposed solution
2. **Success Criteria**: Measurable, testable outcomes
3. **Context**: Links to relevant docs, existing code, dependencies
4. **Technical Specification**: Data models, API changes, component structure
5. **Implementation Steps**: Ordered, atomic tasks with file paths
6. **Testing Requirements**: Unit, integration, E2E tests needed
7. **Error Handling**: Edge cases and failure scenarios
8. **Open Questions**: Anything that needs clarification

### Step 4: Score Confidence

Before finishing, score your confidence (1-10) on each dimension:
- **Clarity**: How well-defined is the scope? (are requirements unambiguous?)
- **Feasibility**: Can this be done with current architecture? (are there blockers?)
- **Completeness**: Does the PRP cover all aspects? (no missing pieces?)
- **Alignment**: Does it align with project goals/constraints? (budget, patterns)

Calculate overall confidence as the average.

If overall confidence is below 7:
- List specific concerns
- Identify what additional context would help
- Ask clarifying questions

### Step 5: Output

1. Create the PRP file in `PRPs/` folder
2. Report the file path created
3. Display confidence scores
4. List any open questions or concerns

## Example Usage

```
/generate-prp Add webhook receiver Lambda for external triggers
```

This would:
1. Research existing Lambda patterns in the codebase
2. Check PLANNING.md for webhook architecture
3. Generate `PRPs/PRP-001-webhook-receiver.md`
4. Score confidence and report any concerns
