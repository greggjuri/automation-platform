"""Pytest fixtures for poller Lambda tests."""

import os

import pytest

# Set environment variables before importing handler
os.environ["WORKFLOWS_TABLE_NAME"] = "test-Workflows"
os.environ["POLL_STATE_TABLE_NAME"] = "test-PollState"
os.environ["EXECUTION_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.com/api/webhooks/test/test"
os.environ["ENVIRONMENT"] = "test"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def sample_rss_feed():
    """Sample RSS 2.0 feed."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>A test feed</description>
    <item>
      <title>First Article</title>
      <link>https://example.com/article1</link>
      <guid>guid-001</guid>
      <pubDate>Sat, 21 Dec 2025 10:00:00 GMT</pubDate>
      <description>First article summary</description>
    </item>
    <item>
      <title>Second Article</title>
      <link>https://example.com/article2</link>
      <guid>guid-002</guid>
      <pubDate>Sat, 21 Dec 2025 09:00:00 GMT</pubDate>
      <description>Second article summary</description>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def sample_atom_feed():
    """Sample Atom feed."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Atom Feed</title>
  <link href="https://example.com"/>
  <entry>
    <title>Atom Article 1</title>
    <link href="https://example.com/atom1"/>
    <id>urn:uuid:atom-001</id>
    <published>2025-12-21T10:00:00Z</published>
    <summary>Atom article summary</summary>
  </entry>
  <entry>
    <title>Atom Article 2</title>
    <link href="https://example.com/atom2"/>
    <id>urn:uuid:atom-002</id>
    <published>2025-12-21T09:00:00Z</published>
    <summary>Second atom article</summary>
  </entry>
</feed>"""


@pytest.fixture
def sample_atom_feed_no_id():
    """Sample Atom feed without id elements (should fallback to link)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Atom Feed No ID</title>
  <entry>
    <title>Article Without ID</title>
    <link href="https://example.com/no-id-article"/>
    <summary>This entry has no id</summary>
  </entry>
</feed>"""


@pytest.fixture
def sample_workflow():
    """Sample workflow with poll trigger."""
    return {
        "workflow_id": "wf_test123",
        "name": "Test Poll Workflow",
        "enabled": True,
        "trigger": {
            "type": "poll",
            "config": {
                "url": "https://example.com/feed.xml",
                "content_type": "rss",
                "interval_minutes": 15,
            },
        },
        "steps": [],
    }


@pytest.fixture
def sample_poll_state():
    """Sample poll state."""
    return {
        "workflow_id": "wf_test123",
        "seen_item_ids": ["guid-001"],
        "last_checked_at": "2025-12-21T09:00:00Z",
        "consecutive_failures": 0,
        "last_error": None,
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    class MockContext:
        function_name = "test-poller"
        memory_limit_in_mb = 256
        invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-poller"
        aws_request_id = "test-request-id"

    return MockContext()
