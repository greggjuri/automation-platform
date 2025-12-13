"""Shared resources stack for Automation Platform.

Creates:
- SSM Parameter Store paths for configuration and secrets
- Base IAM policies for Lambda functions
"""

from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class SharedStack(Stack):
    """Stack for shared resources used by multiple components.

    Attributes:
        config_path: SSM path prefix for configuration parameters
        secrets_path: SSM path prefix for secret parameters
        lambda_base_role: Base IAM role for Lambda functions
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize shared stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            environment: Deployment environment (dev, staging, prod)
            **kwargs: Additional stack options
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment

        # SSM parameter path prefixes
        self.config_path = f"/automations/{environment}/config"
        self.secrets_path = f"/automations/{environment}/secrets"

        # Create base configuration parameters
        self._create_config_parameters()

        # Create base IAM role for Lambda functions
        self._create_lambda_base_role()

    def _create_config_parameters(self) -> None:
        """Create base configuration parameters in SSM."""
        # Environment parameter
        ssm.StringParameter(
            self,
            "EnvironmentParam",
            parameter_name=f"{self.config_path}/environment",
            string_value=self.env_name,
            description="Deployment environment",
            tier=ssm.ParameterTier.STANDARD,
        )

        # Log level parameter
        log_level = "DEBUG" if self.env_name == "dev" else "INFO"
        ssm.StringParameter(
            self,
            "LogLevelParam",
            parameter_name=f"{self.config_path}/log_level",
            string_value=log_level,
            description="Default log level for Lambda functions",
            tier=ssm.ParameterTier.STANDARD,
        )

    def _create_lambda_base_role(self) -> None:
        """Create base IAM role that Lambda functions can assume."""
        self.lambda_base_role = iam.Role(
            self,
            "LambdaBaseRole",
            role_name=f"{self.env_name}-automation-lambda-base",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Base role for automation platform Lambda functions",
            managed_policies=[
                # Basic Lambda execution
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                # X-Ray tracing
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSXRayDaemonWriteAccess"
                ),
            ],
        )

        # Allow reading config parameters
        self.lambda_base_role.add_to_policy(
            iam.PolicyStatement(
                sid="ReadConfigParameters",
                effect=iam.Effect.ALLOW,
                actions=[
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:GetParametersByPath",
                ],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter{self.config_path}/*",
                ],
            )
        )

        # Allow reading secrets (with decrypt)
        self.lambda_base_role.add_to_policy(
            iam.PolicyStatement(
                sid="ReadSecretParameters",
                effect=iam.Effect.ALLOW,
                actions=[
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                ],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter{self.secrets_path}/*",
                ],
            )
        )
