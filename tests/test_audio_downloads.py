import base64
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import QUrl  # noqa: E402
from defjam_caf import audio_downloads  # noqa: E402
from test_audition_cache import wav  # noqa: E402


class Request:
    def __init__(self, value, mime="audio/wav"):
        self.value, self.mime, self.cancelled = value, mime, False

    def url(self):
        return QUrl(self.value)

    def mimeType(self):
        return self.mime

    def suggestedFileName(self):
        return "../fighter-line.wav"

    def cancel(self):
        self.cancelled = True


def test_audio_download_writes_valid_wav_with_explicit_destination(tmp_path, monkeypatch):
    messages = []

    class Message:
        ButtonRole = audio_downloads.QMessageBox.ButtonRole
        StandardButton = audio_downloads.QMessageBox.StandardButton

        def __init__(self, parent):
            pass

        def setWindowTitle(self, title):
            pass

        def setText(self, value):
            messages.append(value)

        def addButton(self, *args):
            return object()

        def exec(self):
            return None

        def clickedButton(self):
            return None

    destination = tmp_path / "chosen.wav"
    monkeypatch.setattr(audio_downloads, "QMessageBox", Message)
    monkeypatch.setattr(audio_downloads.QFileDialog, "getSaveFileName", lambda *args: (str(destination), ""))
    request = Request("data:audio/wav;base64," + base64.b64encode(wav()).decode())
    audio_downloads.accept_audio_download(None, request)
    assert request.cancelled and destination.read_bytes() == wav()
    assert str(destination) in messages[0]


@pytest.mark.parametrize(
    "value,mime", [("https://example.invalid/a.wav", "audio/wav"), ("data:text/plain;base64,YQ==", "text/plain")]
)
def test_nonlocal_or_nonaudio_downloads_are_refused(value, mime, monkeypatch):
    monkeypatch.setattr(audio_downloads.QFileDialog, "getSaveFileName", lambda *a: pytest.fail("must not open picker"))
    request = Request(value, mime)
    audio_downloads.accept_audio_download(None, request)
    assert request.cancelled


def test_cancelled_save_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_downloads.QFileDialog, "getSaveFileName", lambda *args: ("", ""))
    request = Request("data:audio/wav;base64," + base64.b64encode(wav()).decode())
    audio_downloads.accept_audio_download(None, request)
    assert request.cancelled and not list(tmp_path.iterdir())


def test_bad_audio_is_refused_before_a_picker(monkeypatch):
    messages = []
    monkeypatch.setattr(audio_downloads, "QMessageBox", SimpleNamespace(warning=lambda *args: messages.append(args)))
    monkeypatch.setattr(audio_downloads.QFileDialog, "getSaveFileName", lambda *a: pytest.fail("must not open picker"))
    audio_downloads.accept_audio_download(None, Request("data:audio/wav;base64,bm90IGEgd2F2"))
    assert len(messages) == 1
