"""Test configuration for action_notify tests."""

import sys
from pathlib import Path

# Add shared module to path for tests
shared_path = Path(__file__).parent.parent.parent / "shared"
if str(shared_path.parent) not in sys.path:
    sys.path.insert(0, str(shared_path.parent))
