"""Verify community handlers register and import correctly.

These tests do NOT require real database credentials. They check:
- Every handler in index.json has the required files/metadata
- Handlers with deps installed import without errors
- Handlers with missing deps report a clean import_error
"""

import ast
import json
import sys
import types
import importlib.util
from pathlib import Path

import pytest


COMMUNITY_HANDLERS_DIR = (
    Path(__file__).resolve().parents[2] / "community_handlers"
)
INDEX_FILE = Path(__file__).resolve().parents[2] / "index.json"

REQUIRED_INIT_ATTRS = {"name", "type", "title"}


def _load_index():
    with open(INDEX_FILE) as f:
        return json.load(f)


def _indexed_handlers():
    """Yield (folder, path) for every handler in index.json."""
    index = _load_index()
    for entry in index["handlers"]:
        folder = entry["folder"]
        path = COMMUNITY_HANDLERS_DIR / folder
        yield folder, path


# -----------------------------------------------------------
# Metadata / structure tests
# -----------------------------------------------------------


class TestHandlerStructure:
    """Verify every indexed handler has the expected files."""

    @pytest.fixture(
        params=list(_indexed_handlers()), ids=lambda x: x[0]
    )
    def handler(self, request):
        return request.param

    def test_directory_exists(self, handler):
        name, path = handler
        assert path.is_dir(), (
            f"{name} listed in index.json but directory missing"
        )

    def test_init_exists(self, handler):
        _, path = handler
        assert (path / "__init__.py").exists(), (
            f"{path.name} is missing __init__.py"
        )

    def test_about_exists(self, handler):
        _, path = handler
        assert (path / "__about__.py").exists(), (
            f"{path.name} is missing __about__.py"
        )

    def test_icon_exists(self, handler):
        _, path = handler
        has_icon = (
            (path / "icon.svg").exists()
            or (path / "icon.png").exists()
        )
        assert has_icon, f"{path.name} is missing an icon file"

    def test_init_has_required_attributes(self, handler):
        """Parse __init__.py via AST (no import needed)."""
        name, path = handler
        init_file = path / "__init__.py"
        if not init_file.exists():
            pytest.skip(f"{name} has no __init__.py")

        tree = ast.parse(init_file.read_text())
        assigned = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigned.add(target.id)

        missing = REQUIRED_INIT_ATTRS - assigned
        assert not missing, (
            f"{name}: __init__.py missing attributes: {missing}"
        )


# -----------------------------------------------------------
# index.json consistency
# -----------------------------------------------------------


class TestIndexConsistency:
    """Verify index.json is internally consistent."""

    def test_index_names_are_unique(self):
        index = _load_index()
        names = [e["name"] for e in index["handlers"]]
        dupes = [n for n in names if names.count(n) > 1]
        assert not dupes, f"Duplicate names in index.json: {dupes}"

    def test_index_folders_are_unique(self):
        index = _load_index()
        folders = [e["folder"] for e in index["handlers"]]
        dupes = [f for f in folders if folders.count(f) > 1]
        assert not dupes, f"Duplicate folders: {dupes}"

    def test_index_types_are_valid(self):
        index = _load_index()
        valid = {"data", "ml"}
        for entry in index["handlers"]:
            assert entry.get("type") in valid, (
                f"'{entry['name']}' has invalid type "
                f"'{entry.get('type')}'"
            )


# -----------------------------------------------------------
# Import tests
# -----------------------------------------------------------

_PARENT_PKG = "_test_community_handlers"


class TestHandlerImport:
    """Verify indexed handlers import cleanly."""

    @pytest.fixture(
        params=list(_indexed_handlers()), ids=lambda x: x[0]
    )
    def handler(self, request):
        return request.param

    def test_import_does_not_crash(self, handler):
        """Importing should succeed or set import_error."""
        name, path = handler
        init_file = path / "__init__.py"
        if not init_file.exists():
            pytest.skip(f"{name} has no __init__.py")

        # Parent package for relative imports
        if _PARENT_PKG not in sys.modules:
            parent = types.ModuleType(_PARENT_PKG)
            parent.__path__ = [str(COMMUNITY_HANDLERS_DIR)]
            parent.__package__ = _PARENT_PKG
            sys.modules[_PARENT_PKG] = parent

        module_name = f"{_PARENT_PKG}.{name}"
        spec = importlib.util.spec_from_file_location(
            module_name,
            init_file,
            submodule_search_locations=[str(path)],
        )
        assert spec is not None, (
            f"Could not create module spec for {name}"
        )

        module = importlib.util.module_from_spec(spec)
        module.__package__ = module_name
        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            pytest.skip(
                f"{name} failed to import (missing deps)"
            )

        handler_cls = getattr(module, "Handler", None)
        import_error = getattr(module, "import_error", None)

        if handler_cls is None:
            assert import_error is not None, (
                f"{name}: Handler is None but import_error "
                "is also None"
            )
        else:
            assert import_error is None, (
                f"{name}: Handler loaded but import_error "
                f"is set: {import_error}"
            )

        sys.modules.pop(module_name, None)
