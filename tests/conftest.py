"""All synthetic writers use disposable locks, never the player's app workspace."""

import pytest
from defjam_caf import storage


@pytest.fixture(autouse=True)
def disposable_lock_namespace(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "default_lock_root", lambda: tmp_path / "workshop-locks")
