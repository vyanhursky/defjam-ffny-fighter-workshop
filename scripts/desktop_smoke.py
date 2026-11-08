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
    ap.add_argument("--startup-timeout", type=float, default=600,
                    help="Seconds allowed for first-use original asset conversion (default: 600)")
    args = ap.parse_args()
    if not (args.data / ".caf-disposable-test-data").is_file():
        raise SystemExit("Refusing UI writes without the disposable-data marker")
    args.output.mkdir(parents=True, exist_ok=False)
    export = args.output / "ui-export.djprofile"
    preview_export = args.output / "preview-only.djprofile"
    original = next(p.container for p in discover(args.data).profiles if p.name == "CAFTEST")
    export_paths = iter([preview_export, export])
    QFileDialog.getSaveFileName = lambda *a, **k: (str(next(export_paths)), "FFNY profiles (*.djprofile)")
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
        ("tattoo category group", "[...document.querySelectorAll('#category optgroup[label=Tattoos] option')].length===9 && [...document.querySelectorAll('#category optgroup[label=Tattoos] option')].every(e=>e.text.startsWith('Tattoo - '))", None),
        ("live garment preview without staging", "window.__cafPreview?.ready && window.__cafPreview.part && !window.__cafState.dirty && window.__cafState.fields.caf_values[12]===window.__originalTop",
         "window.__originalTop=window.__cafState.fields.caf_values[12];window.__originalTopColor=window.__cafState.fields.caf_colors[12];let e=document.getElementById('garment');e.value=[...e.options].find(o=>o.text==='Fila Logo Tee').value;e.dispatchEvent(new Event('change'))"),
        ("live color preview without staging", "window.__cafPreview?.ready && window.__cafPreview.part!==window.__oldTryOn && !window.__cafState.dirty",
         "window.__oldTryOn=window.__cafPreview.part;let e=document.getElementById('color');e.selectedIndex=1;e.dispatchEvent(new Event('change'))"),
        ("live fitting preview without staging", "window.__cafPreview?.ready && window.__cafPreview.part!==window.__oldTryOn && !window.__cafState.dirty",
         "window.__oldTryOn=window.__cafPreview.part;let e=document.getElementById('fitting');e.selectedIndex=1;e.dispatchEvent(new Event('change'))"),
        ("rapid selectors keep latest preview", "window.__cafPreview?.ready && window.__cafPreview.part===window.__latestTryOn && !window.__cafState.dirty",
         "window.__latestTryOn=window.__cafPreview.part;for(let index of [2,0,1]){let c=document.getElementById('color');c.selectedIndex=index;c.dispatchEvent(new Event('change'));let f=document.getElementById('fitting');f.selectedIndex=1;f.dispatchEvent(new Event('change'))}"),
        ("export excludes try-on", "document.getElementById('toast').textContent.includes('preview-only.djprofile')",
         "document.getElementById('export').click()"),
        ("no clothes temporary preview", "window.__cafPreview?.ready && window.__cafPreview.hideClothes && !window.__cafState.dirty && window.__cafState.fields.caf_values[12]===window.__originalTop",
         "document.getElementById('no-clothes').click()"),
        ("warm lighting", "window.__cafView?.lighting==='warm' && !window.__cafState.dirty",
         "let e=document.getElementById('lighting');e.value='warm';e.dispatchEvent(new Event('change'))"),
        ("cool lighting", "window.__cafView?.lighting==='cool' && window.__cafView.materials.every(t=>t==='MeshStandardMaterial') && !window.__cafState.dirty",
         "let e=document.getElementById('lighting');e.value='cool';e.dispatchEvent(new Event('change'))"),
        ("texture reference lighting", "window.__cafView?.lighting==='flat' && window.__cafView.materials.every(t=>t==='MeshBasicMaterial') && !window.__cafState.dirty",
         "let e=document.getElementById('lighting');e.value='flat';e.dispatchEvent(new Event('change'))"),
        ("source T-pose", "window.__cafView?.pose==='tpose' && window.__cafView.bounds[1][0]-window.__cafView.bounds[0][0]>window.__wardrobeWidth*1.25 && !window.__cafState.dirty",
         "window.__wardrobeWidth=window.__cafView.bounds[1][0]-window.__cafView.bounds[0][0];let e=document.getElementById('pose');e.value='tpose';e.dispatchEvent(new Event('change'))"),
        ("relaxed pose", "window.__cafView?.pose==='relaxed' && !window.__cafState.dirty",
         "let e=document.getElementById('pose');e.value='relaxed';e.dispatchEvent(new Event('change'))"),
        ("restore clothes", "window.__cafPreview?.ready && !window.__cafPreview.hideClothes && window.__cafPreview.part && !window.__cafState.dirty",
         "document.getElementById('no-clothes').click();let e=document.getElementById('pose');e.value='wardrobe';e.dispatchEvent(new Event('change'));document.getElementById('lighting').value='studio';document.getElementById('lighting').dispatchEvent(new Event('change'))"),
        ("equip commits preview", "window.__cafState.dirty && (window.__cafState.fields.caf_values[12]!==window.__originalTop || window.__cafState.fields.caf_colors[12]!==window.__originalTopColor) && window.__cafPreview?.ready && !window.__cafPreview.part",
         "document.getElementById('equip').click()"),
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
            _, preview_only, _ = read_archive(preview_export)
            assert preview_only == original, "Uncommitted preview leaked into export"
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
        QTimer.singleShot(800, lambda: (window.grab().save(str(args.output / "desktop-compact.png")), app.exit(1 if error else 0)))

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
        timeout = args.startup_timeout if index == 0 else 60
        if time.monotonic() - state["waiting_since"] > timeout:
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
                if title in {"no clothes temporary preview", "warm lighting", "cool lighting", "texture reference lighting", "source T-pose", "relaxed pose", "equip commits preview"}:
                    capture = args.output / (title.replace(" ", "-") + ".png")
                    QTimer.singleShot(250, lambda path=capture: window.grab().save(str(path)))
                state.update(step=index + 1, sent=False)
        window.page.runJavaScript("Boolean(" + condition + ")", checked)

    timer.timeout.connect(tick)
    timer.start(700)
    app.exec()
    return 1 if state["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
