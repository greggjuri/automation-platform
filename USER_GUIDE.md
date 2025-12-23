# User Guide: Automation Platform

A comprehensive guide to building and running automated workflows on your self-hosted serverless platform.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Creating Your First Workflow](#creating-your-first-workflow)
4. [Triggers](#triggers)
5. [Actions](#actions)
6. [Variables & Secrets](#variables--secrets)
7. [Monitoring Executions](#monitoring-executions)
8. [Authentication](#authentication)
9. [Real-World Examples](#real-world-examples)
10. [Troubleshooting](#troubleshooting)
11. [API Reference](#api-reference)

---

## Quick Start

Get a workflow running in under 5 minutes.

### Step 1: Access the Dashboard

Open your browser and navigate to your deployment URL (e.g., `https://automations.jurigregg.com`).

### Step 2: Log In

Click **Log In** in the top navigation. Enter your credentials to enable workflow creation.

> **Note:** Without logging in, you can view workflows and executions, but all creation, editing, and running requires authentication.

### Step 3: Create a Simple Workflow

1. Click **New Workflow**
2. Fill in the basics:
   - **Name:** `Hello World`
   - **Description:** `My first workflow`
3. Leave trigger as **Manual**
4. Click **Add Step** and configure:
   - **Name:** `log_hello`
   - **Type:** Log
   - **Message:** `Hello from my first workflow!`
   - **Level:** Info
5. Click **Save Workflow**

### Step 4: Run It

On the workflow detail page, click **Run Now**. You'll see a new execution appear with status "Success".

### Step 5: View Results

Click the execution to see step-by-step results, timing, and output.

**Congratulations!** You've created and run your first workflow.

---

## Installation

### Prerequisites

Before you begin, ensure you have:

- **AWS Account** with administrator access
- **AWS CLI** installed and configured (`aws configure`)
- **Python 3.11+** installed
- **Node.js 18+** installed
- **AWS CDK CLI** installed (`npm install -g aws-cdk`)
- **Git** installed

### Clone the Repository

```bash
git clone https://github.com/greggjuri/automation-platform.git
cd automation-platform
```

### Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate        # macOS/Linux
# OR
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements-dev.txt
```

### Bootstrap CDK (First Time Only)

If you've never used CDK in this AWS account/region:

```bash
cd cdk
cdk bootstrap
```

### Deploy Infrastructure

```bash
cd cdk
cdk deploy --all
```

This deploys 6 CloudFormation stacks:
1. **SharedStack** - IAM roles, SSM paths
2. **DatabaseStack** - DynamoDB tables
3. **TriggersStack** - EventBridge rules, SQS queues, Poller Lambda
4. **ExecutionStack** - Step Functions, action Lambdas
5. **ApiStack** - API Gateway, API Lambda
6. **FrontendStack** - S3, CloudFront, Route53

Deployment takes approximately 5-10 minutes.

### Set Up Authentication (Cognito)

```bash
cd scripts

# Create the Cognito User Pool and App Client
./setup-cognito.sh

# Create your admin user (check email for temporary password)
./create-admin-user.sh your-email@example.com

# Configure API Gateway to use Cognito
./setup-cognito-authorizer.sh
```

### Configure Frontend Environment

Create `frontend/.env.local`:

```bash
VITE_API_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com
VITE_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXX
VITE_COGNITO_CLIENT_ID=your-client-id
VITE_COGNITO_REGION=us-east-1
```

### Build and Deploy Frontend

```bash
cd frontend
npm install
npm run build

# Deploy (this happens automatically if you run cdk deploy again)
cd ../cdk
cdk deploy FrontendStack
```

### Verify Installation

1. Open your frontend URL in a browser
2. Log in with your Cognito credentials
3. Create a test workflow and run it

---

## Creating Your First Workflow

A workflow consists of:
- **Trigger** - What starts the workflow
- **Steps** - Actions to execute in order

### Using the Workflow Editor

1. Navigate to **Workflows** → **New Workflow**
2. Fill in the form:

| Field | Description | Example |
|-------|-------------|---------|
| Name | Short identifier | `RSS to Discord` |
| Description | What this workflow does | `Posts new blog items to Discord` |
| Enabled | Toggle on/off | ✓ Enabled |

3. Configure the **Trigger** (see [Triggers](#triggers))
4. Add one or more **Steps** (see [Actions](#actions))
5. Click **Save Workflow**

### Workflow States

| State | Meaning |
|-------|---------|
| **Enabled** | Workflow runs automatically when triggered |
| **Disabled** | Workflow won't run (manual execution still works) |

Toggle the switch on the workflow card or detail page to enable/disable.

---

## Triggers

Triggers determine **when** a workflow runs.

### Manual Trigger

**What it does:** Workflow only runs when you click "Run Now" or call the API.

**When to use:** Testing, on-demand tasks, one-time operations.

**Configuration:** None required.

**Example use case:** Generate a weekly report on demand.

---

### Webhook Trigger

**What it does:** Runs when an external service POSTs to your unique webhook URL.

**When to use:** Real-time integrations with services that support webhooks (GitHub, Stripe, etc.).

**Configuration:**
1. Select "Webhook" as trigger type
2. Save the workflow
3. Copy the generated webhook URL
4. Configure the external service to POST to this URL

**Your webhook URL format:**
```
https://your-api-id.execute-api.us-east-1.amazonaws.com/webhook/{workflow_id}
```

**Available variables in steps:**

| Variable | Description |
|----------|-------------|
| `{{trigger.type}}` | Always "webhook" |
| `{{trigger.payload}}` | The JSON body sent to the webhook |
| `{{trigger.headers}}` | Request headers as object |
| `{{trigger.query}}` | Query string parameters |

**Example: GitHub Push Notification**

External service sends:
```json
POST /webhook/wf_abc123
{
  "ref": "refs/heads/main",
  "repository": {"full_name": "user/repo"},
  "pusher": {"name": "johndoe"}
}
```

Your workflow step can use:
```
{{trigger.payload.pusher.name}} pushed to {{trigger.payload.repository.full_name}}
```

---

### Cron (Schedule) Trigger

**What it does:** Runs on a schedule using AWS EventBridge.

**When to use:** Recurring tasks - daily reports, hourly checks, weekly cleanups.

**Configuration:**
1. Select "Schedule (Cron)" as trigger type
2. Enter a schedule expression

**Schedule Expression Formats:**

| Format | Example | Meaning |
|--------|---------|---------|
| Rate | `rate(5 minutes)` | Every 5 minutes |
| Rate | `rate(1 hour)` | Every hour |
| Rate | `rate(1 day)` | Every day |
| Cron | `cron(0 9 * * ? *)` | Daily at 9:00 AM UTC |
| Cron | `cron(0 9 ? * MON *)` | Every Monday at 9:00 AM UTC |
| Cron | `cron(0 */2 * * ? *)` | Every 2 hours |

**Quick reference buttons** in the UI let you select common schedules with one click.

**AWS Cron Syntax:** `cron(minutes hours day-of-month month day-of-week year)`
- Use `?` for day-of-month OR day-of-week (not both)
- Use `*` for "every"
- All times are **UTC**

**Available variables in steps:**

| Variable | Description |
|----------|-------------|
| `{{trigger.type}}` | Always "cron" |
| `{{trigger.scheduled_time}}` | ISO timestamp of scheduled run |

**Example: Daily 9 AM Report**
- Schedule: `cron(0 9 * * ? *)`
- Step message: `Daily report triggered at {{trigger.scheduled_time}}`

---

### Poll Trigger

**What it does:** Periodically checks a URL for changes and triggers when new content is found.

**When to use:** RSS/Atom feeds, APIs without webhooks, monitoring pages for changes.

**Configuration:**

| Field | Description | Required |
|-------|-------------|----------|
| URL to Poll | The feed or page URL | Yes |
| Content Type | `RSS`, `Atom`, or `HTTP` | Yes |
| Poll Interval | Minutes between checks (min: 5) | Yes |

**Content Type Behavior:**

| Type | Detection Method | Trigger Data |
|------|-----------------|--------------|
| **RSS** | Tracks `<guid>` elements, triggers on new items | Array of new items |
| **Atom** | Tracks `<id>` elements, triggers on new items | Array of new items |
| **HTTP** | SHA256 hash of response body | Raw content + hash |

**Available variables in steps:**

For RSS/Atom feeds:

| Variable | Description |
|----------|-------------|
| `{{trigger.type}}` | Always "poll" |
| `{{trigger.content_type}}` | "rss" or "atom" |
| `{{trigger.items}}` | Array of new feed items |
| `{{trigger.items[0].title}}` | First item's title |
| `{{trigger.items[0].link}}` | First item's link |
| `{{trigger.items[0].guid}}` | First item's unique ID |
| `{{trigger.items[0].summary}}` | First item's summary/description |

For HTTP polling:

| Variable | Description |
|----------|-------------|
| `{{trigger.content}}` | Full response body |
| `{{trigger.content_hash}}` | SHA256 hash of content |

**Example: Blog RSS to Discord**

Configuration:
- URL: `https://blog.example.com/feed.xml`
- Content Type: RSS
- Poll Interval: 15 minutes

Step (Notify):
```
New post: {{trigger.items[0].title}}
Read more: {{trigger.items[0].link}}
```

**How It Works:**

The platform tracks which feed items have been seen (by GUID/ID) in DynamoDB. When polling:
- Only **new** items trigger the workflow
- Re-enabling a disabled workflow won't re-process old items
- Each poll checks for items not previously seen

**Error Handling:**

If polling fails 4 consecutive times:
1. Workflow is automatically disabled
2. You receive a Discord notification (if configured)
3. Check execution history for error details

---

## Actions

Actions are the **steps** your workflow executes. Steps run in order, and each step can use outputs from previous steps.

### HTTP Request

**What it does:** Makes an HTTP request to any URL.

**Configuration:**

| Field | Description | Required |
|-------|-------------|----------|
| Method | GET, POST, PUT, DELETE | Yes |
| URL | Target URL (supports variables) | Yes |
| Headers | Key-value pairs (JSON format) | No |
| Body | Request body for POST/PUT | No |

**Output available to subsequent steps:**

| Variable | Description |
|----------|-------------|
| `{{steps.{step_name}.output.status}}` | HTTP status code (200, 404, etc.) |
| `{{steps.{step_name}.output.body}}` | Response body (parsed JSON if applicable) |
| `{{steps.{step_name}.output.headers}}` | Response headers |

**Example: Fetch Weather Data**

```
Step Name: fetch_weather
Type: HTTP Request
Method: GET
URL: https://api.weather.gov/gridpoints/TOP/32,81/forecast
Headers: {"User-Agent": "MyApp/1.0"}
```

Then in the next step:
```
Today's forecast: {{steps.fetch_weather.output.body.properties.periods[0].detailedForecast}}
```

**Example: POST with JSON Body**

```
Step Name: create_issue
Type: HTTP Request
Method: POST
URL: https://api.github.com/repos/user/repo/issues
Headers: {
  "Authorization": "token {{secrets.github_token}}",
  "Content-Type": "application/json"
}
Body: {
  "title": "Automated issue from {{trigger.type}}",
  "body": "Created by automation platform"
}
```

---

### Transform

**What it does:** Creates new data using templates and variable interpolation.

**Configuration:**

| Field | Description | Required |
|-------|-------------|----------|
| Template | String with `{{variables}}` | Yes |
| Output Key | Name for the result (default: "result") | No |

**Output:**

| Variable | Description |
|----------|-------------|
| `{{steps.{step_name}.output}}` | The transformed result |

**Example: Format a Message**

```
Step Name: format_message
Type: Transform
Template: 🚀 New release: {{trigger.payload.release.name}} by {{trigger.payload.sender.login}}
Output Key: notification
```

Result available as `{{steps.format_message.output}}`

**Example: Build JSON Object**

```
Step Name: build_payload
Type: Transform
Template: {"channel": "alerts", "text": "{{steps.fetch_data.output.body.message}}"}
```

---

### Log

**What it does:** Writes a message to the execution log. Useful for debugging.

**Configuration:**

| Field | Description | Required |
|-------|-------------|----------|
| Message | Text to log (supports variables) | Yes |
| Level | info, warn, or error | Yes |

**No output** - Log steps don't produce output for subsequent steps.

**Example: Debug Logging**

```
Step Name: debug_payload
Type: Log
Message: Received webhook payload: {{trigger.payload}}
Level: info
```

**Example: Conditional Warning**

```
Step Name: warn_empty
Type: Log
Message: Warning: No items found in feed response
Level: warn
```

---

### Notify (Discord)

**What it does:** Sends a message to a Discord channel via webhook.

**Configuration:**

| Field | Description | Required |
|-------|-------------|----------|
| Webhook URL | Discord webhook URL (use secrets!) | Yes |
| Message | Text content (max 2000 chars) | Yes |
| Send as Embed | Format as a rich embed card | No |

> **Tip:** Enable "Send as embed" for a visually distinct card-style message instead of plain text.

**Output:**

| Variable | Description |
|----------|-------------|
| `{{steps.{step_name}.output.status_code}}` | HTTP status from Discord |

**Setting up Discord Webhook:**

1. In Discord, go to your server → Server Settings → Integrations → Webhooks
2. Click "New Webhook"
3. Name it, choose a channel, copy the URL
4. Add the URL as a secret in the platform (see [Secrets](#secrets))

**Example: Simple Notification**

```
Step Name: notify_discord
Type: Notify
Webhook URL: {{secrets.discord_webhook}}
Message: New item posted: {{trigger.items[0].title}} - {{trigger.items[0].link}}
```

**Example: Rich Notification**

```
Step Name: notify_complete
Type: Notify
Webhook URL: {{secrets.discord_webhook}}
Message: ✅ Workflow completed successfully!
📊 Processed {{steps.count_items.output}} items
⏱️ Triggered at {{trigger.scheduled_time}}
```

---

## Variables & Secrets

### Variable Syntax

Use double curly braces to insert dynamic values: `{{variable.path}}`

### Variable Sources

| Prefix | Source | Example |
|--------|--------|---------|
| `trigger.*` | Data from the trigger event | `{{trigger.payload.user.name}}` |
| `steps.*` | Output from previous steps | `{{steps.fetch_data.output.body}}` |
| `secrets.*` | Secure values from SSM | `{{secrets.api_key}}` |

### Accessing Nested Data

Use dot notation for nested objects:
```
{{trigger.payload.repository.owner.login}}
```

Use bracket notation for arrays:
```
{{trigger.items[0].title}}
{{trigger.items[1].link}}
```

### Variable Helper

When editing a step, click **Available Variables** to expand a panel showing all variables you can use:

- **Trigger variables** - Context-specific to your selected trigger type (manual, webhook, cron, or poll)
- **Step outputs** - From all previous steps in the workflow, with type-specific hints (e.g., HTTP requests show `output.status`, `output.body`, `output.headers`)
- **Secrets** - Pattern for referencing your stored secrets

**Features:**
- Variables update dynamically as you change the trigger type or add/remove steps
- Only shows steps *above* the current step (you can't reference future steps)
- Hover over any variable and click the copy icon to copy the full `{{...}}` syntax to your clipboard
- A toast notification confirms when copied

---

### Secrets

Secrets store sensitive values like API keys, tokens, and webhook URLs. They're encrypted at rest using AWS SSM Parameter Store.

#### Adding a Secret

1. Navigate to **Secrets** in the main menu
2. Click **Add Secret**
3. Enter a name (lowercase, letters, numbers, underscores, hyphens)
4. Enter the secret value
5. Click **Save**

#### Using Secrets in Workflows

Reference secrets with `{{secrets.secret_name}}`:

```
URL: https://api.example.com/data
Headers: {"Authorization": "Bearer {{secrets.api_token}}"}
```

#### Managing Secrets

- **View:** See all secret names (values are hidden)
- **Delete:** Remove a secret (workflows using it will fail)
- **Update:** Delete and recreate with the same name

**Best Practice:** Always use secrets for:
- API keys and tokens
- Webhook URLs (especially Discord)
- Passwords
- Any value you don't want in your workflow definition

---

## Monitoring Executions

> **Note:** Execution history is automatically cleaned up after 90 days (DynamoDB TTL).

### Execution List

Navigate to a workflow's detail page to see all executions:

| Column | Description |
|--------|-------------|
| **Status** | pending, running, success, failed |
| **Started** | When execution began |
| **Duration** | Total execution time |
| **Trigger** | What started this execution |

### Execution Detail

Click an execution to see:

1. **Overall status** - Success or failure
2. **Step-by-step breakdown:**
   - Each step's status (green = success, red = failed)
   - Duration per step
   - Input and output data
   - Error messages (if failed)

### Status Meanings

| Status | Meaning |
|--------|---------|
| `pending` | Queued, waiting to start |
| `running` | Currently executing |
| `success` | All steps completed successfully |
| `failed` | One or more steps failed |

### Retrying Failed Executions

If an execution failed due to a transient error (API timeout, rate limit):

1. View the execution detail
2. Click **Retry** button
3. A new execution starts with the same trigger data

### Failed Step Highlighting

Failed steps appear with a red border and show the error message. Check:
- Variable interpolation errors (missing data)
- HTTP errors (wrong URL, auth failures)
- Invalid configuration

---

## Authentication

The platform uses **read-only public access**:

| Action | Public | Authenticated |
|--------|--------|---------------|
| View workflows | ✓ | ✓ |
| View executions | ✓ | ✓ |
| Create workflow | ✗ | ✓ |
| Edit workflow | ✗ | ✓ |
| Delete workflow | ✗ | ✓ |
| Manage secrets | ✗ | ✓ |
| Run workflow | ✗ | ✓ |

### Logging In

1. Click **Log In** in the navigation bar
2. Enter your email and password
3. On first login, you'll be prompted to change your temporary password

### Managing Users

Users are managed through AWS Cognito. To add a new user:

```bash
cd scripts
./create-admin-user.sh newuser@example.com
```

The user will receive an email with a temporary password.

---

## Real-World Examples

### Example 1: RSS Feed to Discord

**Goal:** Post new blog articles to a Discord channel.

**Trigger:**
- Type: Poll
- URL: `https://blog.example.com/feed.xml`
- Content Type: RSS
- Interval: 15 minutes

**Steps:**

1. **format_message** (Transform)
   ```
   Template: 📰 New post: **{{trigger.items[0].title}}**
   {{trigger.items[0].summary}}
   Read more: {{trigger.items[0].link}}
   ```

2. **notify_discord** (Notify)
   ```
   Webhook URL: {{secrets.discord_webhook}}
   Message: {{steps.format_message.output}}
   ```

---

### Example 2: GitHub Webhook → Discord

**Goal:** Get notified when someone stars your repository.

**Trigger:**
- Type: Webhook
- (Configure GitHub to send "star" events to your webhook URL)

**Steps:**

1. **notify_star** (Notify)
   ```
   Webhook URL: {{secrets.discord_webhook}}
   Message: ⭐ {{trigger.payload.sender.login}} starred {{trigger.payload.repository.full_name}}!
   ```

---

### Example 3: Daily Health Check

**Goal:** Check if an API is responding and notify if it's down.

**Trigger:**
- Type: Cron
- Schedule: `rate(1 hour)`

**Steps:**

1. **check_api** (HTTP Request)
   ```
   Method: GET
   URL: https://api.myservice.com/health
   ```

2. **log_status** (Log)
   ```
   Message: API returned status {{steps.check_api.output.status}}
   Level: info
   ```

3. **notify_if_down** (Notify)
   ```
   Webhook URL: {{secrets.discord_webhook}}
   Message: ⚠️ API health check: Status {{steps.check_api.output.status}}
   ```

---

### Example 4: Data Pipeline

**Goal:** Fetch data from one API, transform it, and POST to another.

**Trigger:**
- Type: Cron
- Schedule: `cron(0 6 * * ? *)` (Daily at 6 AM UTC)

**Steps:**

1. **fetch_source** (HTTP Request)
   ```
   Method: GET
   URL: https://source-api.com/data
   Headers: {"Authorization": "Bearer {{secrets.source_api_key}}"}
   ```

2. **transform_data** (Transform)
   ```
   Template: {
     "items": {{steps.fetch_source.output.body.results}},
     "timestamp": "{{trigger.scheduled_time}}",
     "source": "automation-platform"
   }
   ```

3. **post_destination** (HTTP Request)
   ```
   Method: POST
   URL: https://destination-api.com/import
   Headers: {
     "Authorization": "Bearer {{secrets.dest_api_key}}",
     "Content-Type": "application/json"
   }
   Body: {{steps.transform_data.output}}
   ```

4. **notify_complete** (Notify)
   ```
   Webhook URL: {{secrets.discord_webhook}}
   Message: ✅ Daily data sync complete. Imported {{steps.fetch_source.output.body.results.length}} items.
   ```

---

## Troubleshooting

### Common Issues

#### "Variable not found" Error

**Symptom:** Step fails with interpolation error.

**Causes:**
1. Typo in variable name
2. Previous step failed (no output)
3. Wrong trigger type (e.g., using `trigger.payload` on a cron trigger)

**Solution:**
- Click **Available Variables** in the step editor to see all valid variables
- Use the copy button to get the exact syntax - never type variable names manually
- Check previous steps completed successfully
- Verify your trigger type matches expected variables (webhook has `payload`, cron has `scheduled_time`, etc.)

---

#### Webhook Not Triggering

**Symptom:** External service sends webhook, but workflow doesn't run.

**Causes:**
1. Workflow is disabled
2. Wrong webhook URL
3. External service configuration issue

**Solution:**
1. Check workflow is enabled (toggle switch is on)
2. Verify the webhook URL matches exactly
3. Check external service's webhook delivery logs
4. Look at CloudWatch logs for webhook receiver Lambda

---

#### Cron Not Running

**Symptom:** Scheduled workflow doesn't execute at expected time.

**Causes:**
1. Invalid cron expression
2. Workflow is disabled
3. EventBridge rule not created

**Solution:**
1. Validate your cron expression (use quick-select buttons)
2. Enable the workflow
3. Re-save the workflow to ensure EventBridge rule is created
4. Remember: all times are **UTC**

---

#### Poll Trigger Auto-Disabled

**Symptom:** Poll workflow stops running, shows as disabled.

**Causes:**
- 4 consecutive polling failures
- Source URL is unreachable
- Feed format changed

**Solution:**
1. Check execution history for error messages
2. Verify the source URL is accessible
3. Fix the issue and re-enable the workflow

---

#### "Unauthorized" Error

**Symptom:** API calls return 401/403.

**Causes:**
1. Not logged in
2. Session expired
3. Missing Cognito configuration

**Solution:**
1. Click Log In and authenticate
2. If session expired, log out and log back in
3. Verify frontend `.env.local` has correct Cognito settings

---

### Viewing Logs

For deeper debugging, access AWS CloudWatch Logs:

| Lambda Function | Log Group |
|----------------|-----------|
| API | `/aws/lambda/dev-automation-api-handler` |
| Webhook Receiver | `/aws/lambda/dev-webhook-receiver` |
| Cron Handler | `/aws/lambda/dev-cron-handler` |
| Poller | `/aws/lambda/dev-poller` |
| Execution Starter | `/aws/lambda/dev-execution-starter` |
| HTTP Request Action | `/aws/lambda/dev-action-http-request` |
| Transform Action | `/aws/lambda/dev-action-transform` |
| Log Action | `/aws/lambda/dev-action-log` |
| Notify Action | `/aws/lambda/dev-action-notify` |

> **Note:** Log group names use the `dev-` prefix. If you deployed with a different environment name, adjust accordingly.

---

## API Reference

The platform exposes a REST API for programmatic access.

### Base URL

```
https://your-api-id.execute-api.us-east-1.amazonaws.com
```

### Authentication

Protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer {cognito_id_token}
```

### Endpoints

#### Workflows

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/workflows` | No | List all workflows |
| POST | `/workflows` | Yes | Create workflow |
| GET | `/workflows/{id}` | No | Get workflow details |
| PUT | `/workflows/{id}` | Yes | Update workflow |
| DELETE | `/workflows/{id}` | Yes | Delete workflow |
| PATCH | `/workflows/{id}/enabled` | Yes | Enable/disable workflow |
| POST | `/workflows/{id}/execute` | Yes | Manually trigger workflow |

#### Executions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/workflows/{workflow_id}/executions` | No | List executions for workflow |
| GET | `/workflows/{workflow_id}/executions/{execution_id}` | No | Get execution details |

#### Secrets

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/secrets` | Yes | List secret names |
| POST | `/secrets` | Yes | Create secret |
| DELETE | `/secrets/{name}` | Yes | Delete secret |

#### Webhooks

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/webhook/{workflow_id}` | No | Trigger webhook workflow |

### Example: Create Workflow via API

```bash
curl -X POST https://your-api.../workflows \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Test Workflow",
    "description": "Created via API",
    "enabled": true,
    "trigger": {
      "type": "manual",
      "config": {}
    },
    "steps": [
      {
        "step_id": "step_1",
        "name": "log_test",
        "type": "log",
        "config": {
          "message": "Hello from API!",
          "level": "info"
        }
      }
    ]
  }'
```

### Example: Trigger Workflow via API

```bash
curl -X POST https://your-api.../workflows/wf_abc123/execute \
  -H "Authorization: Bearer $TOKEN"
```

### Example: Send Webhook

```bash
curl -X POST https://your-api.../webhook/wf_abc123 \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "data": {"message": "Hello"}}'
```

---

## Cost Optimization

The platform is designed to stay under $20/month with typical personal use.

### Expected Costs

| Service | Estimate |
|---------|----------|
| Lambda | $1-2 (mostly free tier) |
| API Gateway | $1 |
| Step Functions | $1-3 |
| DynamoDB | $1-2 |
| EventBridge | $0.50 |
| S3 + CloudFront | $1 |
| SQS | $0.50 |
| **Total** | **$8-15/month** |

### Tips to Minimize Costs

1. **Increase poll intervals** - 15+ minutes instead of 5
2. **Disable unused workflows** - They still have EventBridge rules
3. **Clean up old executions** - DynamoDB storage costs (minimal)
4. **Use manual triggers for testing** - Don't leave cron triggers running

---

## Getting Help

- **GitHub Issues:** Report bugs or request features
- **Documentation:** `PLANNING.md`, `DECISIONS.md` in the repo
- **Architecture:** See the architecture diagram in `PLANNING.md`

---

*Happy automating!* 🚀
