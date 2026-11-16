"""Qt desktop host for the offline Three.js fighter editor."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import traceback
from urllib.parse import urlencode

from PySide6.QtCore import QObject, Signal, Slot, QUrl, QStandardPaths, QTimer, Qt, qInstallMessageHandler
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from . import remembered, runtimes
from .dialogs import Dialogs
from .editor import Editor
from .container import SaveError
from .diagnostics import log_detail
from .locations import initial_data_directory


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
    _completed = Signal(str, object)
    _progress = Signal(str)

    def __init__(self, window, workspace, initial):
        super().__init__(window)
        self.window = window
        self._completed.connect(self._deliver, Qt.ConnectionType.QueuedConnection)
        self._progress.connect(self._deliver_progress, Qt.ConnectionType.QueuedConnection)
        self.editor = Editor(workspace, self._progress.emit)
        self.initial = initial
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="caf-editor")
        self.busy = 0
        self.visible_busy = 0
        self._requests = {}
        self._pending_navigation = None
        self.dialogs = Dialogs(self)

    BACKGROUND = frozenset(
        {
            "snapshot",
            "home",
            "preview",
            "options",
            "ui_preview",
            "performance_audio",
            "performance_animation",
            "retail_snapshot",
            "retail_preview",
        }
    )

    @Slot(str)
    def _deliver_progress(self, message):
        self.progress.emit(message)

    def _error(self, ident, exc):
        detail = getattr(exc, "detail", None) or "".join(traceback.format_exception(exc))
        message = (
            exc.message
            if isinstance(exc, SaveError)
            else (
                "The file could not be read or written. Check its folder and try again."
                if isinstance(exc, OSError)
                else "This operation could not be completed. Open Details for more information."
            )
        )
        log_detail(self.editor.workspace, detail)
        self.response.emit(json.dumps(dict(id=ident, error=message, detail=detail)))

    def runtime_folder(self, feature):
        """The game version chosen once in Game setup. Refused up front, in plain words, when it cannot do the job,
        so nobody picks an output file for an export that was never going to work."""
        return str(runtimes.require(self.editor.runtime, feature, self.editor.recipe_format())["path"])

    PAGES = {
        "home": "home.html",
        "story": "index.html",
        "caf": "index.html",
        "retail-new": "retail.html",
        "retail-edit": "retail.html",
    }
    STARTS = {"open", "new", "import"}

    def navigate(self, ident, mode, args):
        """Move this window to Home or one of the workflows. The page reads what to do from the address fragment."""
        if mode not in self.PAGES:
            raise SaveError("Unknown workflow")
        if self.visible_busy:
            raise SaveError("Please wait for the current operation to finish.")
        if self.busy:
            if self._pending_navigation is not None:
                self.response.emit(json.dumps(dict(id=ident, result=False)))
            else:
                self._pending_navigation = (ident, mode, args)
            return
        editor = self.editor
        unsaved = ((editor.profile or editor.project) and editor.changes()) or editor.retail.snapshot()["dirty"]
        if (
            unsaved
            and QMessageBox.question(self.window, "Unsaved changes", "Leave without saving your fighter changes?")
            != QMessageBox.StandardButton.Yes
        ):
            return self.response.emit(json.dumps(dict(id=ident, result=False)))
        if mode.startswith("retail") and self.initial and editor.retail.data is None:
            editor.retail.data = Path(self.initial).resolve()
        fragment = {"mode": mode}
        if args.get("start") in self.STARTS:
            fragment["start"] = args["start"]
        if isinstance(args.get("path"), str) and args["path"]:
            fragment["path"] = args["path"]
        url = QUrl.fromLocalFile(str(Path(__file__).parent / "resources" / self.PAGES[mode]))
        url.setFragment(urlencode(fragment))
        self.response.emit(json.dumps(dict(id=ident, result=True)))
        previous = QUrl(self.window.web.url())
        previous.setFragment("")
        target = QUrl(url)
        target.setFragment("")
        fragment_change = previous == target and self.window.web.url().fragment() != url.fragment()
        self.window.web.setUrl(url)
        if fragment_change:
            self.window.web.reload()

    @Slot(str)
    def dispatch(self, raw):
        try:
            request = json.loads(raw)
            ident, action, args = request["id"], request["action"], request.get("args", {})
            if not isinstance(ident, str) or not isinstance(action, str) or not isinstance(args, dict):
                raise SaveError("Invalid editor request")
            if self._pending_navigation is not None and action not in self.BACKGROUND:
                raise SaveError("Please wait while the workflow opens.")
            if action in ("open_home", "open_workflow", "open_retail_editor", "open_caf_editor"):
                if action == "open_retail_editor":
                    action, args = "open_workflow", {"mode": "retail-edit", "start": "new"}
                if action == "open_caf_editor":
                    action, args = "open_workflow", {"mode": "story", "start": "open"}
                return self.navigate(ident, "home" if action == "open_home" else args.get("mode"), args)
            if action == "open_folder":
                # Only folders the Workshop itself reported: the last export's folder or its own backups folder.
                if args.get("target") == "backups":
                    folder = self.editor.workspace / "backups"
                    folder.mkdir(parents=True, exist_ok=True)
                elif args.get("target") == "export" and self.editor.last_export is not None:
                    folder = self.editor.last_export.parent
                else:
                    raise SaveError("There is no folder to open yet")
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
                return self.response.emit(json.dumps(dict(id=ident, result=None)))
            if action == "boot":
                if self.initial:
                    action, args = "open_data", {"path": str(self.initial)}
                    self.initial = None
                else:
                    action = "snapshot"
            prepared = self.dialogs.prepare(action, args)
            if prepared.action is None:
                return self.response.emit(json.dumps(dict(id=ident, result=prepared.result)))
            action, args = prepared.action, prepared.args
            if self._pending_navigation is not None:
                return self.response.emit(json.dumps(dict(id=ident, result=None)))
            future = self.pool.submit(self._request, action, args)
            self._requests[ident] = action not in self.BACKGROUND
            self.busy += 1
            self.visible_busy += self._requests[ident]
            future.add_done_callback(lambda task: self.finish(ident, task))
        except Exception as exc:
            self._error(request.get("id", "") if isinstance(locals().get("request"), dict) else "", exc)

    def finish(self, ident, task):
        self._completed.emit(ident, task)

    def _request(self, action, args):
        result = self.editor.request(action, args)
        if action in {"preview", "retail_preview"}:
            from .preview_transport import pack_preview

            return pack_preview(result)
        return result

    @Slot(str, object)
    def _deliver(self, ident, task):
        try:
            self.response.emit(json.dumps(dict(id=ident, result=task.result()), allow_nan=False))
        except Exception as exc:
            self._error(ident, exc)
        finally:
            self.busy -= 1
            self.visible_busy -= self._requests.pop(ident, False)
        if not self.busy and self._pending_navigation is not None:
            navigation, self._pending_navigation = self._pending_navigation, None
            try:
                self.navigate(*navigation)
            except Exception as exc:
                self._error(navigation[0], exc)


class Window(QMainWindow):
    def __init__(self, workspace, initial=None, start_page="home.html"):
        super().__init__()
        icon_name = "defjam.icns" if sys.platform == "darwin" else "defjam.png"
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "resources" / "branding" / icon_name)))
        self.setWindowTitle("Def Jam FFNY · Fighter Workshop · Local Beta")
        self.resize(1440, 940)
        self.setMinimumSize(1080, 740)
        self.web = QWebEngineView(self)
        self.page = Page(self.web)
        self.page.loadFinished.connect(lambda ok: print(f"[LOAD] ok={ok} url={self.page.url().toString()}", flush=True))
        self.page.renderProcessTerminated.connect(
            lambda status, code: print(f"[RENDERER] {status} exit={code}", flush=True)
        )
        self.web.setPage(self.page)
        self.guard = OfflineOnly(self)
        self.page.profile().setUrlRequestInterceptor(self.guard)
        self.channel = QWebChannel(self.page)
        self.bridge = Bridge(self, workspace, initial)
        self.channel.registerObject("editor", self.bridge)
        self.page.setWebChannel(self.channel)
        self.setCentralWidget(self.web)
        self.web.setUrl(QUrl.fromLocalFile(str(Path(__file__).parent / "resources" / start_page)))

    def closeEvent(self, event):
        if self.bridge.busy:
            QMessageBox.information(self, "Operation in progress", "Please wait for the current operation to finish.")
            event.ignore()
            return
        if (
            (self.bridge.editor.profile or self.bridge.editor.project) and self.bridge.editor.changes()
        ) or self.bridge.editor.retail.snapshot()["dirty"]:
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
        receipt.write_text(
            json.dumps(
                dict(
                    passed=not error,
                    error=error,
                    details=details,
                    icon_loaded=not window.windowIcon().isNull(),
                    platform=sys.platform,
                    machine=platform.machine(),
                    frozen=bool(getattr(sys, "frozen", False)),
                    seconds=round(time.monotonic() - started, 2),
                ),
                indent=2,
            ),
            encoding="utf-8",
        )
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

        window.page.runJavaScript(
            """(()=>{
            const canvas=document.querySelector('#viewport canvas');
            const gl=canvas?.getContext('webgl2');
            if(!window.__cafState || !gl || gl.isContextLost())return null;
            if(window.__cafState.fields?.has_fighter && window.__cafState.preview_available
                && !window.__cafPreview?.ready)return null;
            const debug=gl.getExtension('WEBGL_debug_renderer_info');
            return JSON.stringify({webchannel:true,webgl:gl.getParameter(gl.VERSION),
                renderer:gl.getParameter(debug?debug.UNMASKED_RENDERER_WEBGL:gl.RENDERER),
                profiles:window.__cafState.profiles.length,selected:window.__cafState.selected,
                preview_ready:Boolean(window.__cafPreview?.ready)});
        })()""",
            checked,
        )

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
    parser.add_argument("--retail", action="store_true", help="Open the retail fighter studio")
    parser.add_argument("--project", type=Path, help="Open a retail fighter project (with --retail)")
    parser.add_argument("--runtime", type=Path, help="Compatible development runtime for retail authoring")
    args = parser.parse_args(argv)
    QApplication.setApplicationName("defjam-ffny-fighter-workshop")
    QApplication.setOrganizationName("FFNY Community Tools")
    workspace = (
        (args.workspace or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)))
        .expanduser()
        .resolve()
    )
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
    initial = (
        args.data if args.smoke_test else initial_data_directory(args.data) or remembered.recall(workspace, "data")
    )
    # Home is the front door. Automated checks and screenshots still open the editor page directly.
    window = Window(workspace, initial, "index.html" if args.smoke_test or args.capture or args.retail else "home.html")
    if args.retail:
        # The retail studio needs the game directory, not a CAF cache/profile.
        window.bridge.initial = None
        window.bridge.editor.data = initial.resolve() if initial else None
        if args.project:
            window.bridge.editor.retail.request("open", {"path": str(args.project)})
        if args.runtime:
            window.bridge.editor.retail.request("configure", {"runtime": str(args.runtime)})
        window.web.setUrl(QUrl.fromLocalFile(str(Path(__file__).parent / "resources/retail.html")))
    elif args.project or args.runtime:
        parser.error("--project and --runtime require --retail")
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
