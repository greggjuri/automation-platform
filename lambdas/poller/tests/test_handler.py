"""Unit tests for poller Lambda handler."""

from unittest.mock import MagicMock, patch



class TestParseFeed:
    """Tests for parse_feed function."""

    def test_parse_rss_feed(self, sample_rss_feed):
        """Test parsing standard RSS 2.0 feed."""
        from handler import parse_feed

        items = parse_feed(sample_rss_feed)

        assert len(items) == 2
        assert items[0]["title"] == "First Article"
        assert items[0]["link"] == "https://example.com/article1"
        assert items[0]["guid"] == "guid-001"
        assert items[1]["guid"] == "guid-002"

    def test_parse_atom_feed(self, sample_atom_feed):
        """Test parsing Atom feed with id elements."""
        from handler import parse_feed

        items = parse_feed(sample_atom_feed)

        assert len(items) == 2
        assert items[0]["title"] == "Atom Article 1"
        assert items[0]["link"] == "https://example.com/atom1"
        assert items[0]["guid"] == "urn:uuid:atom-001"

    def test_parse_atom_feed_fallback_link(self, sample_atom_feed_no_id):
        """Test fallback to link when no id element."""
        from handler import parse_feed

        items = parse_feed(sample_atom_feed_no_id)

        assert len(items) == 1
        assert items[0]["guid"] == "https://example.com/no-id-article"

    def test_parse_empty_feed(self):
        """Test parsing empty feed."""
        from handler import parse_feed

        items = parse_feed("<rss><channel></channel></rss>")
        assert items == []


class TestFindNewItems:
    """Tests for find_new_items function."""

    def test_find_new_items(self):
        """Test filtering to only new items."""
        from handler import find_new_items

        items = [
            {"guid": "id1", "title": "Article 1"},
            {"guid": "id2", "title": "Article 2"},
            {"guid": "id3", "title": "Article 3"},
        ]
        seen_ids = ["id1", "id3"]

        new_items = find_new_items(items, seen_ids)

        assert len(new_items) == 1
        assert new_items[0]["guid"] == "id2"

    def test_find_new_items_all_new(self):
        """Test when all items are new."""
        from handler import find_new_items

        items = [{"guid": "id1"}, {"guid": "id2"}]
        seen_ids = []

        new_items = find_new_items(items, seen_ids)

        assert len(new_items) == 2

    def test_find_new_items_none_new(self):
        """Test when no items are new."""
        from handler import find_new_items

        items = [{"guid": "id1"}, {"guid": "id2"}]
        seen_ids = ["id1", "id2", "id3"]

        new_items = find_new_items(items, seen_ids)

        assert len(new_items) == 0


class TestPruneSeenIds:
    """Tests for prune_seen_ids function."""

    def test_prune_seen_ids_under_limit(self):
        """Test pruning when under limit."""
        from handler import prune_seen_ids

        seen_ids = ["id1", "id2"]
        new_ids = ["id3"]

        result = prune_seen_ids(seen_ids, new_ids)

        assert result == ["id1", "id2", "id3"]

    def test_prune_seen_ids_over_limit(self):
        """Test pruning when over limit."""
        from handler import MAX_SEEN_ITEMS, prune_seen_ids

        # Create list just under limit
        seen_ids = [f"id{i}" for i in range(MAX_SEEN_ITEMS - 1)]
        new_ids = ["new1", "new2", "new3"]

        result = prune_seen_ids(seen_ids, new_ids)

        assert len(result) == MAX_SEEN_ITEMS
        # Should keep most recent (end of list)
        assert result[-1] == "new3"
        assert result[-2] == "new2"
        assert result[-3] == "new1"


class TestHashContent:
    """Tests for hash_content function."""

    def test_hash_content(self):
        """Test SHA256 hashing."""
        from handler import hash_content

        hash1 = hash_content("hello world")
        hash2 = hash_content("hello world")
        hash3 = hash_content("different content")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA256 hex length


class TestCheckHttpChanged:
    """Tests for check_http_changed function."""

    def test_check_http_changed_first_poll(self):
        """Test first poll (no previous hash)."""
        from handler import check_http_changed

        changed, new_hash = check_http_changed("content", None)

        assert changed is True
        assert len(new_hash) == 64

    def test_check_http_changed_no_change(self):
        """Test when content unchanged."""
        from handler import check_http_changed, hash_content

        content = "same content"
        previous_hash = hash_content(content)

        changed, new_hash = check_http_changed(content, previous_hash)

        assert changed is False
        assert new_hash == previous_hash

    def test_check_http_changed_with_change(self):
        """Test when content changed."""
        from handler import check_http_changed

        previous_hash = "old_hash_value_here_abcdef1234567890"

        changed, new_hash = check_http_changed("new content", previous_hash)

        assert changed is True
        assert new_hash != previous_hash


class TestHandlerSkipConditions:
    """Tests for handler skip conditions."""

    @patch("handler.get_workflow")
    def test_skip_missing_workflow_id(self, mock_get_workflow, lambda_context):
        """Test skip when workflow_id missing."""
        from handler import handler

        result = handler({"time": "2025-12-21T10:00:00Z"}, lambda_context)

        assert result["status"] == "error"
        assert result["reason"] == "missing_workflow_id"
        mock_get_workflow.assert_not_called()

    @patch("handler.get_workflow")
    def test_skip_workflow_not_found(self, mock_get_workflow, lambda_context):
        """Test skip when workflow not found."""
        from handler import handler

        mock_get_workflow.return_value = None

        result = handler(
            {"workflow_id": "wf_missing", "time": "2025-12-21T10:00:00Z"},
            lambda_context,
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "workflow_not_found"

    @patch("handler.get_workflow")
    def test_skip_disabled_workflow(self, mock_get_workflow, lambda_context):
        """Test skip when workflow is disabled."""
        from handler import handler

        mock_get_workflow.return_value = {
            "workflow_id": "wf_test",
            "enabled": False,
            "trigger": {"type": "poll"},
        }

        result = handler(
            {"workflow_id": "wf_test", "time": "2025-12-21T10:00:00Z"},
            lambda_context,
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "workflow_disabled"

    @patch("handler.get_workflow")
    def test_skip_wrong_trigger_type(self, mock_get_workflow, lambda_context):
        """Test skip when trigger type is not poll."""
        from handler import handler

        mock_get_workflow.return_value = {
            "workflow_id": "wf_test",
            "enabled": True,
            "trigger": {"type": "cron"},
        }

        result = handler(
            {"workflow_id": "wf_test", "time": "2025-12-21T10:00:00Z"},
            lambda_context,
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "not_poll_trigger"


class TestFailureHandling:
    """Tests for failure handling."""

    @patch("handler.send_discord_notification")
    @patch("handler.disable_eventbridge_rule")
    @patch("handler.disable_workflow")
    @patch("handler.update_poll_state")
    def test_handle_failure_increments_counter(
        self, mock_update_state, mock_disable_wf, mock_disable_rule, mock_discord
    ):
        """Test that failure counter increments."""
        from handler import handle_failure

        poll_state = {"consecutive_failures": 1}

        handle_failure("wf_test", poll_state, "Connection error")

        mock_update_state.assert_called_once()
        call_args = mock_update_state.call_args[0]
        assert call_args[1]["consecutive_failures"] == 2
        mock_disable_wf.assert_not_called()

    @patch("handler.send_discord_notification")
    @patch("handler.disable_eventbridge_rule")
    @patch("handler.disable_workflow")
    @patch("handler.update_poll_state")
    def test_auto_disable_after_four_failures(
        self, mock_update_state, mock_disable_wf, mock_disable_rule, mock_discord
    ):
        """Test auto-disable after 4 consecutive failures."""
        from handler import handle_failure

        poll_state = {"consecutive_failures": 3}  # Will become 4

        handle_failure("wf_test", poll_state, "Connection error")

        mock_disable_wf.assert_called_once_with("wf_test")
        mock_disable_rule.assert_called_once_with("wf_test")
        mock_discord.assert_called_once()

    @patch("handler.requests.post")
    def test_send_discord_notification(self, mock_post):
        """Test Discord notification sending."""
        from handler import send_discord_notification

        mock_post.return_value = MagicMock(status_code=204)

        send_discord_notification("wf_test", "Test error", 4)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "wf_test" in call_args[1]["json"]["content"]
        assert "4" in call_args[1]["json"]["content"]


class TestPollFeed:
    """Tests for poll_feed function."""

    @patch("handler.fetch_url")
    def test_poll_feed_with_new_items(self, mock_fetch, sample_rss_feed):
        """Test polling feed with new items."""
        from handler import poll_feed

        mock_fetch.return_value = sample_rss_feed
        poll_state = {"seen_item_ids": ["guid-001"]}

        new_items, state_updates = poll_feed(
            "https://example.com/feed.xml", "rss", poll_state
        )

        assert len(new_items) == 1
        assert new_items[0]["guid"] == "guid-002"
        assert "guid-001" in state_updates["seen_item_ids"]
        assert "guid-002" in state_updates["seen_item_ids"]
        assert state_updates["consecutive_failures"] == 0

    @patch("handler.fetch_url")
    def test_poll_feed_no_new_items(self, mock_fetch, sample_rss_feed):
        """Test polling feed with no new items."""
        from handler import poll_feed

        mock_fetch.return_value = sample_rss_feed
        poll_state = {"seen_item_ids": ["guid-001", "guid-002"]}

        new_items, state_updates = poll_feed(
            "https://example.com/feed.xml", "rss", poll_state
        )

        assert len(new_items) == 0


class TestPollHttp:
    """Tests for poll_http function."""

    @patch("handler.fetch_url")
    def test_poll_http_first_check(self, mock_fetch):
        """Test first HTTP poll (no previous hash)."""
        from handler import poll_http

        mock_fetch.return_value = "page content"
        poll_state = {}

        trigger_data, state_updates = poll_http("https://example.com", poll_state)

        # First poll should not trigger (need baseline)
        assert trigger_data is None
        assert state_updates["last_content_hash"] is not None
        assert state_updates["consecutive_failures"] == 0

    @patch("handler.fetch_url")
    def test_poll_http_content_changed(self, mock_fetch):
        """Test HTTP poll when content changed."""
        from handler import hash_content, poll_http

        old_content = "old content"
        new_content = "new content"
        mock_fetch.return_value = new_content
        poll_state = {"last_content_hash": hash_content(old_content)}

        trigger_data, state_updates = poll_http("https://example.com", poll_state)

        assert trigger_data is not None
        assert trigger_data["type"] == "poll"
        assert trigger_data["content_type"] == "http"
        assert "new content" in trigger_data["content"]

    @patch("handler.fetch_url")
    def test_poll_http_no_change(self, mock_fetch):
        """Test HTTP poll when content unchanged."""
        from handler import hash_content, poll_http

        content = "same content"
        mock_fetch.return_value = content
        poll_state = {"last_content_hash": hash_content(content)}

        trigger_data, state_updates = poll_http("https://example.com", poll_state)

        assert trigger_data is None
