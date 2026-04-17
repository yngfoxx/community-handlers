"""Integration tests that verify community handlers register and import correctly in MindsDB.

These tests do NOT require real database credentials. They verify that:
- Every handler's __init__.py has the required metadata attributes
- Handlers whose dependencies are installed can be imported without errors
- Handlers whose dependencies are missing report a clean import_error (not a crash)
- The integration controller correctly registers community handlers
"""

import json
import os
from pathlib import Path

import pytest

from mindsdb.integrations.libs.const import HANDLER_TYPE


COMMUNITY_HANDLERS_DIR = Path(__file__).resolve().parents[2] / "community_handlers"
INDEX_FILE = Path(__file__).resolve().parents[2] / "index.json"

REQUIRED_INIT_ATTRS = {"name", "type", "title"}


def _get_handler_dirs():
    """Yield (handler_name, handler_path) for every handler directory."""
    for entry in sorted(COMMUNITY_HANDLERS_DIR.iterdir()):
        if entry.is_dir() and not entry.name.startswith(("__", ".")):
            yield entry.name, entry


def _load_index():
    with open(INDEX_FILE) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Metadata / structure tests
# ---------------------------------------------------------------------------


class TestHandlerStructure:
    """Verify every handler directory has the expected files and metadata."""

    @pytest.fixture(params=list(_get_handler_dirs()), ids=lambda x: x[0])
    def handler(self, request):
        return request.param  # (name, path)

    def test_init_exists(self, handler):
        _, path = handler
        assert (path / "__init__.py").exists(), f"{path.name} is missing __init__.py"

    def test_about_exists(self, handler):
        _, path = handler
        assert (path / "__about__.py").exists(), f"{path.name} is missing __about__.py"

    def test_icon_exists(self, handler):
        _, path = handler
        assert (path / "icon.svg").exists() or (path / "icon.png").exists(), (
            f"{path.name} is missing an icon file"
        )

    def test_init_has_required_attributes(self, handler):
        """Parse __init__.py with AST to check required attributes without importing."""
        import ast

        name, path = handler
        init_file = path / "__init__.py"
        tree = ast.parse(init_file.read_text())

        assigned_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigned_names.add(target.id)

        missing = REQUIRED_INIT_ATTRS - assigned_names
        assert not missing, f"{name}: __init__.py missing required attributes: {missing}"


# ---------------------------------------------------------------------------
# index.json consistency
# ---------------------------------------------------------------------------


class TestIndexConsistency:
    """Verify index.json matches the actual handler directories."""

    def test_index_entries_have_matching_directories(self):
        """Every handler in index.json should have a corresponding directory."""
        index = _load_index()
        for entry in index["handlers"]:
            folder = entry["folder"]
            assert (COMMUNITY_HANDLERS_DIR / folder).is_dir(), (
                f"index.json lists '{folder}' but directory does not exist"
            )

    def test_all_directories_are_in_index(self):
        """Every handler directory should have an entry in index.json."""
        index = _load_index()
        indexed_folders = {e["folder"] for e in index["handlers"]}
        for name, _ in _get_handler_dirs():
            assert name in indexed_folders, (
                f"Handler directory '{name}' is not listed in index.json"
            )

    def test_index_names_are_unique(self):
        index = _load_index()
        names = [e["name"] for e in index["handlers"]]
        assert len(names) == len(set(names)), "Duplicate handler names in index.json"

    def test_index_folders_are_unique(self):
        index = _load_index()
        folders = [e["folder"] for e in index["handlers"]]
        assert len(folders) == len(set(folders)), "Duplicate handler folders in index.json"


# ---------------------------------------------------------------------------
# Import tests (via MindsDB integration controller)
# ---------------------------------------------------------------------------


class TestHandlerImport:
    """Verify handlers can be registered and imported through the integration controller."""

    @pytest.fixture(scope="class")
    def integration_controller(self):
        """Create an IntegrationController with community handlers registered."""
        # Minimal DB init required by IntegrationController
        import mindsdb.interfaces.storage.db as db

        db.init()

        from mindsdb.interfaces.database.integrations import IntegrationController

        controller = IntegrationController()
        return controller

    def test_community_handlers_are_registered(self, integration_controller):
        """At least some community handlers should appear in handlers_import_status."""
        statuses = integration_controller.handlers_import_status
        community_handlers = {
            name: meta for name, meta in statuses.items() if meta.get("community", False)
        }
        assert len(community_handlers) > 0, "No community handlers were registered"

    def test_handler_types_are_valid(self, integration_controller):
        """Every registered handler should have a valid HANDLER_TYPE."""
        valid_types = {HANDLER_TYPE.DATA, HANDLER_TYPE.ML}
        for name, meta in integration_controller.handlers_import_status.items():
            if meta.get("community"):
                assert meta.get("type") in valid_types, (
                    f"Handler '{name}' has invalid type: {meta.get('type')}"
                )

    def test_import_errors_are_clean(self, integration_controller):
        """Handlers that fail to import should have a string error, not a crash."""
        for name, meta in integration_controller.handlers_import_status.items():
            if not meta.get("community"):
                continue
            import_info = meta.get("import", {})
            if import_info.get("success") is False:
                assert isinstance(import_info.get("error_message"), str), (
                    f"Handler '{name}' failed import but error_message is not a string"
                )
