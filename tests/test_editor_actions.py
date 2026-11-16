from pathlib import Path
import runpy

import pytest

from defjam_caf.container import SaveError
from defjam_caf.editor import Editor


def test_action_documentation_matches_live_tables():
    root = Path(__file__).resolve().parents[1]
    render = runpy.run_path(str(root / "scripts/editor_actions.py"))["render"]
    assert (root / "docs/editor-actions.md").read_text(encoding="utf-8") == render()


def test_unknown_actions_and_retail_guard_remain_explicit(tmp_path):
    editor = Editor(tmp_path)
    with pytest.raises(SaveError, match="Unsupported editor action"):
        editor.request("unknown", {})
    with pytest.raises(SaveError, match="Create or open a retail fighter project"):
        editor.request("retail_stats", {"stats": {}})
