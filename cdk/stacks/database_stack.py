"""Database stack for Automation Platform.

Creates DynamoDB tables:
- Workflows: Store workflow definitions
- Executions: Store workflow execution history (with TTL)
- PollState: Track polling trigger state
"""

from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct


class DatabaseStack(Stack):
    """Stack for DynamoDB tables.

    Attributes:
        workflows_table: Table for workflow definitions
        executions_table: Table for execution history
        poll_state_table: Table for polling trigger state
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize database stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            environment: Deployment environment
            **kwargs: Additional stack options
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment

        # Set removal policy based on environment
        removal_policy = (
            RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        )

        # Create tables
        self._create_workflows_table(removal_policy)
        self._create_executions_table(removal_policy)
        self._create_poll_state_table(removal_policy)

    def _create_workflows_table(self, removal_policy: RemovalPolicy) -> None:
        """Create the Workflows table.

        Schema:
        - PK: workflow_id (String)
        """
        self.workflows_table = dynamodb.Table(
            self,
            "WorkflowsTable",
            table_name=f"{self.env_name}-Workflows",
            partition_key=dynamodb.Attribute(
                name="workflow_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            # Stream for reacting to workflow changes (e.g., cron trigger updates)
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

    def _create_executions_table(self, removal_policy: RemovalPolicy) -> None:
        """Create the Executions table.

        Schema:
        - PK: workflow_id (String)
        - SK: execution_id (String, ULID for time-based sorting)
        - GSI: status-started_at-index for querying by status
        - TTL: ttl attribute for automatic cleanup after 90 days
        """
        self.executions_table = dynamodb.Table(
            self,
            "ExecutionsTable",
            table_name=f"{self.env_name}-Executions",
            partition_key=dynamodb.Attribute(
                name="workflow_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="execution_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            # TTL for automatic cleanup
            time_to_live_attribute="ttl",
        )

        # GSI for querying executions by status
        self.executions_table.add_global_secondary_index(
            index_name="status-started_at-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="started_at",
                type=dynamodb.AttributeType.STRING,
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

    def _create_poll_state_table(self, removal_policy: RemovalPolicy) -> None:
        """Create the PollState table.

        Schema:
        - PK: workflow_id (String)

        Stores state for polling triggers to track what has been processed.
        """
        self.poll_state_table = dynamodb.Table(
            self,
            "PollStateTable",
            table_name=f"{self.env_name}-PollState",
            partition_key=dynamodb.Attribute(
                name="workflow_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
        )
