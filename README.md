# Automation Platform

A personal event-driven automation platform for defining and executing workflows with triggers and actions. Think Zapier or n8n, but self-hosted on AWS serverless.

## Live Demo

**https://automations.jurigregg.com**

Public visitors can view workflows and executions. Authentication required to create, edit, or delete.

## Features

- **Triggers:** Webhooks, cron schedules, manual execution
- **Actions:** HTTP requests, transformations, Discord notifications
- **Execution:** Step Functions for reliable orchestration with retries
- **Monitoring:** Execution history, step-by-step logs, error tracking
- **Secrets:** Secure storage with SSM Parameter Store
- **Auth:** Cognito authentication with read-only public access
- **UI:** React dashboard with glass morphism design

## Architecture

```
Frontend (React) → API Gateway → Lambda → DynamoDB
                                    ↓
Triggers (EventBridge/Webhook) → SQS → Step Functions → Actions
```

See [docs/PLANNING.md](docs/PLANNING.md) for detailed architecture.

## Quick Start

### Prerequisites

- AWS CLI configured with credentials
- Python 3.11+
- Node.js 18+
- AWS CDK CLI (`npm install -g aws-cdk`)

### Setup

```bash
# Clone the repo
git clone https://github.com/greggjuri/automation-platform.git
cd automation-platform

# Set up Python environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Bootstrap CDK (first time only)
cd cdk
cdk bootstrap

# Deploy infrastructure
cdk deploy --all

# Set up frontend
cd ../frontend
npm install
npm run dev
```

### Configuration

#### Backend
1. Copy `.env.example` to `.env`
2. Add your AWS account ID and region
3. Configure secrets in SSM Parameter Store

#### Authentication (Cognito)
```bash
# Create Cognito User Pool and Client
cd scripts
./setup-cognito.sh

# Create admin user
./create-admin-user.sh your-email@example.com

# Set up API Gateway authorizer
./setup-cognito-authorizer.sh
```

#### Frontend
Create `frontend/.env.local` with Cognito config:
```
VITE_COGNITO_USER_POOL_ID=us-east-1_XXXXXX
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxx
VITE_COGNITO_REGION=us-east-1
```

## Project Structure

```
automation-platform/
├── .claude/              # Claude Code configuration
│   ├── commands/         # Slash commands (generate-prp, execute-prp)
│   └── settings.local.json
├── docs/                 # Documentation
│   ├── PLANNING.md       # Architecture and roadmap
│   ├── TASK.md          # Current tasks
│   └── DECISIONS.md     # Architecture decisions
├── PRPs/                # Product Requirements Prompts
├── INITIAL/             # Feature requests
├── examples/            # Code patterns to follow
├── cdk/                 # AWS CDK infrastructure
├── lambdas/             # Lambda function code
├── frontend/            # React application
├── tests/               # Test suites
├── CLAUDE.md            # AI assistant rules
└── README.md
```

## Development Workflow

This project uses **context engineering** for AI-assisted development:

1. **Define feature** in `INITIAL/{feature-name}.md`
2. **Generate PRP:** `/generate-prp INITIAL/{feature-name}.md`
3. **Execute PRP:** `/execute-prp PRPs/{feature-name}.md`
4. **Review and iterate**

See [Context Engineering Guide](https://github.com/coleam00/context-engineering-intro) for methodology details.

## Commands

```bash
# Backend
cd lambdas && pytest                    # Run tests
cd lambdas && ruff check .              # Lint Python

# Frontend  
cd frontend && npm run dev              # Dev server
cd frontend && npm run build            # Production build
cd frontend && npm test                 # Run tests

# Infrastructure
cd cdk && cdk synth                     # Synthesize CloudFormation
cd cdk && cdk deploy --all              # Deploy all stacks
cd cdk && cdk diff                      # Show pending changes
```

## Documentation

- [PLANNING.md](docs/PLANNING.md) - Architecture, goals, roadmap
- [DECISIONS.md](docs/DECISIONS.md) - Architecture Decision Records
- [TASK.md](docs/TASK.md) - Current work and backlog
- [CLAUDE.md](CLAUDE.md) - AI assistant guidelines

## Contributing

1. Check `docs/TASK.md` for available tasks
2. Create feature request in `INITIAL/`
3. Generate and execute PRP
4. Submit PR with tests

## License

MIT

## Acknowledgments

- [Context Engineering](https://github.com/coleam00/context-engineering-intro) by Cole Medin
- [AWS Powertools for Lambda](https://docs.powertools.aws.dev/lambda/python/)
