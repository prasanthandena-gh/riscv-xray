"""plugin_loader.py - Load community extension detector plugins."""

from __future__ import annotations
import importlib.util
import sys
from pathlib import Path


_REQUIRED_ATTRS = ("EXTENSION_NAME", "PREFIXES", "METADATA")


def load_plugins(plugin_dir: str = None) -> dict:
    """
    Load plugins from the built-in plugins/ directory and an optional extra dir.

    Returns {extension_name: module} for all valid plugins found.
    """
    plugins = {}

    # Built-in plugins dir
    builtin_dir = Path(__file__).parent / "plugins"
    dirs_to_scan = [builtin_dir]

    if plugin_dir:
        extra = Path(plugin_dir)
        if extra.exists():
            dirs_to_scan.append(extra)
        else:
            print(f"  Warning: plugin dir not found: {plugin_dir}", flush=True)

    for directory in dirs_to_scan:
        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module = _load_module(py_file)
            if module is None:
                continue
            # Validate required attributes
            missing = [a for a in _REQUIRED_ATTRS if not hasattr(module, a)]
            if missing:
                print(
                    f"  Warning: plugin {py_file.name} missing "
                    f"attributes: {missing} — skipped",
                    flush=True,
                )
                continue
            name = module.EXTENSION_NAME
            plugins[name] = module

    return plugins


def _load_module(path: Path):
    """Load a Python file as a module. Returns None on error."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"  Warning: failed to load plugin {path.name}: {e}", flush=True)
        return None
    return module


def merge_with_core(core_extensions: dict, plugins: dict) -> dict:
    """
    Merge plugin extensions into the core EXTENSIONS dict.

    Plugin extensions get "source": "plugin".
    Core extensions get "source": "core".
    Returns a new merged dict (does not mutate inputs).
    """
    merged = {}
    for name, meta in core_extensions.items():
        merged[name] = {**meta, "source": "core"}

    for name, plugin in plugins.items():
        if name in merged:
            # Plugin overrides core — warn
            print(
                f"  Warning: plugin '{name}' conflicts with core extension "
                "— plugin takes precedence.",
                flush=True,
            )
        merged[name] = {**plugin.METADATA, "source": "plugin",
                        "prefixes": plugin.PREFIXES}

    return merged
