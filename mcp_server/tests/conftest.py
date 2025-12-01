"""
Pytest configuration for MCP Server tests.

Ensures the parent directory is in the Python path so imports work correctly.
"""
import sys
from pathlib import Path

# Add parent directory to Python path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
