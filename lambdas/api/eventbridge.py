"""EventBridge rule management for cron and poll triggers.

This module provides utilities to create, update, and delete
EventBridge rules when workflows with cron or poll triggers are saved.
"""

from __future__ import annotations

import json
import os

import boto3
from aws_lambda_powertools import Logger

logger = Logger(child=True)

# AWS clients
events_client = boto3.client("events")

# Environment variables
ENV = os.environ.get("ENVIRONMENT", "dev")
CRON_HANDLER_ARN = os.environ.get("CRON_HANDLER_LAMBDA_ARN", "")
POLLER_ARN = os.environ.get("POLLER_LAMBDA_ARN", "")


def get_rule_name(workflow_id: str) -> str:
    """Generate EventBridge rule name from workflow ID.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Rule name following naming convention
    """
    return f"automations-{ENV}-{workflow_id}-schedule"


def create_schedule_rule(workflow_id: str, schedule: str) -> None:
    """Create or update EventBridge rule for cron trigger.

    This is idempotent - calling it multiple times with the same
    workflow_id will update the existing rule.

    Args:
        workflow_id: Workflow identifier
        schedule: EventBridge schedule expression (cron or rate)

    Raises:
        ValueError: If CRON_HANDLER_LAMBDA_ARN is not configured
        ClientError: If EventBridge API call fails
    """
    if not CRON_HANDLER_ARN:
        logger.error("CRON_HANDLER_LAMBDA_ARN not configured")
        raise ValueError("Cron handler Lambda ARN not configured")

    rule_name = get_rule_name(workflow_id)

    logger.info(
        "Creating EventBridge rule",
        rule_name=rule_name,
        schedule=schedule,
        workflow_id=workflow_id,
    )

    # Create/update rule
    # EventBridge requires cron expressions wrapped in cron()
    schedule_expression = f"cron({schedule})"
    events_client.put_rule(
        Name=rule_name,
        ScheduleExpression=schedule_expression,
        State="ENABLED",
        Description=f"Cron trigger for workflow {workflow_id}",
    )

    # Set target to cron handler Lambda
    # Use InputTransformer to include EventBridge time in the event
    events_client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "cron-handler",
                "Arn": CRON_HANDLER_ARN,
                "InputTransformer": {
                    "InputPathsMap": {
                        "time": "$.time",
                    },
                    "InputTemplate": json.dumps({
                        "workflow_id": workflow_id,
                        "source": "eventbridge-schedule",
                        "time": "<time>",
                    }).replace('"<time>"', '<time>'),  # InputTemplate uses <var> without quotes for strings
                },
            }
        ],
    )

    logger.info("EventBridge rule created/updated", rule_name=rule_name)


def enable_schedule_rule(workflow_id: str) -> None:
    """Enable the EventBridge rule for a cron workflow.

    This is idempotent - enabling an already-enabled rule has no effect.

    Args:
        workflow_id: Workflow identifier
    """
    rule_name = get_rule_name(workflow_id)

    logger.info(
        "Enabling EventBridge rule",
        rule_name=rule_name,
        workflow_id=workflow_id,
    )

    try:
        events_client.enable_rule(Name=rule_name)
        logger.info("EventBridge rule enabled", rule_name=rule_name)
    except events_client.exceptions.ResourceNotFoundException:
        logger.warning("Rule not found, cannot enable", rule_name=rule_name)


def disable_schedule_rule(workflow_id: str) -> None:
    """Disable the EventBridge rule for a cron workflow.

    This is idempotent - disabling an already-disabled rule has no effect.
    The rule is not deleted, just disabled.

    Args:
        workflow_id: Workflow identifier
    """
    rule_name = get_rule_name(workflow_id)

    logger.info(
        "Disabling EventBridge rule",
        rule_name=rule_name,
        workflow_id=workflow_id,
    )

    try:
        events_client.disable_rule(Name=rule_name)
        logger.info("EventBridge rule disabled", rule_name=rule_name)
    except events_client.exceptions.ResourceNotFoundException:
        logger.warning("Rule not found, cannot disable", rule_name=rule_name)


def delete_schedule_rule(workflow_id: str) -> None:
    """Delete EventBridge rule for workflow.

    This is idempotent - calling it for a non-existent rule
    will not raise an error.

    Args:
        workflow_id: Workflow identifier
    """
    rule_name = get_rule_name(workflow_id)

    logger.info(
        "Deleting EventBridge rule",
        rule_name=rule_name,
        workflow_id=workflow_id,
    )

    try:
        # Remove targets first (required before deleting rule)
        events_client.remove_targets(
            Rule=rule_name,
            Ids=["cron-handler"],
        )
    except events_client.exceptions.ResourceNotFoundException:
        logger.info("Rule not found, skipping target removal", rule_name=rule_name)
        return

    try:
        events_client.delete_rule(Name=rule_name)
        logger.info("EventBridge rule deleted", rule_name=rule_name)
    except events_client.exceptions.ResourceNotFoundException:
        logger.info("Rule already deleted", rule_name=rule_name)


# -----------------------------------------------------------------------------
# Poll Trigger Functions
# -----------------------------------------------------------------------------


def get_poll_rule_name(workflow_id: str) -> str:
    """Generate EventBridge rule name for poll trigger.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Rule name following naming convention
    """
    return f"automations-{ENV}-{workflow_id}-poll"


def create_poll_rule(workflow_id: str, interval_minutes: int) -> None:
    """Create or update EventBridge rule for poll trigger.

    This is idempotent - calling it multiple times with the same
    workflow_id will update the existing rule.

    Args:
        workflow_id: Workflow identifier
        interval_minutes: Polling interval in minutes (minimum 5)

    Raises:
        ValueError: If POLLER_LAMBDA_ARN is not configured
        ClientError: If EventBridge API call fails
    """
    if not POLLER_ARN:
        logger.error("POLLER_LAMBDA_ARN not configured")
        raise ValueError("Poller Lambda ARN not configured")

    rule_name = get_poll_rule_name(workflow_id)

    # Ensure minimum interval
    interval = max(interval_minutes, 5)

    # Build schedule expression
    schedule = f"rate({interval} minutes)" if interval > 1 else "rate(1 minute)"

    logger.info(
        "Creating poll EventBridge rule",
        rule_name=rule_name,
        interval_minutes=interval,
        workflow_id=workflow_id,
    )

    # Create/update rule
    events_client.put_rule(
        Name=rule_name,
        ScheduleExpression=schedule,
        State="ENABLED",
        Description=f"Polling trigger for workflow {workflow_id}",
    )

    # Set target to poller Lambda
    # Use InputTransformer to include EventBridge time in the event
    events_client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "poller",
                "Arn": POLLER_ARN,
                "InputTransformer": {
                    "InputPathsMap": {
                        "time": "$.time",
                    },
                    "InputTemplate": json.dumps({
                        "workflow_id": workflow_id,
                        "time": "<time>",
                    }).replace('"<time>"', '<time>'),
                },
            }
        ],
    )

    logger.info("Poll EventBridge rule created/updated", rule_name=rule_name)


def enable_poll_rule(workflow_id: str) -> None:
    """Enable the EventBridge rule for a poll workflow.

    This is idempotent - enabling an already-enabled rule has no effect.

    Args:
        workflow_id: Workflow identifier
    """
    rule_name = get_poll_rule_name(workflow_id)

    logger.info(
        "Enabling poll EventBridge rule",
        rule_name=rule_name,
        workflow_id=workflow_id,
    )

    try:
        events_client.enable_rule(Name=rule_name)
        logger.info("Poll EventBridge rule enabled", rule_name=rule_name)
    except events_client.exceptions.ResourceNotFoundException:
        logger.warning("Poll rule not found, cannot enable", rule_name=rule_name)


def disable_poll_rule(workflow_id: str) -> None:
    """Disable the EventBridge rule for a poll workflow.

    This is idempotent - disabling an already-disabled rule has no effect.
    The rule is not deleted, just disabled.

    Args:
        workflow_id: Workflow identifier
    """
    rule_name = get_poll_rule_name(workflow_id)

    logger.info(
        "Disabling poll EventBridge rule",
        rule_name=rule_name,
        workflow_id=workflow_id,
    )

    try:
        events_client.disable_rule(Name=rule_name)
        logger.info("Poll EventBridge rule disabled", rule_name=rule_name)
    except events_client.exceptions.ResourceNotFoundException:
        logger.warning("Poll rule not found, cannot disable", rule_name=rule_name)


def delete_poll_rule(workflow_id: str) -> None:
    """Delete EventBridge poll rule for workflow.

    This is idempotent - calling it for a non-existent rule
    will not raise an error.

    Args:
        workflow_id: Workflow identifier
    """
    rule_name = get_poll_rule_name(workflow_id)

    logger.info(
        "Deleting poll EventBridge rule",
        rule_name=rule_name,
        workflow_id=workflow_id,
    )

    try:
        # Remove targets first (required before deleting rule)
        events_client.remove_targets(
            Rule=rule_name,
            Ids=["poller"],
        )
    except events_client.exceptions.ResourceNotFoundException:
        logger.info("Poll rule not found, skipping target removal", rule_name=rule_name)
        return

    try:
        events_client.delete_rule(Name=rule_name)
        logger.info("Poll EventBridge rule deleted", rule_name=rule_name)
    except events_client.exceptions.ResourceNotFoundException:
        logger.info("Poll rule already deleted", rule_name=rule_name)


# -----------------------------------------------------------------------------
# Unified Rule Sync
# -----------------------------------------------------------------------------


def sync_workflow_rule(
    workflow_id: str,
    old_trigger: dict | None,
    new_trigger: dict | None,
) -> None:
    """Sync EventBridge rules based on workflow trigger changes.

    Handles all trigger change scenarios for both cron and poll triggers:
    - Non-scheduled to scheduled: Create rule
    - Scheduled to scheduled (same type): Update rule
    - Scheduled to different type: Delete old, create new
    - Scheduled to non-scheduled: Delete rule
    - Non-scheduled to non-scheduled: No action

    Args:
        workflow_id: Workflow identifier
        old_trigger: Previous trigger configuration (None for new workflow)
        new_trigger: New trigger configuration (None for deleted workflow)
    """
    old_type = (old_trigger or {}).get("type")
    new_type = (new_trigger or {}).get("type")

    # Handle cron triggers
    old_is_cron = old_type == "cron"
    new_is_cron = new_type == "cron"

    if new_is_cron:
        schedule = (new_trigger or {}).get("config", {}).get("schedule", "")
        if schedule:
            create_schedule_rule(workflow_id, schedule)
        else:
            logger.warning(
                "Cron trigger missing schedule, skipping rule creation",
                workflow_id=workflow_id,
            )
    elif old_is_cron:
        delete_schedule_rule(workflow_id)

    # Handle poll triggers
    old_is_poll = old_type == "poll"
    new_is_poll = new_type == "poll"

    if new_is_poll:
        interval = (new_trigger or {}).get("config", {}).get("interval_minutes", 15)
        url = (new_trigger or {}).get("config", {}).get("url", "")
        if url:
            create_poll_rule(workflow_id, interval)
        else:
            logger.warning(
                "Poll trigger missing URL, skipping rule creation",
                workflow_id=workflow_id,
            )
    elif old_is_poll:
        delete_poll_rule(workflow_id)


def sync_workflow_enabled(
    workflow_id: str,
    trigger: dict | None,
    enabled: bool,
) -> None:
    """Enable or disable EventBridge rule based on workflow enabled state.

    Args:
        workflow_id: Workflow identifier
        trigger: Trigger configuration
        enabled: Whether the workflow is enabled
    """
    trigger_type = (trigger or {}).get("type")

    if trigger_type == "cron":
        if enabled:
            enable_schedule_rule(workflow_id)
        else:
            disable_schedule_rule(workflow_id)
    elif trigger_type == "poll":
        if enabled:
            enable_poll_rule(workflow_id)
        else:
            disable_poll_rule(workflow_id)
