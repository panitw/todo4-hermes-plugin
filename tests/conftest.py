"""Load the plugin as a package so tests can import its submodules."""
import importlib.util
import sys
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_PACKAGE_NAME = "todo4_plugin"

_spec = importlib.util.spec_from_file_location(
    _PACKAGE_NAME,
    _PLUGIN_ROOT / "__init__.py",
    submodule_search_locations=[str(_PLUGIN_ROOT)],
)
_pkg = importlib.util.module_from_spec(_spec)
sys.modules[_PACKAGE_NAME] = _pkg
_spec.loader.exec_module(_pkg)

collect_ignore_glob = ["../__init__.py", "../*.py"]
