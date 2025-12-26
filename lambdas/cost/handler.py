"""Lambda handler for AWS Cost API endpoint.

This module provides an endpoint to retrieve current month AWS costs
from Cost Explorer, formatted for use in automation workflows.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import boto3
from aws_lambda_powertools import Logger, Tracer
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="cost-api")
tracer = Tracer(service="cost-api")

# Cost Explorer client
ce_client = boto3.client("ce")


# -----------------------------------------------------------------------------
# Cost Retrieval Logic
# -----------------------------------------------------------------------------


def calculate_period() -> tuple[str, str, str]:
    """Calculate the MTD period for Cost Explorer query.

    Returns:
        Tuple of (start_date, end_date, display_end_date)
        - start_date: First day of current month (YYYY-MM-DD)
        - end_date: Tomorrow's date for exclusive end (YYYY-MM-DD)
        - display_end_date: Today's date for display purposes (YYYY-MM-DD)
    """
    today = date.today()
    start_of_month = today.replace(day=1)
    # Cost Explorer End date is EXCLUSIVE, so add 1 day to include today
    end_date = today + timedelta(days=1)

    return (
        start_of_month.isoformat(),
        end_date.isoformat(),
        today.isoformat(),
    )


def format_cost(amount: str | float) -> str:
    """Format cost amount to 2 decimal places.

    Args:
        amount: Cost amount as string or float

    Returns:
        Formatted cost string with 2 decimal places
    """
    return f"{float(amount):.2f}"


@tracer.capture_method
def get_month_to_date_costs() -> dict:
    """Get MTD costs from Cost Explorer.

    Returns:
        Dictionary with period, total_cost, currency, and services breakdown

    Raises:
        ClientError: If Cost Explorer API call fails
    """
    start_date, end_date, display_end_date = calculate_period()

    logger.info(
        "Fetching MTD costs",
        start_date=start_date,
        end_date=end_date,
    )

    response = ce_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date,
            "End": end_date,
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    # Parse results
    services = []
    total_cost = 0.0

    results = response.get("ResultsByTime", [])
    if results:
        groups = results[0].get("Groups", [])
        for group in groups:
            service_name = group["Keys"][0]
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])

            if amount > 0:  # Only include services with non-zero cost
                services.append({
                    "name": service_name,
                    "cost": format_cost(amount),
                    "_sort_cost": amount,  # For sorting, removed from response
                })
                total_cost += amount

    # Sort by cost descending and remove sort key
    services.sort(key=lambda x: x["_sort_cost"], reverse=True)
    for service in services:
        del service["_sort_cost"]

    # Get currency (should always be USD but get from response)
    currency = "USD"
    if results and results[0].get("Groups"):
        currency = results[0]["Groups"][0]["Metrics"]["UnblendedCost"].get(
            "Unit", "USD"
        )

    return {
        "period": {
            "start": start_date,
            "end": display_end_date,
        },
        "total_cost": format_cost(total_cost),
        "currency": currency,
        "services": services,
    }


# -----------------------------------------------------------------------------
# Lambda Handler
# -----------------------------------------------------------------------------


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda entry point for AWS Cost API.

    This handler is invoked by API Gateway HTTP API.

    Args:
        event: API Gateway HTTP API event
        context: Lambda context

    Returns:
        API Gateway HTTP API response with cost data or error
    """
    logger.info("Received request for AWS costs")

    try:
        cost_data = get_month_to_date_costs()

        logger.info(
            "Cost data retrieved",
            total_cost=cost_data["total_cost"],
            service_count=len(cost_data["services"]),
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": _json_dumps(cost_data),
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]

        logger.exception(
            "Cost Explorer API error",
            error_code=error_code,
            error_message=error_message,
        )

        status_code = 429 if "Throttl" in error_code else 500

        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": _json_dumps({
                "error": error_code,
                "message": error_message,
            }),
        }

    except Exception as e:
        logger.exception("Unexpected error", error=str(e))

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": _json_dumps({
                "error": "InternalError",
                "message": str(e),
            }),
        }


def _json_dumps(obj: dict) -> str:
    """Serialize dict to JSON string.

    Args:
        obj: Dictionary to serialize

    Returns:
        JSON string
    """
    import json
    return json.dumps(obj)
