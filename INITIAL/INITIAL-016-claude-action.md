# INITIAL-016: Claude AI Action Type

## What I Want

Add a new action type that calls the Anthropic Claude API, enabling AI-powered automation workflows. This allows workflows to summarize content, analyze data, generate text, or make decisions based on input.

## Why

- **AI-powered automation**: Differentiates this platform from basic Zapier/n8n clones
- **Personal utility**: Daily news/blog digest summarized automatically
- **Showcase capability**: Demonstrates the platform can handle complex, longer-running actions
- **Natural fit**: RSS polling → Claude summarization → Discord notification is a compelling use case

## Primary Use Case: RSS → Claude → Discord

```
[Poll RSS Feed] → [Claude: Summarize] → [Notify Discord]
```

Daily summary of tech news delivered to Discord, with AI-generated summaries instead of raw article snippets.

## Example Workflow Definition

```json
{
  "name": "Daily Tech Digest",
  "enabled": true,
  "trigger": {
    "type": "poll",
    "config": {
      "url": "https://news.ycombinator.com/rss",
      "interval_minutes": 60,
      "content_type": "rss"
    }
  },
  "steps": [
    {
      "step_id": "summarize",
      "name": "Summarize Articles",
      "type": "claude",
      "config": {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 500,
        "prompt": "Summarize the following article in 2-3 sentences, focusing on why it matters:\n\nTitle: {{trigger.output.title}}\n\n{{trigger.output.content}}"
      }
    },
    {
      "step_id": "notify",
      "name": "Send to Discord",
      "type": "notify",
      "config": {
        "service": "discord",
        "webhook_url": "{{secrets.discord_webhook}}",
        "message": "📰 **{{trigger.output.title}}**\n\n{{steps.summarize.output.response}}\n\n🔗 {{trigger.output.link}}"
      }
    }
  ]
}
```

## User Stories

1. As a user, I can add a Claude action to my workflow that processes text with AI
2. As a user, I can configure the model, max tokens, and prompt template
3. As a user, I can use variables in the prompt (trigger data, previous step outputs)
4. As a user, I can store my Anthropic API key securely and reference it in workflows
5. As a user, I can see Claude's response and token usage in execution history

## Technical Specification

### Action Configuration Schema

```json
{
  "type": "claude",
  "config": {
    "model": "claude-3-haiku-20240307",
    "max_tokens": 500,
    "prompt": "Your prompt with {{variables}}",
    "api_key_secret": "anthropic_api_key",
    "truncate_input": 4000
  }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `model` | string | No | `claude-3-haiku-20240307` | Claude model to use |
| `max_tokens` | integer | No | `500` | Max output tokens |
| `prompt` | string | Yes | - | Prompt template with variable interpolation |
| `api_key_secret` | string | No | `anthropic_api_key` | SSM secret name for API key |
| `truncate_input` | integer | No | `4000` | Max chars for interpolated prompt |

### Action Output Schema

```json
{
  "response": "The article discusses...",
  "model": "claude-3-haiku-20240307",
  "usage": {
    "input_tokens": 450,
    "output_tokens": 89
  },
  "truncated": false
}
```

### Model Options

Support these models (can expand later):
- `claude-3-haiku-20240307` (default) - Fast, cheap
- `claude-3-5-sonnet-20241022` - More capable
- `claude-3-5-haiku-20241022` - Newer fast model

### Cost Considerations

- Haiku: $0.25/1M input tokens, $1.25/1M output tokens
- ~500 input + ~100 output tokens per call ≈ $0.00025/call
- 10 calls/day = ~$0.08/month (very cheap)
- Truncation prevents runaway costs from large inputs

## Implementation Scope

### Backend

1. **New Lambda**: `lambdas/claude/handler.py`
   - Fetch API key from SSM
   - Interpolate prompt template
   - Truncate if over limit
   - Call Anthropic API
   - Return response with usage stats

2. **Step Functions**: Add claude action type to state machine Choice

3. **CDK Updates**: 
   - New Lambda in `execution_stack.py`
   - IAM: SSM read + HTTPS egress (already allowed)

### Frontend

4. **ClaudeConfig.tsx**: New step config component
   - Model dropdown
   - Max tokens number input
   - Prompt textarea with variable hints
   - API key secret selector (from existing secrets)
   - Optional: truncate limit input

5. **StepEditor.tsx**: Add claude to step type options

6. **VariableHelper.tsx**: Add claude output hints

### Testing

7. **Unit tests**: `test_claude_action.py`
   - Successful API call
   - API key retrieval
   - Prompt interpolation
   - Truncation
   - Error handling (API errors, missing key)
   - Rate limit handling

## Error Handling

| Error | Handling |
|-------|----------|
| Missing API key | Fail step with "API key not found in secrets" |
| API error (4xx) | Fail step with API error message |
| Rate limit (429) | Fail step with "Rate limited, try again later" |
| Timeout | 30s Lambda timeout, fail step |
| Invalid model | Fail step with "Invalid model specified" |

## Dependencies

- `anthropic` Python package (add to Lambda layer or bundle)
- Existing: shared interpolation, SSM access patterns

## Success Criteria

1. ✅ Can create workflow with Claude action in UI
2. ✅ Claude action calls API and returns response
3. ✅ Response accessible via `{{steps.step_name.output.response}}`
4. ✅ Token usage visible in execution details
5. ✅ Large inputs truncated to prevent cost overrun
6. ✅ Errors surfaced clearly in execution history

## Out of Scope

- Streaming responses (not needed for automation)
- Vision/image input (future enhancement)
- Tool use (future enhancement)
- Conversation memory (each call is stateless)
- Model fine-tuning

## Cost Estimate

With daily usage (10 calls/day):
- Input: ~500 tokens × 10 × 30 = 150,000 tokens/month
- Output: ~100 tokens × 10 × 30 = 30,000 tokens/month
- Cost: (150k × $0.25 + 30k × $1.25) / 1M = **~$0.08/month**

Within budget constraints.

## Implementation Estimate

- Lambda + CDK: 2-3 hours
- Frontend component: 1-2 hours  
- Tests: 1-2 hours
- Integration testing: 1 hour
- **Total: 5-8 hours**

## Open Questions

1. Should we support system prompts separately from user prompts? (Probably not for MVP)
2. Should we expose temperature/top_p? (Probably not for MVP, use defaults)
3. Should truncation be configurable per-action or global? (Per-action, defaulting to 4000)
