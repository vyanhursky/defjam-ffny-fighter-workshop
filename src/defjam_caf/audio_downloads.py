"""Explicit, local-only handling for the audio player's WAV downloads."""

from pathlib import Path
from urllib.parse import unquote

from PySide6.QtCore import QStandardPaths, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox
from .container import SaveError
from .performance import audio_bytes
from .storage import atomic_bytes


def accept_audio_download(parent, request):
    url = request.url()
    if url.scheme() != "data" or request.mimeType() not in {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/vnd.wave",
    }:
        request.cancel()
        return
    # Save through the app's bounded writer, rather than Chromium's temporary
    # download directory. The audio element always uses a local base64 WAV URL.
    request.cancel()
    header, separator, encoded = url.toString().partition(",")
    if not separator or not header.lower().endswith(";base64"):
        return
    try:
        raw = audio_bytes(unquote(encoded))
    except (SaveError, ValueError) as error:
        QMessageBox.warning(parent, "Voice clip could not be saved", str(error))
        return
    name = Path(request.suggestedFileName().replace("\\", "/")).name
    if not name.lower().endswith(".wav"):
        name = "voice-clip.wav"
    folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
    destination, _ = QFileDialog.getSaveFileName(
        parent, "Save voice clip", str(Path(folder) / name), "WAV audio (*.wav)"
    )
    if not destination:
        return
    path = Path(destination)
    if path.suffix.lower() != ".wav":
        path = path.with_name(path.name + ".wav")
    try:
        atomic_bytes(path, raw)
    except OSError as error:
        QMessageBox.warning(parent, "Voice clip could not be saved", str(error))
        return
    message = QMessageBox(parent)
    message.setWindowTitle("Voice clip saved")
    message.setText("Saved WAV audio to:\n" + str(path))
    open_folder = message.addButton("Open folder", QMessageBox.ButtonRole.ActionRole)
    message.addButton(QMessageBox.StandardButton.Close)
    message.exec()
    if message.clickedButton() == open_folder:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
