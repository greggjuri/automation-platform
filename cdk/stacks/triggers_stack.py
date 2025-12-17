"""Triggers Stack for Automation Platform.

Creates:
- Cron Handler Lambda (invoked by EventBridge schedules)

EventBridge rules are created dynamically by the API Lambda when
workflows with cron triggers are saved.
"""

import os

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sqs as sqs
from constructs import Construct


class TriggersStack(Stack):
    """CDK Stack for trigger infrastructure.

    Attributes:
        cron_handler: Lambda function invoked by EventBridge cron rules
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        workflows_table: dynamodb.ITable,
        execution_queue: sqs.IQueue,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize the triggers stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            workflows_table: DynamoDB Workflows table
            execution_queue: SQS queue for execution requests
            environment: Deployment environment
            **kwargs: Additional stack options
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment
        self.workflows_table = workflows_table
        self.execution_queue = execution_queue

        # Create cron handler Lambda
        self._create_cron_handler()

        # Export ARN for API Lambda to use when creating EventBridge rules
        CfnOutput(
            self,
            "CronHandlerArn",
            value=self.cron_handler.function_arn,
            description="Cron Handler Lambda ARN for EventBridge targets",
            export_name=f"{environment}-automation-cron-handler-arn",
        )

    def _create_cron_handler(self) -> None:
        """Create the cron handler Lambda function."""
        function_name = f"{self.env_name}-automation-cron-handler"

        # Create log group
        log_group = logs.LogGroup(
            self,
            "CronHandlerLogs",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Environment variables
        env_vars = {
            "WORKFLOWS_TABLE_NAME": self.workflows_table.table_name,
            "EXECUTION_QUEUE_URL": self.execution_queue.queue_url,
            "ENVIRONMENT": self.env_name,
            "POWERTOOLS_SERVICE_NAME": "cron-handler",
            "POWERTOOLS_LOG_LEVEL": "INFO" if self.env_name == "prod" else "DEBUG",
        }

        # Path to lambdas directory
        lambdas_dir = os.path.join(os.path.dirname(__file__), "..", "..", "lambdas")

        # Create Lambda function
        self.cron_handler = lambda_.Function(
            self,
            "CronHandler",
            function_name=function_name,
            description="Handles EventBridge scheduled triggers for workflows",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                path=os.path.join(lambdas_dir, "cron_handler"),
                bundling={
                    "image": lambda_.Runtime.PYTHON_3_11.bundling_image,
                    "command": [
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r . /asset-output",
                    ],
                },
            ),
            memory_size=256,
            timeout=Duration.seconds(10),  # Quick validation and queue
            environment=env_vars,
            log_group=log_group,
            tracing=lambda_.Tracing.ACTIVE,
        )

        # Grant DynamoDB read permissions (only need to check workflow)
        self.workflows_table.grant_read_data(self.cron_handler)

        # Grant SQS send permissions
        self.execution_queue.grant_send_messages(self.cron_handler)

        # Grant EventBridge permission to invoke this Lambda
        # This is needed for EventBridge rules to invoke the function
        self.cron_handler.add_permission(
            "EventBridgeInvoke",
            principal=iam.ServicePrincipal("events.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=self.account,
        )
