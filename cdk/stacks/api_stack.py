"""API Stack for Automation Platform.

Creates:
- Lambda function for API handling
- HTTP API Gateway with CORS
- Routes for workflow CRUD operations
- CloudWatch log group
"""

import os

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct


class ApiStack(Stack):
    """CDK Stack for API Gateway and Lambda function.

    Attributes:
        api: The HTTP API Gateway
        api_handler: The Lambda function handling requests
        api_url: The API endpoint URL
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        workflows_table: dynamodb.ITable,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize the API stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            workflows_table: DynamoDB table for workflows
            environment: Deployment environment (dev, staging, prod)
            **kwargs: Additional stack options
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment

        # Create Lambda function
        self._create_lambda(workflows_table)

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

        # Lambda function for API handling
        self.api_handler = lambda_.Function(
            self,
            "ApiHandler",
            function_name=f"{self.env_name}-automation-api-handler",
            description="Handles API Gateway requests for workflow operations",
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
            environment={
                "TABLE_NAME": workflows_table.table_name,
                "ENVIRONMENT": self.env_name,
                "POWERTOOLS_SERVICE_NAME": "automation-api",
                "POWERTOOLS_LOG_LEVEL": "INFO" if self.env_name == "prod" else "DEBUG",
                "POWERTOOLS_METRICS_NAMESPACE": "AutomationPlatform",
            },
            # Logging
            log_group=log_group,
            # Tracing
            tracing=lambda_.Tracing.ACTIVE,
        )

        # Grant DynamoDB read/write permissions
        workflows_table.grant_read_write_data(self.api_handler)

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
