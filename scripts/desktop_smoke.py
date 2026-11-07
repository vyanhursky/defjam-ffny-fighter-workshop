"""Exercise the real Qt/WebChannel UI on explicitly marked disposable data.

Only native file/name pickers and confirmation responses are deterministic test
adapters; all editor buttons, DOM events, transport, previews and persistence are
the production implementation. Never use an owner's unmarked data directory.
"""
import argparse
import json
from pathlib import Path
import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog

from defjam_caf import desktop
from defjam_caf.profiles import discover
from defjam_caf.fields import read_fields
from defjam_caf.storage import read_archive


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--import-data", type=Path)
    args = ap.parse_args()
    if not (args.data / ".caf-disposable-test-data").is_file():
        raise SystemExit("Refusing UI writes without the disposable-data marker")
    args.output.mkdir(parents=True, exist_ok=False)
    export = args.output / "ui-export.djprofile"
    QFileDialog.getSaveFileName = lambda *a, **k: (str(export), "FFNY profiles (*.djprofile)")
    QInputDialog.getText = lambda *a, **k: ("UITEST", True)
    if args.import_data:
        if not (args.import_data / ".caf-disposable-test-data").is_file() or discover(args.import_data).profiles:
            raise SystemExit("Import destination must be an empty marked disposable data root")
        QFileDialog.getExistingDirectory = lambda *a, **k: str(args.import_data)
        QFileDialog.getOpenFileName = lambda *a, **k: (str(export), "FFNY profiles (*.djprofile)")

    class TestPage(desktop.Page):
        def javaScriptConfirm(self, origin, message):
            return True

    desktop.Page = TestPage
    app = QApplication(sys.argv[:1])
    window = desktop.Window(args.workspace, args.data)
    window.show()
    evidence = []
    steps = [
        ("initial preview", "Boolean(window.__cafState?.selected && window.__cafPreview?.ready)", None),
        ("cash edit", "window.__cafState?.fields?.cash===12345 && window.__cafState.dirty",
         "document.querySelector('[data-tab=stats]').click();let e=document.getElementById('cash');e.value='12345';e.dispatchEvent(new Event('change'))"),
        ("health edit", "window.__cafState?.fields?.stats.health===50",
         "let e=document.getElementById('stat-health');e.value='50';e.dispatchEvent(new Event('change'))"),
        ("undo", "window.__cafState?.fields?.stats.health===45 && window.__cafState.fields.cash===12345",
         "document.getElementById('undo').click()"),
        ("style combination", "JSON.stringify(window.__cafState?.fields?.styles)==='[0,2,4]'",
         "document.querySelector('[data-tab=styles]').click();document.getElementById('style-0').value='0';document.getElementById('style-1').value='2';document.getElementById('style-2').value='4';document.getElementById('apply-styles').click()"),
        ("body build", "window.__cafState?.fields?.caf_values[0]===2 && window.__cafPreview?.ready",
         "document.querySelector('[data-tab=appearance]').click();let e=document.getElementById('build');e.value='C';e.dispatchEvent(new Event('change'))"),
        ("tattoo choices", "document.getElementById('garment').options.length>0 && document.getElementById('garment').options[0].text.includes('Tattoo')",
         "window.__cafOldTattoo=window.__cafState.fields.caf_values[30];let e=document.getElementById('category');e.value='30';e.dispatchEvent(new Event('change'))"),
        ("equip tattoo", "window.__cafState?.fields?.caf_values[30]!==window.__cafOldTattoo && window.__cafPreview?.ready",
         "let e=document.getElementById('garment');e.selectedIndex=0;e.dispatchEvent(new Event('change'));document.getElementById('equip').click()"),
        ("export", "document.getElementById('toast').textContent.includes('Exported complete profile')",
         "document.getElementById('export').click()"),
        ("duplicate", "window.__cafState?.selected==='UITEST' && !window.__cafState.dirty && window.__cafPreview?.ready",
         "document.getElementById('duplicate').click()"),
        ("edit duplicate", "window.__cafState?.fields?.cash===12346 && window.__cafState.dirty",
         "document.querySelector('[data-tab=stats]').click();let e=document.getElementById('cash');e.value='12346';e.dispatchEvent(new Event('change'))"),
        ("save with backup", "window.__cafState?.fields?.cash===12346 && !window.__cafState.dirty",
         "document.getElementById('save').click()"),
        ("final preview", "Boolean(window.__cafPreview?.ready)",
         "document.querySelector('[data-tab=appearance]').click();document.getElementById('front').click()"),
    ]
    if args.import_data:
        steps += [
            ("choose transfer destination", "window.__cafState?.profiles?.length===0",
             "document.getElementById('open-data').click()"),
            ("import complete profile", "window.__cafState?.selected==='CAFTEST' && window.__cafState.fields.cash===12345 && window.__cafPreview?.ready",
             "document.getElementById('import').click()"),
        ]
    state = {"step": 0, "started": time.monotonic(), "sent": False, "checking": False,
             "failed": None, "waiting_since": time.monotonic()}
    timer = QTimer()

    def finish(error=None):
        timer.stop()
        state["failed"] = error
        if error:
            print("FAILED: " + error, flush=True)
        else:
            _, exported, files = read_archive(export)
            exported_fields = read_fields(exported.payload)
            assert exported_fields["cash"] == 12345 and exported_fields["styles"] == [0, 2, 4]
            profile = next(p for p in discover(args.data).profiles if p.name == "UITEST")
            fields = read_fields(profile.container.payload)
            assert fields["cash"] == 12346 and fields["stats"]["health"] == 45
            assert list((args.workspace / "backups").glob("*-UITEST-*.djprofile"))
            if args.import_data:
                imported = next(p for p in discover(args.import_data).profiles if p.name == "CAFTEST")
                assert imported.container == exported
            window.grab().save(str(args.output / "desktop-final.png"))
            window.resize(1100, 760)
        (args.output / "receipt.json").write_text(json.dumps(dict(passed=not error, error=error, steps=evidence), indent=2))
        QTimer.singleShot(800, lambda: (window.grab().save(str(args.output / "desktop-compact.png")), app.quit()))

    def tick():
        if state["checking"]:
            return
        index = state["step"]
        if index == len(steps):
            try:
                finish()
            except Exception as exc:
                finish(str(exc))
            return
        title, condition, action = steps[index]
        if not state["sent"]:
            state["sent"] = True
            state["waiting_since"] = time.monotonic()
            if action:
                window.page.runJavaScript("(()=>{" + action + "})()")
        if time.monotonic() - state["waiting_since"] > 60:
            finish("Timed out during " + title)
            return
        state["checking"] = True
        def checked(value):
            state["checking"] = False
            if value:
                evidence.append(dict(step=title, seconds=round(time.monotonic() - state["started"], 2)))
                print("PASS: " + title, flush=True)
                if index == 0:
                    window.grab().save(str(args.output / "desktop-initial.png"))
                state.update(step=index + 1, sent=False)
        window.page.runJavaScript("Boolean(" + condition + ")", checked)

    timer.timeout.connect(tick)
    timer.start(700)
    app.exec()
    return 1 if state["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
