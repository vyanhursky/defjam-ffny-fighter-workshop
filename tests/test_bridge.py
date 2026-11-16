"""GUI-thread delivery and navigation without game data or a browser process."""

import json
import os
import threading
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import QObject, QThread, QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402
from defjam_caf.desktop import Bridge  # noqa: E402
from defjam_caf.container import SaveError  # noqa: E402


class Web:
    def __init__(self):
        self.current = QUrl("about:blank")
        self.reloads = 0

    def url(self):
        return self.current

    def setUrl(self, url):
        self.current = url

    def reload(self):
        self.reloads += 1


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def bridge(app, tmp_path):
    window = QObject()
    window.web = Web()
    instance = Bridge(window, tmp_path, None)
    yield instance
    instance.pool.shutdown(wait=True)
    app.processEvents()


def drain(app, predicate):
    deadline = time.monotonic() + 3
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert predicate()


def test_result_progress_and_counters_are_delivered_on_gui_thread(app, bridge):
    received, progress, workers = [], [], []
    bridge.response.connect(lambda raw: received.append((json.loads(raw), QThread.currentThread())))
    bridge.progress.connect(lambda text: progress.append((text, QThread.currentThread())))

    def request(action, args):
        workers.append(QThread.currentThread())
        bridge.editor.progress("Preparing")
        return {"done": True}

    bridge.editor.request = request
    bridge.dispatch(json.dumps(dict(id="1", action="snapshot")))
    assert bridge.busy == 1 and bridge.visible_busy == 0
    drain(app, lambda: len(received) == 1)
    assert workers[0] != app.thread()
    assert received[0] == ({"id": "1", "result": {"done": True}}, app.thread())
    assert progress == [("Preparing", app.thread())]
    assert bridge.busy == bridge.visible_busy == 0


@pytest.mark.parametrize(
    "result", [SaveError("Choose another project.", "Precise diagnostic"), {"value": float("nan")}]
)
def test_failures_and_json_encoding_release_busy_counters(app, bridge, result):
    received = []
    bridge.response.connect(lambda raw: received.append(json.loads(raw)))

    def request(action, args):
        if isinstance(result, Exception):
            raise result
        return result

    bridge.editor.request = request
    bridge.dispatch(json.dumps(dict(id="1", action="save")))
    drain(app, lambda: bool(received))
    assert received[0]["error"] and received[0]["detail"]
    if isinstance(result, SaveError):
        assert received[0]["error"] == result.message and received[0]["detail"] == result.detail
    assert bridge.busy == bridge.visible_busy == 0
    assert (bridge.editor.workspace / "logs/desktop.log").is_file()


def test_navigation_waits_for_background_refresh_and_reloads_mode_fragment(app, bridge):
    received, release = [], threading.Event()
    bridge.response.connect(lambda raw: received.append(json.loads(raw)))
    bridge.navigate("first", "story", {})
    bridge.editor.request = lambda action, args: release.wait(2)
    bridge.dispatch(json.dumps(dict(id="preview", action="preview")))
    bridge.navigate("next", "caf", {})
    assert bridge._pending_navigation is not None and len(received) == 1
    release.set()
    drain(app, lambda: len(received) == 3)
    assert [row["id"] for row in received] == ["first", "preview", "next"]
    assert bridge.window.web.url().fragment() == "mode=caf"
    assert bridge.window.web.reloads == 1


def test_visible_work_blocks_navigation_and_unsaved_prompt_can_cancel(app, bridge, monkeypatch):
    release = threading.Event()
    bridge.editor.request = lambda action, args: release.wait(2)
    bridge.dispatch(json.dumps(dict(id="save", action="save")))
    with pytest.raises(SaveError, match="Please wait"):
        bridge.navigate("next", "home", {})
    release.set()
    drain(app, lambda: bridge.busy == 0)
    bridge.editor.project = {"dirty": True}
    bridge.editor.changes = lambda: ["changed"]
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    bridge.navigate("cancel", "home", {})
    assert bridge.window.web.url().toString() == "about:blank"
