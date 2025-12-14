"""Execution Stack for Automation Platform.

Creates:
- SQS execution queue and DLQ
- Step Functions Express state machine
- Execution Starter Lambda (SQS consumer)
- Action Lambdas (HTTP Request, Transform, Log)
"""

import os

from aws_cdk import BundlingOptions, CfnOutput, DockerVolume, Duration, RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_lambda_event_sources as lambda_events
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct

# Path to lambdas directory (used for shared module)
LAMBDAS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "lambdas")


class ExecutionStack(Stack):
    """CDK Stack for workflow execution engine.

    Attributes:
        execution_queue: SQS queue for execution requests
        state_machine: Step Functions Express state machine
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        workflows_table: dynamodb.ITable,
        executions_table: dynamodb.ITable,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize the execution stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            workflows_table: DynamoDB Workflows table
            executions_table: DynamoDB Executions table
            environment: Deployment environment
            **kwargs: Additional stack options
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment
        self.workflows_table = workflows_table
        self.executions_table = executions_table

        # Create SQS queues
        self._create_queues()

        # Create action Lambdas first (needed for state machine)
        self._create_action_lambdas()

        # Create Step Functions state machine
        self._create_state_machine()

        # Create execution starter Lambda
        self._create_execution_starter()

        # Output queue URL for API to send messages
        CfnOutput(
            self,
            "ExecutionQueueUrl",
            value=self.execution_queue.queue_url,
            description="SQS Queue URL for execution requests",
            export_name=f"{environment}-automation-execution-queue-url",
        )

        CfnOutput(
            self,
            "StateMachineArn",
            value=self.state_machine.state_machine_arn,
            description="Step Functions state machine ARN",
            export_name=f"{environment}-automation-state-machine-arn",
        )

    def _create_queues(self) -> None:
        """Create SQS execution queue and DLQ."""
        # Dead letter queue for failed messages
        self.execution_dlq = sqs.Queue(
            self,
            "ExecutionDLQ",
            queue_name=f"{self.env_name}-automation-execution-dlq",
            retention_period=Duration.days(14),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Main execution queue
        self.execution_queue = sqs.Queue(
            self,
            "ExecutionQueue",
            queue_name=f"{self.env_name}-automation-execution-queue",
            visibility_timeout=Duration.seconds(330),  # > 5 min Step Functions max
            retention_period=Duration.days(4),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.execution_dlq,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _create_lambda_with_logs(
        self,
        id_suffix: str,
        description: str,
        code_path: str,
        handler: str = "handler.handler",
        memory_size: int = 256,
        timeout_seconds: int = 30,
        environment: dict | None = None,
    ) -> lambda_.Function:
        """Create a Lambda function with log group.

        Args:
            id_suffix: Suffix for construct IDs
            description: Lambda description
            code_path: Path to Lambda code relative to lambdas/
            handler: Handler function path
            memory_size: Memory in MB
            timeout_seconds: Timeout in seconds
            environment: Additional environment variables

        Returns:
            The Lambda function
        """
        function_name = f"{self.env_name}-automation-{id_suffix}"

        # Create log group
        log_group = logs.LogGroup(
            self,
            f"{id_suffix}Logs",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Base environment variables
        env_vars = {
            "ENVIRONMENT": self.env_name,
            "POWERTOOLS_SERVICE_NAME": f"automation-{id_suffix}",
            "POWERTOOLS_LOG_LEVEL": "INFO" if self.env_name == "prod" else "DEBUG",
        }
        if environment:
            env_vars.update(environment)

        # Resolve absolute path to shared module for Docker volume mount
        shared_path = os.path.abspath(os.path.join(LAMBDAS_DIR, "shared"))

        # Create Lambda function
        return lambda_.Function(
            self,
            id_suffix,
            function_name=function_name,
            description=description,
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler=handler,
            code=lambda_.Code.from_asset(
                path=os.path.join(LAMBDAS_DIR, code_path),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    volumes=[
                        DockerVolume(
                            host_path=shared_path,
                            container_path="/shared",
                        )
                    ],
                    command=[
                        "bash",
                        "-c",
                        # Copy shared module from mounted volume, install requirements, copy Lambda code
                        "cp -r /shared /asset-output/shared && "
                        "pip install -r requirements.txt -t /asset-output && "
                        "cp -r . /asset-output",
                    ],
                ),
            ),
            memory_size=memory_size,
            timeout=Duration.seconds(timeout_seconds),
            environment=env_vars,
            log_group=log_group,
            tracing=lambda_.Tracing.ACTIVE,
        )

    def _create_action_lambdas(self) -> None:
        """Create action Lambda functions."""
        # HTTP Request action
        self.http_request_lambda = self._create_lambda_with_logs(
            id_suffix="action-http-request",
            description="Executes HTTP requests for workflow steps",
            code_path="action_http_request",
            timeout_seconds=60,  # Allow longer for HTTP calls
            environment={
                "EXECUTIONS_TABLE_NAME": self.executions_table.table_name,
            },
        )
        self.executions_table.grant_read_write_data(self.http_request_lambda)

        # Transform action
        self.transform_lambda = self._create_lambda_with_logs(
            id_suffix="action-transform",
            description="Transforms data using templates",
            code_path="action_transform",
            environment={
                "EXECUTIONS_TABLE_NAME": self.executions_table.table_name,
            },
        )
        self.executions_table.grant_read_write_data(self.transform_lambda)

        # Log action
        self.log_lambda = self._create_lambda_with_logs(
            id_suffix="action-log",
            description="Logs messages for workflow debugging",
            code_path="action_log",
            environment={
                "EXECUTIONS_TABLE_NAME": self.executions_table.table_name,
            },
        )
        self.executions_table.grant_read_write_data(self.log_lambda)

    def _create_state_machine(self) -> None:
        """Create Step Functions Express state machine.

        Uses Map state to iterate over workflow steps, which is more
        compatible with CDK and handles dynamic array access properly.
        """
        # Initialize execution state
        initialize = sfn.Pass(
            self,
            "InitializeExecution",
            parameters={
                "execution_id.$": "$.execution_id",
                "workflow_id.$": "$.workflow_id",
                "workflow.$": "$.workflow",
                "trigger_data.$": "$.trigger_data",
                "context.$": "$.context",
            },
        )

        # HTTP Request action task
        http_request_task = tasks.LambdaInvoke(
            self,
            "ExecuteHttpRequest",
            lambda_function=self.http_request_lambda,
            result_path="$.step_result",
            payload_response_only=True,
        )

        # Transform action task
        transform_task = tasks.LambdaInvoke(
            self,
            "ExecuteTransform",
            lambda_function=self.transform_lambda,
            result_path="$.step_result",
            payload_response_only=True,
        )

        # Log action task
        log_task = tasks.LambdaInvoke(
            self,
            "ExecuteLog",
            lambda_function=self.log_lambda,
            result_path="$.step_result",
            payload_response_only=True,
        )

        # Success state for unknown types (skip)
        skip_unknown = sfn.Pass(
            self,
            "SkipUnknownType",
            parameters={
                "status": "skipped",
                "error": "Unknown step type",
            },
            result_path="$.step_result",
        )

        # Route by step type
        route_by_type = sfn.Choice(self, "RouteByStepType")
        route_by_type.when(
            sfn.Condition.string_equals("$.step.action", "http_request"),
            http_request_task,
        )
        route_by_type.when(
            sfn.Condition.string_equals("$.step.action", "transform"),
            transform_task,
        )
        route_by_type.when(
            sfn.Condition.string_equals("$.step.action", "log"),
            log_task,
        )
        route_by_type.otherwise(skip_unknown)

        # Collect result pass state
        collect_result = sfn.Pass(
            self,
            "CollectStepResult",
            parameters={
                "step_name.$": "$.step.name",
                "status.$": "$.step_result.status",
                "output.$": "$.step_result.output",
            },
        )

        # Chain step execution
        http_request_task.next(collect_result)
        transform_task.next(collect_result)
        log_task.next(collect_result)
        skip_unknown.next(collect_result)

        # Map state to iterate over all steps
        process_steps = sfn.Map(
            self,
            "ProcessAllSteps",
            items_path="$.workflow.steps",
            parameters={
                "step.$": "$$.Map.Item.Value",
                "step_index.$": "$$.Map.Item.Index",
                "execution_id.$": "$.execution_id",
                "workflow_id.$": "$.workflow_id",
                "context.$": "$.context",
            },
            result_path="$.step_results",
        )
        process_steps.item_processor(route_by_type)

        # Success state
        execution_success = sfn.Succeed(
            self,
            "ExecutionSuccess",
        )

        # Build the definition
        definition = initialize.next(process_steps).next(execution_success)

        # Create the state machine
        self.state_machine = sfn.StateMachine(
            self,
            "WorkflowExecutor",
            state_machine_name=f"{self.env_name}-automation-executor",
            state_machine_type=sfn.StateMachineType.EXPRESS,
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            tracing_enabled=True,
            logs=sfn.LogOptions(
                destination=logs.LogGroup(
                    self,
                    "StateMachineLogs",
                    log_group_name=f"/aws/states/{self.env_name}-automation-executor",
                    retention=logs.RetentionDays.TWO_WEEKS,
                    removal_policy=RemovalPolicy.DESTROY,
                ),
                level=sfn.LogLevel.ALL,
            ),
        )

    def _create_execution_starter(self) -> None:
        """Create the execution starter Lambda that consumes SQS."""
        self.execution_starter = self._create_lambda_with_logs(
            id_suffix="execution-starter",
            description="Starts workflow executions from SQS queue",
            code_path="execution_starter",
            timeout_seconds=60,
            environment={
                "WORKFLOWS_TABLE_NAME": self.workflows_table.table_name,
                "EXECUTIONS_TABLE_NAME": self.executions_table.table_name,
                "STATE_MACHINE_ARN": self.state_machine.state_machine_arn,
                "SSM_SECRETS_PATH": f"/automation/{self.env_name}/secrets",
            },
        )

        # Grant permissions
        self.workflows_table.grant_read_data(self.execution_starter)
        self.executions_table.grant_read_write_data(self.execution_starter)
        self.state_machine.grant_start_sync_execution(self.execution_starter)

        # Grant SSM read permissions for secrets
        self.execution_starter.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParametersByPath", "ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/automation/{self.env_name}/secrets/*"
                ],
            )
        )

        # Add SQS trigger
        self.execution_starter.add_event_source(
            lambda_events.SqsEventSource(
                self.execution_queue,
                batch_size=1,  # Process one execution at a time
            )
        )
