"""Tests for plugin_loader.py and built-in plugins."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.plugin_loader import load_plugins, merge_with_core
from riscv_xray.extensions import EXTENSIONS


def test_load_builtin_plugins():
    """Built-in plugins directory loads at least xtheadv."""
    plugins = load_plugins()
    assert "XTheadV" in plugins


def test_load_invalid_plugin_dir():
    """Non-existent plugin dir prints warning, returns empty (or only builtins)."""
    plugins = load_plugins(plugin_dir="/nonexistent/path/xyz")
    # Should not raise; builtins still loaded
    assert isinstance(plugins, dict)


def test_merge_preserves_core():
    """merge_with_core keeps all core extensions."""
    plugins = {}  # no plugins
    merged = merge_with_core(EXTENSIONS, plugins)
    for key in EXTENSIONS:
        assert key in merged
        assert merged[key]["source"] == "core"


def test_plugin_classification():
    """XTheadV plugin classifies th.vadd.* as belonging to its extension."""
    plugins = load_plugins()
    plugin = plugins["XTheadV"]
    assert plugin.classify("th.vadd.vv") is True
    assert plugin.classify("vadd.vv") is False
    assert plugin.classify("add") is False


def test_merge_adds_plugin_extension():
    """merge_with_core adds plugin extension with source=plugin."""
    plugins = load_plugins()
    merged = merge_with_core(EXTENSIONS, plugins)
    assert "XTheadV" in merged
    assert merged["XTheadV"]["source"] == "plugin"


def test_plugin_required_attrs():
    """All loaded plugins have EXTENSION_NAME, PREFIXES, METADATA."""
    plugins = load_plugins()
    for name, module in plugins.items():
        assert hasattr(module, "EXTENSION_NAME")
        assert hasattr(module, "PREFIXES")
        assert hasattr(module, "METADATA")
