"""Make plugin root importable for tests (Hermes loads the plugin as a flat package)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
