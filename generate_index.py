

import ast
import json
from datetime import datetime, timezone
from pathlib import Path


HANDLERS_DIR = Path(__file__).parent / "community_handlers"
OUTPUT_PATH = Path(__file__).parent / "index.json"


def _parse_init(init_path: Path) -> dict:
    """Extract metadata from a handler's __init__.py using AST (no imports)."""
    info = {}
    try:
        code = ast.parse(init_path.read_text(encoding="utf-8"))
    except Exception:
        return info

    for item in code.body:
        if not isinstance(item, ast.Assign):
            continue
        target = item.targets[0]
        if not isinstance(target, ast.Name):
            continue
        name = target.id
        value = item.value

        if isinstance(value, ast.Constant):
            info[name] = value.value
        elif name == "type" and isinstance(value, ast.Attribute):
            # HANDLER_TYPE.DATA → "data", HANDLER_TYPE.ML → "ml"
            info["type"] = value.attr.lower()
        elif name == "support_level" and isinstance(value, ast.Attribute):
            # HANDLER_SUPPORT_LEVEL.COMMUNITY → "community", .MINDSDB → "mindsdb"
            info["support_level"] = value.attr.lower()

    return info


def _parse_about(about_path: Path) -> dict:
    """Extract __description__ and __version__ from __about__.py."""
    info = {}
    if not about_path.exists():
        return info
    try:
        code = ast.parse(about_path.read_text(encoding="utf-8"))
    except Exception:
        return info

    for item in code.body:
        if not isinstance(item, ast.Assign):
            continue
        target = item.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if isinstance(item.value, ast.Constant):
            info[target.id] = item.value.value

    return info


def build_index() -> dict:
    handlers = []

    for handler_dir in sorted(HANDLERS_DIR.iterdir()):
        if not handler_dir.is_dir() or not handler_dir.name.endswith("_handler"):
            continue

        init_path = handler_dir / "__init__.py"
        if not init_path.exists():
            continue

        init_info = _parse_init(init_path)
        about_info = _parse_about(handler_dir / "__about__.py")

        name = init_info.get("name")
        title = init_info.get("title")
        if not name or not title:
            # Handler is malformed — skip it
            continue

        entry = {
            "name": name,
            "title": title,
            "folder": handler_dir.name,
            "type": init_info.get("type", "data"),
            "support_level": init_info.get("support_level", "community"),
            "icon_path": init_info.get("icon_path", "icon.svg"),
            "description": about_info.get("__description__", ""),
        }
        handlers.append(entry)

    return {
        "version": "1.0",
        "handlers": handlers,
    }


def main():
    if not HANDLERS_DIR.is_dir():
        print(f"ERROR: handlers directory not found: {HANDLERS_DIR}")
        raise SystemExit(1)

    index = build_index()
    OUTPUT_PATH.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {OUTPUT_PATH} with {len(index['handlers'])} handlers.")


if __name__ == "__main__":
    main()
