"""Pytest configuration and fixtures for Cost Lambda tests."""

from __future__ import annotations

import os
import sys

# Add the lambda directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set required environment variables before importing modules
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("POWERTOOLS_SERVICE_NAME", "cost-api")
os.environ.setdefault("POWERTOOLS_LOG_LEVEL", "DEBUG")
