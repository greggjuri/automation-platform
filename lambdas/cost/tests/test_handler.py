"""Unit tests for Cost Lambda handler."""

from datetime import date
from unittest.mock import MagicMock, patch


from handler import (
    calculate_period,
    format_cost,
    get_month_to_date_costs,
    handler,
)


class TestCalculatePeriod:
    """Tests for calculate_period function."""

    @patch("handler.date")
    def test_mid_month(self, mock_date):
        """Test period calculation mid-month."""
        mock_date.today.return_value = date(2024, 12, 15)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        start, end, display_end = calculate_period()

        assert start == "2024-12-01"
        assert end == "2024-12-16"  # Exclusive: today + 1
        assert display_end == "2024-12-15"

    @patch("handler.date")
    def test_first_day_of_month(self, mock_date):
        """Test period calculation on first day of month."""
        mock_date.today.return_value = date(2024, 12, 1)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        start, end, display_end = calculate_period()

        assert start == "2024-12-01"
        assert end == "2024-12-02"  # Exclusive: today + 1
        assert display_end == "2024-12-01"

    @patch("handler.date")
    def test_last_day_of_month(self, mock_date):
        """Test period calculation on last day of month."""
        mock_date.today.return_value = date(2024, 12, 31)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        start, end, display_end = calculate_period()

        assert start == "2024-12-01"
        assert end == "2025-01-01"  # Exclusive: crosses year boundary
        assert display_end == "2024-12-31"

    @patch("handler.date")
    def test_end_date_is_exclusive(self, mock_date):
        """Test that End date is today+1 for exclusive CE API."""
        mock_date.today.return_value = date(2024, 12, 25)
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        _, end, display_end = calculate_period()

        # End should be one day after display_end (exclusive)
        assert end == "2024-12-26"
        assert display_end == "2024-12-25"


class TestFormatCost:
    """Tests for format_cost function."""

    def test_format_string_input(self):
        """Test formatting string cost."""
        assert format_cost("3.456789") == "3.46"

    def test_format_float_input(self):
        """Test formatting float cost."""
        assert format_cost(3.456789) == "3.46"

    def test_format_zero(self):
        """Test formatting zero cost."""
        assert format_cost(0) == "0.00"

    def test_format_small_decimal(self):
        """Test formatting small decimal."""
        assert format_cost(0.001) == "0.00"

    def test_format_large_number(self):
        """Test formatting large number."""
        assert format_cost(1234.567) == "1234.57"


class TestGetMonthToDateCosts:
    """Tests for get_month_to_date_costs function."""

    @patch("handler.ce_client")
    @patch("handler.calculate_period")
    def test_successful_retrieval(self, mock_period, mock_ce):
        """Test successful cost retrieval with multiple services."""
        mock_period.return_value = ("2024-12-01", "2024-12-26", "2024-12-25")

        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "Groups": [
                        {
                            "Keys": ["Amazon DynamoDB"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "3.45", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["AWS Lambda"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "2.10", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["Amazon API Gateway"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "1.50", "Unit": "USD"}
                            },
                        },
                    ]
                }
            ]
        }

        result = get_month_to_date_costs()

        assert result["period"]["start"] == "2024-12-01"
        assert result["period"]["end"] == "2024-12-25"
        assert result["total_cost"] == "7.05"
        assert result["currency"] == "USD"
        assert len(result["services"]) == 3
        # Verify sorted by cost descending
        assert result["services"][0]["name"] == "Amazon DynamoDB"
        assert result["services"][0]["cost"] == "3.45"
        assert result["services"][1]["name"] == "AWS Lambda"
        assert result["services"][2]["name"] == "Amazon API Gateway"

    @patch("handler.ce_client")
    @patch("handler.calculate_period")
    def test_no_services(self, mock_period, mock_ce):
        """Test handling when no services have costs."""
        mock_period.return_value = ("2024-12-01", "2024-12-26", "2024-12-25")

        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [{"Groups": []}]
        }

        result = get_month_to_date_costs()

        assert result["total_cost"] == "0.00"
        assert result["services"] == []

    @patch("handler.ce_client")
    @patch("handler.calculate_period")
    def test_filters_zero_cost_services(self, mock_period, mock_ce):
        """Test that services with zero cost are filtered out."""
        mock_period.return_value = ("2024-12-01", "2024-12-26", "2024-12-25")

        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "Groups": [
                        {
                            "Keys": ["Amazon DynamoDB"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "3.45", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["AWS Lambda"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "0.00", "Unit": "USD"}
                            },
                        },
                    ]
                }
            ]
        }

        result = get_month_to_date_costs()

        assert len(result["services"]) == 1
        assert result["services"][0]["name"] == "Amazon DynamoDB"

    @patch("handler.ce_client")
    @patch("handler.calculate_period")
    def test_services_sorted_by_cost_descending(self, mock_period, mock_ce):
        """Test that services are sorted by cost in descending order."""
        mock_period.return_value = ("2024-12-01", "2024-12-26", "2024-12-25")

        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "Groups": [
                        {
                            "Keys": ["Service A"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "1.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["Service B"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "5.00", "Unit": "USD"}
                            },
                        },
                        {
                            "Keys": ["Service C"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "3.00", "Unit": "USD"}
                            },
                        },
                    ]
                }
            ]
        }

        result = get_month_to_date_costs()

        costs = [float(s["cost"]) for s in result["services"]]
        assert costs == sorted(costs, reverse=True)
        assert result["services"][0]["name"] == "Service B"
        assert result["services"][1]["name"] == "Service C"
        assert result["services"][2]["name"] == "Service A"


class TestHandler:
    """Tests for Lambda handler function."""

    @patch("handler.get_month_to_date_costs")
    def test_successful_response(self, mock_get_costs):
        """Test successful handler response."""
        mock_get_costs.return_value = {
            "period": {"start": "2024-12-01", "end": "2024-12-25"},
            "total_cost": "14.23",
            "currency": "USD",
            "services": [{"name": "DynamoDB", "cost": "3.45"}],
        }

        result = handler({}, MagicMock())

        assert result["statusCode"] == 200
        assert "application/json" in result["headers"]["Content-Type"]
        assert "14.23" in result["body"]

    @patch("handler.get_month_to_date_costs")
    def test_client_error_access_denied(self, mock_get_costs):
        """Test handling of AccessDeniedException."""
        from botocore.exceptions import ClientError

        mock_get_costs.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Not allowed"}},
            "GetCostAndUsage",
        )

        result = handler({}, MagicMock())

        assert result["statusCode"] == 500
        assert "AccessDeniedException" in result["body"]

    @patch("handler.get_month_to_date_costs")
    def test_client_error_throttling(self, mock_get_costs):
        """Test handling of throttling error."""
        from botocore.exceptions import ClientError

        mock_get_costs.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "GetCostAndUsage",
        )

        result = handler({}, MagicMock())

        assert result["statusCode"] == 429
        assert "ThrottlingException" in result["body"]

    @patch("handler.get_month_to_date_costs")
    def test_unexpected_error(self, mock_get_costs):
        """Test handling of unexpected error."""
        mock_get_costs.side_effect = ValueError("Unexpected error")

        result = handler({}, MagicMock())

        assert result["statusCode"] == 500
        assert "InternalError" in result["body"]
