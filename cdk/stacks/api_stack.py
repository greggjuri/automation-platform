"""API Stack for Automation Platform.

Creates:
- Lambda function for API handling
- Webhook Receiver Lambda for external webhooks
- HTTP API Gateway with CORS
- Routes for workflow CRUD, execution, and webhook operations
- CloudWatch log groups
"""

import os

from aws_cdk import BundlingOptions, CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sqs as sqs
from constructs import Construct

# Path to lambdas directory
LAMBDAS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "lambdas")


class ApiStack(Stack):
    """CDK Stack for API Gateway and Lambda functions.

    Attributes:
        api: The HTTP API Gateway
        api_handler: The Lambda function handling API requests
        webhook_receiver: The Lambda function handling webhook requests
        api_url: The API endpoint URL
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        workflows_table: dynamodb.ITable,
        executions_table: dynamodb.ITable | None = None,
        execution_queue: sqs.IQueue | None = None,
        cron_handler_arn: str | None = None,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize the API stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            workflows_table: DynamoDB table for workflows
            executions_table: DynamoDB table for executions (optional)
            execution_queue: SQS queue for execution requests (optional)
            cron_handler_arn: ARN of cron handler Lambda for EventBridge rules
            environment: Deployment environment (dev, staging, prod)
            **kwargs: Additional stack options
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment
        self.workflows_table = workflows_table
        self.executions_table = executions_table
        self.execution_queue = execution_queue
        self.cron_handler_arn = cron_handler_arn

        # Create Lambda functions
        self._create_lambda(workflows_table)
        self._create_webhook_receiver()

        # Create HTTP API Gateway
        self._create_api_gateway()

        # Output the API URL
        self.api_url = CfnOutput(
            self,
            "ApiUrl",
            value=self.api.api_endpoint,
            description="API Gateway endpoint URL",
            export_name=f"{environment}-automation-api-url",
        )

    def _create_lambda(self, workflows_table: dynamodb.ITable) -> None:
        """Create the API Lambda function.

        Args:
            workflows_table: DynamoDB table to grant access to
        """
        # Create log group with retention policy
        log_group = logs.LogGroup(
            self,
            "ApiHandlerLogs",
            log_group_name=f"/aws/lambda/{self.env_name}-automation-api-handler",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Build environment variables
        env_vars = {
            "TABLE_NAME": workflows_table.table_name,
            "ENVIRONMENT": self.env_name,
            "POWERTOOLS_SERVICE_NAME": "automation-api",
            "POWERTOOLS_LOG_LEVEL": "INFO" if self.env_name == "prod" else "DEBUG",
            "POWERTOOLS_METRICS_NAMESPACE": "AutomationPlatform",
        }

        # Add execution-related env vars if available
        if self.executions_table:
            env_vars["EXECUTIONS_TABLE_NAME"] = self.executions_table.table_name
        if self.execution_queue:
            env_vars["EXECUTION_QUEUE_URL"] = self.execution_queue.queue_url

        # Add cron handler ARN for EventBridge rule creation
        if self.cron_handler_arn:
            env_vars["CRON_HANDLER_LAMBDA_ARN"] = self.cron_handler_arn

        # Lambda function for API handling
        self.api_handler = lambda_.Function(
            self,
            "ApiHandler",
            function_name=f"{self.env_name}-automation-api-handler",
            description="Handles API Gateway requests for workflow and execution operations",
            # Runtime and code
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                path=os.path.join(
                    os.path.dirname(__file__), "..", "..", "lambdas", "api"
                ),
                bundling={
                    "image": lambda_.Runtime.PYTHON_3_11.bundling_image,
                    "command": [
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r . /asset-output",
                    ],
                },
            ),
            # Resource configuration
            memory_size=256,
            timeout=Duration.seconds(29),  # API Gateway max is 29s
            # Environment variables
            environment=env_vars,
            # Logging
            log_group=log_group,
            # Tracing
            tracing=lambda_.Tracing.ACTIVE,
        )

        # Grant DynamoDB read/write permissions
        workflows_table.grant_read_write_data(self.api_handler)

        # Grant executions table access if available
        if self.executions_table:
            self.executions_table.grant_read_data(self.api_handler)

        # Grant SQS send permissions if queue available
        if self.execution_queue:
            self.execution_queue.grant_send_messages(self.api_handler)

        # Grant EventBridge permissions for cron trigger management
        if self.cron_handler_arn:
            self.api_handler.add_to_role_policy(
                iam.PolicyStatement(
                    actions=[
                        "events:PutRule",
                        "events:DeleteRule",
                        "events:PutTargets",
                        "events:RemoveTargets",
                        "events:DescribeRule",
                    ],
                    resources=[
                        f"arn:aws:events:{self.region}:{self.account}:rule/automations-{self.env_name}-*"
                    ],
                )
            )

        # Grant SSM permissions for secrets management
        self.api_handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ssm:GetParametersByPath",
                    "ssm:GetParameter",
                    "ssm:PutParameter",
                    "ssm:DeleteParameter",
                    "ssm:AddTagsToResource",
                    "ssm:ListTagsForResource",
                ],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/automations/*/secrets/*"
                ],
            )
        )

    def _create_webhook_receiver(self) -> None:
        """Create the Webhook Receiver Lambda function."""
        function_name = f"{self.env_name}-automation-webhook-receiver"

        # Create log group
        log_group = logs.LogGroup(
            self,
            "WebhookReceiverLogs",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Build environment variables
        env_vars = {
            "WORKFLOWS_TABLE_NAME": self.workflows_table.table_name,
            "ENVIRONMENT": self.env_name,
            "POWERTOOLS_SERVICE_NAME": "webhook-receiver",
            "POWERTOOLS_LOG_LEVEL": "INFO" if self.env_name == "prod" else "DEBUG",
        }

        # Add execution queue URL if available
        if self.execution_queue:
            env_vars["EXECUTION_QUEUE_URL"] = self.execution_queue.queue_url

        # Lambda function for webhook handling
        self.webhook_receiver = lambda_.Function(
            self,
            "WebhookReceiver",
            function_name=function_name,
            description="Receives webhooks and queues workflow executions",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                path=os.path.join(LAMBDAS_DIR, "webhook_receiver"),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r . /asset-output",
                    ],
                ),
            ),
            memory_size=256,
            timeout=Duration.seconds(10),  # Quick response for webhooks
            environment=env_vars,
            log_group=log_group,
            tracing=lambda_.Tracing.ACTIVE,
        )

        # Grant DynamoDB read permissions (only need to check workflow exists)
        self.workflows_table.grant_read_data(self.webhook_receiver)

        # Grant SQS send permissions if queue available
        if self.execution_queue:
            self.execution_queue.grant_send_messages(self.webhook_receiver)

    def _create_api_gateway(self) -> None:
        """Create the HTTP API Gateway with routes."""
        # Determine CORS origins based on environment
        cors_origins = (
            ["https://automations.jurigregg.com"]
            if self.env_name == "prod"
            else ["*"]
        )

        # Create HTTP API
        self.api = apigwv2.HttpApi(
            self,
            "HttpApi",
            api_name=f"{self.env_name}-automation-api",
            description="Automation Platform API",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_headers=["Content-Type", "Authorization", "X-Api-Key"],
                allow_methods=[
                    apigwv2.CorsHttpMethod.GET,
                    apigwv2.CorsHttpMethod.POST,
                    apigwv2.CorsHttpMethod.PUT,
                    apigwv2.CorsHttpMethod.PATCH,
                    apigwv2.CorsHttpMethod.DELETE,
                    apigwv2.CorsHttpMethod.OPTIONS,
                ],
                allow_origins=cors_origins,
                max_age=Duration.hours(1),
            ),
        )

        # Lambda integration
        api_integration = integrations.HttpLambdaIntegration(
            "ApiIntegration",
            handler=self.api_handler,
        )

        # ---------------------------------------------------------------------
        # Routes
        # ---------------------------------------------------------------------

        # Health check
        self.api.add_routes(
            path="/health",
            methods=[apigwv2.HttpMethod.GET],
            integration=api_integration,
        )

        # Workflow routes - collection
        self.api.add_routes(
            path="/workflows",
            methods=[apigwv2.HttpMethod.GET, apigwv2.HttpMethod.POST],
            integration=api_integration,
        )

        # Workflow routes - single item
        self.api.add_routes(
            path="/workflows/{workflow_id}",
            methods=[
                apigwv2.HttpMethod.GET,
                apigwv2.HttpMethod.PUT,
                apigwv2.HttpMethod.DELETE,
            ],
            integration=api_integration,
        )

        # Execution routes - trigger execution
        self.api.add_routes(
            path="/workflows/{workflow_id}/execute",
            methods=[apigwv2.HttpMethod.POST],
            integration=api_integration,
        )

        # Execution routes - list executions
        self.api.add_routes(
            path="/workflows/{workflow_id}/executions",
            methods=[apigwv2.HttpMethod.GET],
            integration=api_integration,
        )

        # Execution routes - single execution
        self.api.add_routes(
            path="/workflows/{workflow_id}/executions/{execution_id}",
            methods=[apigwv2.HttpMethod.GET],
            integration=api_integration,
        )

        # ---------------------------------------------------------------------
        # Webhook Routes (separate Lambda)
        # ---------------------------------------------------------------------

        webhook_integration = integrations.HttpLambdaIntegration(
            "WebhookIntegration",
            handler=self.webhook_receiver,
        )

        # Webhook receiver - POST /webhook/{workflow_id}
        self.api.add_routes(
            path="/webhook/{workflow_id}",
            methods=[apigwv2.HttpMethod.POST],
            integration=webhook_integration,
        )

        # ---------------------------------------------------------------------
        # Secrets Routes
        # ---------------------------------------------------------------------

        # Secrets collection
        self.api.add_routes(
            path="/secrets",
            methods=[apigwv2.HttpMethod.GET, apigwv2.HttpMethod.POST],
            integration=api_integration,
        )

        # Single secret
        self.api.add_routes(
            path="/secrets/{name}",
            methods=[apigwv2.HttpMethod.DELETE],
            integration=api_integration,
        )
