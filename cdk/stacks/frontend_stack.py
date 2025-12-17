"""Frontend hosting stack for Automation Platform.

Creates:
- S3 bucket for static assets
- CloudFront distribution with OAC
- Route 53 DNS record
- BucketDeployment to upload frontend/dist on deploy
"""

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as cf_origins
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3_deployment
from constructs import Construct


class FrontendStack(Stack):
    """Stack for frontend static hosting.

    Attributes:
        bucket: S3 bucket for frontend assets
        distribution: CloudFront distribution
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        domain_name: str,
        hosted_zone_id: str,
        hosted_zone_name: str,
        certificate_arn: str,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize frontend stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            domain_name: Full domain name (e.g., automations.jurigregg.com)
            hosted_zone_id: Route 53 hosted zone ID
            hosted_zone_name: Route 53 hosted zone name (e.g., jurigregg.com)
            certificate_arn: ACM certificate ARN for SSL
            environment: Deployment environment (dev, staging, prod)
            **kwargs: Additional stack options
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment

        # Import existing certificate
        certificate = acm.Certificate.from_certificate_arn(
            self, "Certificate", certificate_arn
        )

        # Import existing hosted zone
        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self,
            "HostedZone",
            hosted_zone_id=hosted_zone_id,
            zone_name=hosted_zone_name,
        )

        # S3 bucket for frontend assets
        self.bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=f"{environment}-automation-frontend-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN,
            auto_delete_objects=environment == "dev",
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        # CloudFront distribution with S3 origin using OAC (Origin Access Control)
        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=cf_origins.S3BucketOrigin.with_origin_access_control(
                    self.bucket,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
            ),
            domain_names=[domain_name],
            certificate=certificate,
            default_root_object="index.html",
            error_responses=[
                # SPA routing: return index.html for 403 (access denied)
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                # SPA routing: return index.html for 404 (not found)
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,  # North America & Europe only
            http_version=cloudfront.HttpVersion.HTTP2_AND_3,
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
        )

        # Route 53 A record pointing to CloudFront
        route53.ARecord(
            self,
            "AliasRecord",
            zone=hosted_zone,
            record_name=domain_name,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.distribution)
            ),
        )

        # Deploy frontend assets to S3 and invalidate CloudFront
        s3_deployment.BucketDeployment(
            self,
            "DeployFrontend",
            sources=[s3_deployment.Source.asset("../frontend/dist")],
            destination_bucket=self.bucket,
            distribution=self.distribution,
            distribution_paths=["/*"],
        )
