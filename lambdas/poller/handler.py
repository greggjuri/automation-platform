"""Poller Lambda handler for polling trigger workflows.

Invoked by EventBridge rules on schedule. Fetches URL content,
detects changes (RSS/Atom new items or HTTP content hash),
and queues workflow execution when changes are found.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import boto3
import feedparser
import requests
from aws_lambda_powertools import Logger, Tracer

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="poller")
tracer = Tracer(service="poller")

# AWS clients
dynamodb = boto3.resource("dynamodb")
sqs_client = boto3.client("sqs")
events_client = boto3.client("events")

# Environment variables
WORKFLOWS_TABLE_NAME = os.environ.get("WORKFLOWS_TABLE_NAME", "dev-Workflows")
POLL_STATE_TABLE_NAME = os.environ.get("POLL_STATE_TABLE_NAME", "dev-PollState")
EXECUTION_QUEUE_URL = os.environ.get("EXECUTION_QUEUE_URL", "")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

# Constants
MAX_CONSECUTIVE_FAILURES = 4
MAX_SEEN_ITEMS = 500
MAX_FEED_ITEMS = 100  # Limit items to process per poll
REQUEST_TIMEOUT = 30
USER_AGENT = "AutomationPlatform-Poller/1.0"


def generate_execution_id() -> str:
    """Generate a ULID-style execution ID.

    Returns:
        Execution ID with 'ex_' prefix
    """
    timestamp = int(time.time() * 1000)
    random_part = random.randint(0, 0xFFFFFFFFFF)
    return f"ex_{timestamp:012x}{random_part:010x}"


def now_iso() -> str:
    """Get current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------------------
# DynamoDB Operations
# -----------------------------------------------------------------------------


@tracer.capture_method
def get_workflow(workflow_id: str) -> dict | None:
    """Fetch workflow from DynamoDB.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Workflow dict or None if not found
    """
    table = dynamodb.Table(WORKFLOWS_TABLE_NAME)
    response = table.get_item(Key={"workflow_id": workflow_id})
    return response.get("Item")


@tracer.capture_method
def get_poll_state(workflow_id: str) -> dict:
    """Fetch poll state from DynamoDB.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Poll state dict (empty dict if not found)
    """
    table = dynamodb.Table(POLL_STATE_TABLE_NAME)
    response = table.get_item(Key={"workflow_id": workflow_id})
    return response.get("Item", {})


@tracer.capture_method
def update_poll_state(workflow_id: str, updates: dict) -> None:
    """Update poll state in DynamoDB.

    Args:
        workflow_id: Workflow identifier
        updates: Fields to update
    """
    table = dynamodb.Table(POLL_STATE_TABLE_NAME)

    # Build update expression
    update_parts = []
    expr_names = {}
    expr_values = {}

    for key, value in updates.items():
        safe_key = f"#{key}"
        value_key = f":{key}"
        update_parts.append(f"{safe_key} = {value_key}")
        expr_names[safe_key] = key
        expr_values[value_key] = value

    table.update_item(
        Key={"workflow_id": workflow_id},
        UpdateExpression="SET " + ", ".join(update_parts),
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


@tracer.capture_method
def disable_workflow(workflow_id: str) -> None:
    """Disable workflow in DynamoDB.

    Args:
        workflow_id: Workflow identifier
    """
    table = dynamodb.Table(WORKFLOWS_TABLE_NAME)
    table.update_item(
        Key={"workflow_id": workflow_id},
        UpdateExpression="SET #enabled = :enabled",
        ExpressionAttributeNames={"#enabled": "enabled"},
        ExpressionAttributeValues={":enabled": False},
    )
    logger.info("Workflow disabled", workflow_id=workflow_id)


# -----------------------------------------------------------------------------
# Feed Parsing
# -----------------------------------------------------------------------------


def parse_feed(content: str) -> list[dict]:
    """Parse RSS/Atom feed and return normalized items.

    Args:
        content: Raw feed content

    Returns:
        List of normalized item dicts with title, link, guid, published, summary
    """
    feed = feedparser.parse(content)
    items = []

    for entry in feed.entries[:MAX_FEED_ITEMS]:
        # Get guid: prefer id, then guid, fallback to link
        guid = entry.get("id") or entry.get("guid")
        if isinstance(guid, dict):
            guid = guid.get("value", "")
        if not guid:
            guid = entry.get("link", "")

        item = {
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "guid": str(guid),
            "published": entry.get("published", ""),
            "summary": (entry.get("summary", "") or "")[:500],
        }
        items.append(item)

    return items


def find_new_items(items: list[dict], seen_ids: list[str]) -> list[dict]:
    """Filter to only items not in seen_ids.

    Args:
        items: List of parsed feed items
        seen_ids: Previously seen item GUIDs

    Returns:
        List of new items not in seen_ids
    """
    seen_set = set(seen_ids)
    return [item for item in items if item["guid"] not in seen_set]


def prune_seen_ids(seen_ids: list[str], new_ids: list[str]) -> list[str]:
    """Add new IDs and prune to MAX_SEEN_ITEMS, keeping most recent.

    Args:
        seen_ids: Current seen IDs list
        new_ids: New IDs to add

    Returns:
        Pruned list with max MAX_SEEN_ITEMS entries
    """
    combined = seen_ids + new_ids
    if len(combined) > MAX_SEEN_ITEMS:
        return combined[-MAX_SEEN_ITEMS:]
    return combined


# -----------------------------------------------------------------------------
# HTTP Content Hashing
# -----------------------------------------------------------------------------


def hash_content(content: str) -> str:
    """Generate SHA256 hash of content.

    Args:
        content: String content to hash

    Returns:
        Hex digest of SHA256 hash
    """
    return hashlib.sha256(content.encode()).hexdigest()


def check_http_changed(content: str, last_hash: str | None) -> tuple[bool, str]:
    """Check if HTTP content has changed.

    Args:
        content: Current content
        last_hash: Previous content hash (None if first check)

    Returns:
        Tuple of (changed, current_hash)
    """
    current_hash = hash_content(content)
    changed = last_hash is None or current_hash != last_hash
    return changed, current_hash


# -----------------------------------------------------------------------------
# URL Fetching
# -----------------------------------------------------------------------------


@tracer.capture_method
def fetch_url(url: str) -> str:
    """Fetch content from URL.

    Args:
        url: URL to fetch

    Returns:
        Response body as string

    Raises:
        requests.RequestException: If request fails
    """
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.text


# -----------------------------------------------------------------------------
# Polling Logic
# -----------------------------------------------------------------------------


@tracer.capture_method
def poll_feed(
    url: str,
    content_type: str,
    poll_state: dict,
) -> tuple[list[dict], dict]:
    """Poll RSS/Atom feed for new items.

    Args:
        url: Feed URL
        content_type: "rss" or "atom"
        poll_state: Current poll state

    Returns:
        Tuple of (new_items, state_updates)
    """
    content = fetch_url(url)
    items = parse_feed(content)

    seen_ids = poll_state.get("seen_item_ids", [])
    new_items = find_new_items(items, seen_ids)

    # Update seen IDs with all current items (not just new ones)
    all_item_ids = [item["guid"] for item in items]
    updated_seen_ids = prune_seen_ids(seen_ids, all_item_ids)

    state_updates = {
        "seen_item_ids": updated_seen_ids,
        "last_checked_at": now_iso(),
        "consecutive_failures": 0,
        "last_error": None,
    }

    logger.info(
        "Feed polled",
        url=url,
        content_type=content_type,
        total_items=len(items),
        new_items=len(new_items),
    )

    return new_items, state_updates


@tracer.capture_method
def poll_http(url: str, poll_state: dict) -> tuple[dict | None, dict]:
    """Poll HTTP URL for content changes.

    Args:
        url: URL to poll
        poll_state: Current poll state

    Returns:
        Tuple of (trigger_data if changed else None, state_updates)
    """
    content = fetch_url(url)
    last_hash = poll_state.get("last_content_hash")

    changed, current_hash = check_http_changed(content, last_hash)

    state_updates = {
        "last_content_hash": current_hash,
        "last_checked_at": now_iso(),
        "consecutive_failures": 0,
        "last_error": None,
    }

    logger.info(
        "HTTP polled",
        url=url,
        changed=changed,
        first_poll=last_hash is None,
    )

    if changed and last_hash is not None:
        # Only trigger on change, not first poll
        trigger_data = {
            "type": "poll",
            "content_type": "http",
            "content": content[:10000],  # Limit content size
            "content_hash": current_hash,
        }
        return trigger_data, state_updates

    return None, state_updates


# -----------------------------------------------------------------------------
# Execution Queueing
# -----------------------------------------------------------------------------


@tracer.capture_method
def queue_execution(
    workflow_id: str,
    trigger_data: dict,
) -> str:
    """Send execution request to SQS queue.

    Args:
        workflow_id: Workflow identifier
        trigger_data: Poll trigger data

    Returns:
        Generated execution ID
    """
    execution_id = generate_execution_id()

    message = {
        "workflow_id": workflow_id,
        "execution_id": execution_id,
        "trigger_type": "poll",
        "trigger_data": trigger_data,
    }

    sqs_client.send_message(
        QueueUrl=EXECUTION_QUEUE_URL,
        MessageBody=json.dumps(message),
    )

    logger.info(
        "Execution queued",
        workflow_id=workflow_id,
        execution_id=execution_id,
    )

    return execution_id


# -----------------------------------------------------------------------------
# Failure Handling
# -----------------------------------------------------------------------------


def get_poll_rule_name(workflow_id: str) -> str:
    """Get EventBridge rule name for poll trigger.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Rule name
    """
    return f"automations-{ENVIRONMENT}-{workflow_id}-poll"


@tracer.capture_method
def disable_eventbridge_rule(workflow_id: str) -> None:
    """Disable EventBridge poll rule.

    Args:
        workflow_id: Workflow identifier
    """
    rule_name = get_poll_rule_name(workflow_id)
    try:
        events_client.disable_rule(Name=rule_name)
        logger.info("EventBridge rule disabled", rule_name=rule_name)
    except events_client.exceptions.ResourceNotFoundException:
        logger.warning("Rule not found", rule_name=rule_name)


@tracer.capture_method
def send_discord_notification(
    workflow_id: str,
    error: str,
    failures: int,
) -> None:
    """Send Discord notification about auto-disabled workflow.

    Args:
        workflow_id: Workflow identifier
        error: Last error message
        failures: Number of consecutive failures
    """
    if not DISCORD_WEBHOOK_URL:
        logger.warning("No DISCORD_WEBHOOK_URL configured, skipping notification")
        return

    try:
        message = (
            f"Workflow `{workflow_id}` auto-disabled after {failures} "
            f"consecutive polling failures.\nLast error: {error[:500]}"
        )

        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": message},
            timeout=10,
        )
        logger.info("Discord notification sent", workflow_id=workflow_id)
    except Exception as e:
        logger.warning("Failed to send Discord notification", error=str(e))


@tracer.capture_method
def handle_failure(
    workflow_id: str,
    poll_state: dict,
    error: str,
) -> None:
    """Handle poll failure, auto-disable after threshold.

    Args:
        workflow_id: Workflow identifier
        poll_state: Current poll state
        error: Error message
    """
    failures = poll_state.get("consecutive_failures", 0) + 1

    logger.warning(
        "Poll failed",
        workflow_id=workflow_id,
        consecutive_failures=failures,
        error=error,
    )

    update_poll_state(
        workflow_id,
        {
            "consecutive_failures": failures,
            "last_error": error[:1000],
            "last_checked_at": now_iso(),
        },
    )

    if failures >= MAX_CONSECUTIVE_FAILURES:
        logger.error(
            "Max failures reached, auto-disabling workflow",
            workflow_id=workflow_id,
            failures=failures,
        )
        disable_workflow(workflow_id)
        disable_eventbridge_rule(workflow_id)
        send_discord_notification(workflow_id, error, failures)


# -----------------------------------------------------------------------------
# Main Handler
# -----------------------------------------------------------------------------


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict[str, Any]:
    """Handle EventBridge scheduled invocation for polling.

    Args:
        event: EventBridge event with workflow_id and time
        context: Lambda context

    Returns:
        Status dict with result information
    """
    workflow_id = event.get("workflow_id")
    scheduled_time = event.get("time")

    logger.info(
        "Poll trigger received",
        workflow_id=workflow_id,
        scheduled_time=scheduled_time,
    )

    # Validate workflow_id
    if not workflow_id:
        logger.error("No workflow_id in event")
        return {"status": "error", "reason": "missing_workflow_id"}

    # Get workflow
    workflow = get_workflow(workflow_id)
    if not workflow:
        logger.warning("Workflow not found", workflow_id=workflow_id)
        return {"status": "skipped", "reason": "workflow_not_found"}

    # Check if enabled
    if not workflow.get("enabled", True):
        logger.info("Workflow disabled, skipping", workflow_id=workflow_id)
        return {"status": "skipped", "reason": "workflow_disabled"}

    # Verify trigger type
    trigger = workflow.get("trigger", {})
    if trigger.get("type") != "poll":
        logger.warning(
            "Workflow trigger type is not poll",
            workflow_id=workflow_id,
            trigger_type=trigger.get("type"),
        )
        return {"status": "skipped", "reason": "not_poll_trigger"}

    # Get poll configuration
    config = trigger.get("config", {})
    url = config.get("url", "")
    content_type = config.get("content_type", "rss")

    if not url:
        logger.error("No URL in poll config", workflow_id=workflow_id)
        return {"status": "error", "reason": "missing_url"}

    # Get current poll state
    poll_state = get_poll_state(workflow_id)

    try:
        if content_type in ("rss", "atom"):
            # Poll RSS/Atom feed
            new_items, state_updates = poll_feed(url, content_type, poll_state)
            update_poll_state(workflow_id, state_updates)

            if new_items:
                trigger_data = {
                    "type": "poll",
                    "content_type": content_type,
                    "items": new_items,
                }
                execution_id = queue_execution(workflow_id, trigger_data)
                return {
                    "status": "triggered",
                    "execution_id": execution_id,
                    "new_items": len(new_items),
                }
            else:
                return {"status": "no_changes", "items_checked": len(state_updates.get("seen_item_ids", []))}

        else:
            # Poll HTTP content
            trigger_data, state_updates = poll_http(url, poll_state)
            update_poll_state(workflow_id, state_updates)

            if trigger_data:
                execution_id = queue_execution(workflow_id, trigger_data)
                return {
                    "status": "triggered",
                    "execution_id": execution_id,
                }
            else:
                return {"status": "no_changes"}

    except requests.RequestException as e:
        handle_failure(workflow_id, poll_state, f"Request failed: {e}")
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        handle_failure(workflow_id, poll_state, f"Unexpected error: {e}")
        logger.exception("Unexpected error during poll")
        return {"status": "failed", "error": str(e)}
