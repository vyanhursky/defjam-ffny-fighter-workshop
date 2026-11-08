"""Qt desktop host for the offline Three.js fighter editor."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import traceback

from PySide6.QtCore import QObject, Signal, Slot, QUrl, QStandardPaths, QTimer, qInstallMessageHandler
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QInputDialog, QMessageBox
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from .editor import Editor
from .locations import default_data_directory, initial_data_directory


class OfflineOnly(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        if info.requestUrl().scheme() not in {"file", "qrc", "data", "blob"}:
            info.block(True)


class Page(QWebEnginePage):
    def acceptNavigationRequest(self, url, kind, main):
        return url.scheme() in {"file", "qrc", "data", "about"}

    def javaScriptConsoleMessage(self, level, message, line, source):
        print(f"[UI] {message} ({Path(source).name}:{line})", flush=True)


class Bridge(QObject):
    response = Signal(str)
    progress = Signal(str)

    def __init__(self, window, workspace, initial):
        super().__init__(window)
        self.window = window
        self.editor = Editor(workspace, lambda message: self.progress.emit(message))
        self.initial = initial
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="caf-editor")
        self.busy = 0

    @Slot(str)
    def dispatch(self, raw):
        try:
            request = json.loads(raw)
            ident, action, args = request["id"], request["action"], request.get("args", {})
            if not isinstance(ident, str) or not isinstance(args, dict):
                raise ValueError("Invalid editor request")
            if action == "boot":
                if self.initial:
                    action, args = "open_data", {"path": str(self.initial)}
                    self.initial = None
                else:
                    action = "snapshot"
            if action == "choose_data":
                path = QFileDialog.getExistingDirectory(self.window, "Select Recomp data directory", str(self.editor.data or default_data_directory() or Path.home()))
                if not path:
                    return self.response.emit(json.dumps(dict(id=ident, result=None)))
                action, args = "open_data", {"path": path}
            elif action == "choose_export":
                if self.editor.profile is None:
                    raise ValueError("Choose a profile first")
                path, _ = QFileDialog.getSaveFileName(self.window, "Export complete profile", self.editor.profile.name + ".djprofile", "FFNY profiles (*.djprofile)")
                if not path:
                    return self.response.emit(json.dumps(dict(id=ident, result=None)))
                action, args = "export", {"path": path}
            elif action == "choose_import":
                if self.editor.discovery is None:
                    raise ValueError("Choose the destination data directory first")
                path, _ = QFileDialog.getOpenFileName(self.window, "Import complete profile", "", "FFNY profiles (*.djprofile)")
                if not path:
                    return self.response.emit(json.dumps(dict(id=ident, result=None)))
                action, args = "import", {"path": path}
            elif action == "choose_duplicate":
                name, ok = QInputDialog.getText(self.window, "Duplicate fighter profile", "New profile ID (1–7 uppercase letters or digits):")
                if not ok:
                    return self.response.emit(json.dumps(dict(id=ident, result=None)))
                action, args = "duplicate", {"name": name.strip().upper()}
            self.busy += 1
            future = self.pool.submit(self.editor.request, action, args)
            future.add_done_callback(lambda task: self.finish(ident, task))
        except Exception as exc:
            self.response.emit(json.dumps(dict(id=request.get("id", "") if isinstance(locals().get("request"), dict) else "", error=str(exc))))

    def finish(self, ident, task):
        try:
            self.response.emit(json.dumps(dict(id=ident, result=task.result()), allow_nan=False))
        except Exception as exc:
            traceback.print_exc()
            self.response.emit(json.dumps(dict(id=ident, error=str(exc))))
        finally:
            self.busy -= 1


class Window(QMainWindow):
    def __init__(self, workspace, initial=None):
        super().__init__()
        icon_name = "defjam.icns" if sys.platform == "darwin" else "defjam.png"
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "resources" / "branding" / icon_name)))
        self.setWindowTitle("Def Jam FFNY · Fighter Workshop · Local Beta")
        self.resize(1440, 940)
        self.setMinimumSize(1080, 740)
        self.web = QWebEngineView(self)
        self.page = Page(self.web)
        self.page.loadFinished.connect(lambda ok: print(f"[LOAD] ok={ok} url={self.page.url().toString()}", flush=True))
        self.page.renderProcessTerminated.connect(lambda status, code: print(f"[RENDERER] {status} exit={code}", flush=True))
        self.web.setPage(self.page)
        self.guard = OfflineOnly(self)
        self.page.profile().setUrlRequestInterceptor(self.guard)
        self.channel = QWebChannel(self.page)
        self.bridge = Bridge(self, workspace, initial)
        self.channel.registerObject("editor", self.bridge)
        self.page.setWebChannel(self.channel)
        self.setCentralWidget(self.web)
        self.web.setUrl(QUrl.fromLocalFile(str(Path(__file__).parent / "resources" / "index.html")))

    def closeEvent(self, event):
        if self.bridge.busy:
            QMessageBox.information(self, "Operation in progress", "Please wait for the current operation to finish.")
            event.ignore()
            return
        if self.bridge.editor.profile and self.bridge.editor.changes():
            answer = QMessageBox.question(self, "Unsaved changes", "Discard your unsaved fighter changes and close?")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self.bridge.pool.shutdown(wait=False)
        event.accept()


def startup_smoke(app, window, receipt):
    import platform
    import time
    started = time.monotonic()
    timer = QTimer(window)
    state = {"done": False, "checking": False}

    def finish(error=None, details=None):
        if state["done"]:
            return
        state["done"] = True
        timer.stop()
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(dict(passed=not error, error=error, details=details,
            icon_loaded=not window.windowIcon().isNull(),
            platform=sys.platform, machine=platform.machine(), frozen=bool(getattr(sys, "frozen", False)),
            seconds=round(time.monotonic() - started, 2)), indent=2), encoding="utf-8")
        app.exit(1 if error else 0)

    def tick():
        if time.monotonic() - started > 120:
            finish("Timed out waiting for WebGL and the editor WebChannel")
            return
        if state["checking"] or state["done"]:
            return
        state["checking"] = True
        def checked(raw):
            state["checking"] = False
            if raw and not state["done"]:
                finish(details=json.loads(raw))
        window.page.runJavaScript("""(()=>{
            const canvas=document.querySelector('#viewport canvas');
            const gl=canvas?.getContext('webgl2');
            if(!window.__cafState || !gl || gl.isContextLost())return null;
            if(window.__cafState.fields?.has_fighter && window.__cafState.preview_available
                && !window.__cafPreview?.ready)return null;
            return JSON.stringify({webchannel:true,webgl:gl.getParameter(gl.VERSION),
                profiles:window.__cafState.profiles.length,selected:window.__cafState.selected,
                preview_ready:Boolean(window.__cafPreview?.ready)});
        })()""", checked)

    window.page.renderProcessTerminated.connect(lambda status, code: finish("Renderer exited: " + str(code)))
    timer.timeout.connect(tick)
    timer.start(250)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--smoke-test", type=Path, help="Write a read-only desktop startup receipt and exit")
    parser.add_argument("--capture", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--quit-after", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    QApplication.setApplicationName("defjam-ffny-fighter-workshop")
    QApplication.setOrganizationName("FFNY Community Tools")
    workspace = (args.workspace or Path(QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation))).expanduser().resolve()
    if getattr(sys, "frozen", False):
        # Windowed executables have no console. Retain local diagnostics so a
        # failed renderer is observable instead of presenting a silent blank.
        log_root = workspace / "logs"
        log_root.mkdir(parents=True, exist_ok=True)
        log = (log_root / "desktop.log").open("a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log
        print(f"[START] {sys.executable} resources={Path(__file__).parent / 'resources'}", flush=True)
        qInstallMessageHandler(lambda kind, context, message: print(f"[QT] {message}", flush=True))
    app = QApplication(sys.argv[:1])
    # Automated package checks without --data stay independent of installed saves.
    initial = args.data if args.smoke_test else initial_data_directory(args.data)
    window = Window(workspace, initial)
    app.setWindowIcon(window.windowIcon())
    window.show()
    if args.smoke_test:
        startup_smoke(app, window, args.smoke_test)
    if args.capture:
        def capture():
            args.capture.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.capture))
            print("[CAPTURE] " + str(args.capture), flush=True)
        QTimer.singleShot(18000, capture)
    if args.quit_after:
        QTimer.singleShot(args.quit_after * 1000, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
