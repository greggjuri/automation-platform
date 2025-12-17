"""Pytest configuration for cron handler tests."""

import sys
from pathlib import Path

# Add the handler directory to the path for imports
handler_dir = Path(__file__).parent.parent
sys.path.insert(0, str(handler_dir))
