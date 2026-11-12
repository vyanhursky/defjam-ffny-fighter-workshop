"""Folders chosen once are remembered, and only while they still qualify."""
import json

from defjam_caf import remembered


def runtime(path):
    (path / "setup").mkdir(parents=True); (path / "scripts").mkdir()
    (path / "setup/fighter_caf.py").write_text("x"); (path / "scripts/fighter-contract.py").write_text("x")
    return path


def test_nothing_is_remembered_by_default(tmp_path):
    assert remembered.recall(tmp_path, "data") is None and remembered.recall(tmp_path, "runtime") is None


def test_a_runtime_that_has_its_tools_is_remembered_across_launches(tmp_path):
    checkout = runtime(tmp_path / "runtime")
    assert remembered.remember(tmp_path / "work", "runtime", checkout)
    assert remembered.recall(tmp_path / "work", "runtime") == checkout.resolve()


def test_a_folder_that_fails_its_check_is_not_remembered_or_offered(tmp_path):
    (tmp_path / "empty").mkdir()
    assert not remembered.remember(tmp_path / "work", "runtime", tmp_path / "empty")
    assert not remembered.remember(tmp_path / "work", "data", tmp_path / "empty")
    assert remembered.recall(tmp_path / "work", "runtime") is None and not (tmp_path / "work/remembered.json").exists()


def test_a_remembered_folder_that_was_moved_falls_back_to_asking(tmp_path):
    data = tmp_path / "data"; (data / "extracted").mkdir(parents=True)
    remembered.remember(tmp_path / "work", "data", data)
    assert remembered.recall(tmp_path / "work", "data") == data.resolve()
    (data / "extracted").rmdir()
    assert remembered.recall(tmp_path / "work", "data") is None


def test_the_two_folders_are_independent_and_a_corrupt_file_is_ignored(tmp_path):
    data = tmp_path / "data"; (data / "extracted").mkdir(parents=True)
    checkout = runtime(tmp_path / "runtime")
    remembered.remember(tmp_path / "work", "data", data); remembered.remember(tmp_path / "work", "runtime", checkout)
    stored = json.loads((tmp_path / "work/remembered.json").read_text())
    assert set(stored) == {"data", "runtime"}
    (tmp_path / "work/remembered.json").write_text("{not json")
    assert remembered.recall(tmp_path / "work", "data") is None
    assert remembered.remember(tmp_path / "work", "data", data) and remembered.recall(tmp_path / "work", "data") == data.resolve()
