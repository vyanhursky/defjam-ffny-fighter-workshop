"""Drive the real Qt/WebChannel UI with invented saves, geometry and catalog adapters.

No game dump is read. Only original-resource/compiler boundaries and native
picker/confirmation answers are deterministic adapters; state editing, projects,
backups, transport, controls and WebGL are production paths. Captures stay local.
"""

import argparse
import base64
from collections import Counter
import io
import json
from pathlib import Path
import sys
import time
import wave
from types import SimpleNamespace

from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from defjam_caf import desktop, projects, remembered, runtimes, storage
from defjam_caf.container import Container
from defjam_caf.container import SaveError
from defjam_caf.fields import apply_fields, renamed
from defjam_caf.performance import AI_FIELDS
from defjam_caf.profiles import directory_name


def fixtures(output):
    data = output / "data"
    folder = data / "save/UserData/45410049" / directory_name("UITEST")
    folder.mkdir(parents=True)
    fighter = dict(
        stats=dict.fromkeys(("health", "upper", "lower", "speed", "toughness"), 20),
        styles=[0],
        caf_values=[0, 0, 0, 0, 0, 1] + [0] * 6 + [0xFFFFFFFF] * 26,
        caf_colors=[0] * 38,
    )
    save = renamed(apply_fields(projects.empty_container(), fighter), "UITEST")
    payload = bytearray(save.payload)
    payload[0x3210:0x321B] = b"STORY BYTES"
    save = Container(save.metadata, bytes(payload))
    (folder / "UITEST").write_bytes(save.encode())
    (folder / "SaveMeta.xbx").write_bytes("Name=UITEST\r\n".encode("utf-16"))
    (data / ".caf-disposable-test-data").write_text("Invented fixture; safe to edit.")
    runtime = output / "runtime"
    (runtime / "scripts").mkdir(parents=True)
    (runtime / "setup").mkdir()
    commands = sorted({command for _, _, needs, *_ in runtimes.FEATURES for command in needs})
    (runtime / "scripts/fighter-contract.py").write_text(
        "parser.add_argument('command', choices=" + repr(tuple(commands)) + ")\n"
    )
    (runtime / "setup/fighter_caf.py").write_text("FORMAT = 'caf-fighter-1'\n")
    (runtime / "scripts/fighter-contract.json").write_text(
        json.dumps(
            dict(api=1, commands=commands, recipe_format="caf-fighter-1", extensions=["retail-animation-preview-1"])
        )
    )
    png = io.BytesIO()
    Image.new("RGBA", (32, 32), (50, 150, 80, 255)).save(png, format="PNG")
    preview = dict(
        meshes=[
            dict(
                positions=[[-1, 0, 0], [1, 0, 0], [0, 2, 0]],
                normals=[[0, 0, 1]] * 3,
                uv=[[0, 0], [1, 0], [0.5, 1]],
                indices=[0, 1, 2],
                atlas="a",
                slot="0",
                rm=0,
                source_model="retail-body",
                source_model_sha256="a" * 64,
                transparent=False,
            )
        ],
        textures={"a": "data:image/png;base64," + base64.b64encode(png.getvalue()).decode("ascii")},
        bounds=[[-1, 0, 0], [1, 2, 0]],
        notices=["Invented geometry; no game-asset acceptance."],
        arm_pivots={},
        shapes=[dict(name="A001", width=32, height=32)],
    )
    fighters = [
        dict(key="retail/" + name, label=name.title(), core=index + 1, voice=5)
        for index, name in enumerate(("blaze", "pockets", "teck"))
    ]
    catalog = dict(
        fighters=fighters,
        banks=[dict(category=name, voice=5, count=2) for name in ("Character", "Taunts", "Enviro")],
        cinematics=[
            dict(key=key, label=role.title(), role=role) for key, role in (("CI_113A", "intro"), ("CE_014A", "victory"))
        ],
        ai=[
            dict(
                key="char0005",
                label="Invented AI",
                tendencies={
                    level: [dict.fromkeys((key for key, _ in AI_FIELDS), 3) for _ in range(4)]
                    for level in ("easy", "normal", "hard")
                },
            )
        ],
    )
    return data, runtime, preview, catalog


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--capture", action="store_true", help="Keep local-only screenshots")
    parser.add_argument("--size", default="1440x940", choices=["1440x940", "1100x760"])
    args = parser.parse_args(argv)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    data, runtime, preview, catalog = fixtures(output)
    workspace = output / "workspace"
    storage.default_lock_root = lambda: workspace / "locks"
    runtimes.default_folder = lambda **kwargs: None
    remembered.remember(workspace, "app", runtime)
    remembered.remember(workspace, "runtime", runtime)
    pickers = []

    def save_picker(parent, title, *rest):
        pickers.append(title)
        return (
            ("", "")
            if "Mod" in title
            else (
                str(
                    output
                    / (
                        "audition.wav"
                        if title == "Save voice clip"
                        else "retail.ffnyfighter"
                        if "retail" in title
                        else "fighter.ffnyfighter"
                    )
                ),
                "",
            )
        )

    QFileDialog.getSaveFileName = save_picker
    QMessageBox.question = lambda *a, **k: QMessageBox.StandardButton.Yes
    QMessageBox.exec = lambda self: QMessageBox.StandardButton.Close

    class Page(desktop.Page):
        def javaScriptConfirm(self, origin, message):
            return True

    desktop.Page = Page
    app = QApplication(sys.argv[:1])
    window = desktop.Window(workspace, None, "home.html")
    window.resize(*map(int, args.size.split("x")))
    editor = window.bridge.editor
    editor.open_data(data)
    editor.runtime = runtime
    editor.retail.catalog = {
        "fighters": [
            dict(id=row["key"].split("/")[1], name=row["label"], components=dict(stats=dict(health=20)))
            for row in catalog["fighters"]
        ]
    }
    calls = Counter()
    original = editor.request
    audio = io.BytesIO()
    with wave.open(audio, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(24000)
        stream.writeframes(b"\x10\0" * 48000)
    audio_result = dict(mime="audio/wav", data=base64.b64encode(audio.getvalue()).decode("ascii"))

    def prepared(value):
        if isinstance(value, dict):
            if "profiles" in value:
                value["preview_available"] = True
            if "snapshot" in value:
                value["snapshot"] = prepared(value["snapshot"])
        return value

    def request(action, arguments):
        calls[action] += 1
        if action == "retail_snapshot" and calls[action] == 1:
            editor.performance_link = None
        if action == "retail_performance_connect":
            editor.performance_link = SimpleNamespace(
                catalog=catalog,
                call=lambda *args: dict(valid=True),
                voice=lambda request: audio_result,
                animation=lambda request: dict(clips=[], unsupported={}),
            )
            return editor.retail.snapshot()
        if action == "retail_performance_animation":
            if arguments.get("operation") == "list":
                return dict(clips=["fixture"], unsupported={})
            return dict(
                schema="fighter-workshop-animation-1",
                clip=arguments["clip"],
                ticks=30,
                ticks_per_second=30,
                models={
                    "retail-body": dict(
                        source_sha256="a" * 64,
                        bones=[dict(parent=-1, scale=[1, 1, 1], quaternion=[0, 0, 0, 1], position=[0, 0, 0])],
                        meshes={"0": dict(indices=[[0, 0, 0, 0]] * 3, weights=[[1, 0, 0, 0]] * 3)},
                    )
                },
                channels=[dict(role="body", bones=[0], samples=[[[0, i / 60, 0, 1]] for i in range(31)])],
                notice="Invented source tracks",
            )
        if action == "performance_audio":
            time.sleep(0.15)  # Exercise playback after the initiating click returns.
            return audio_result
        if action in ("preview", "retail_preview"):
            return preview
        if action == "retail_appearance":
            document = editor.retail.effective()
            document["resources"] = [
                dict(
                    id="retail-body",
                    kind="appearance",
                    compatibility=dict(skeleton="retail/binding-" + arguments["donor"].split("/")[1]),
                    source=dict(format="invented-fixture"),
                )
            ]
            document["definition"]["components"]["appearance"] = document["identity"]["pack"] + "/retail-body"
            document["textures"] = {}
            return editor.retail.commit(document)
        if action == "performance_connect":
            if calls[action] == 1:
                raise SaveError(
                    "The catalogs could not be loaded. Retry or check Game setup.",
                    "Invented catalog failure for retry coverage",
                )
            editor.performance_link = SimpleNamespace(catalog=catalog, call=lambda *args: dict(valid=True))
            return prepared(editor.snapshot())
        if action == "donors":
            return dict(donors=catalog["fighters"])
        return prepared(original(action, arguments))

    editor.request = request
    window.show()
    steps = [
        ("Home workflows", "document.querySelectorAll('.home-card').length===4", None),
        (
            "Story through Home",
            "window.__cafState?.selected==='UITEST' && window.__cafPreview?.ready",
            "document.querySelector('.home-card button').click()",
        ),
        (
            "Stat editing through WebChannel",
            "window.__cafState?.fields.cash===350 && window.__cafState.dirty",
            "document.querySelector('[data-tab=stats]').click();let e=document.getElementById('cash');e.value=350;e.dispatchEvent(new Event('change'))",
        ),
        (
            "Profile save and backup",
            "window.__cafState && !window.__cafState.dirty",
            "document.getElementById('save').click()",
        ),
        (
            "Return Home",
            "document.querySelectorAll('.home-card').length===4",
            "document.getElementById('home-button').click()",
        ),
        (
            "CAF start",
            "window.__cafState?.selected==='UITEST' && !document.getElementById('start-banner').hidden",
            "document.querySelectorAll('.home-card')[1].querySelector('button').click()",
        ),
        (
            "Create portable project",
            "Boolean(window.__cafState?.project)",
            "document.getElementById('start-action').click()",
        ),
        (
            "Project sidebar",
            "document.body.dataset.hasProject==='true' && getComputedStyle(document.getElementById('profile-sidebar')).display==='none' && document.querySelectorAll('#project-outfits button').length===1",
            None,
        ),
        (
            "Compact layout and vertical tabs",
            "document.querySelector('header').getBoundingClientRect().height<=64 && document.documentElement.scrollWidth<=innerWidth && new Set([...document.querySelectorAll('#editor-tabs [role=tab]')].map(e=>Math.round(e.getBoundingClientRect().x))).size===1",
            None,
        ),
        ("Copy outfit", "window.__cafState?.outfits.length===2", "document.getElementById('add-outfit').click()"),
        (
            "Rename outfit",
            "window.__cafState?.outfits.some(o=>o.name==='Alt look') && document.getElementById('outfit-select').value===window.__cafState.active_outfit",
            "let e=document.getElementById('outfit-name');e.value='Alt look';e.dispatchEvent(new Event('change'))",
        ),
        (
            "Keyboard tabs",
            "document.querySelector('[data-tab=styles]').getAttribute('aria-selected')==='true'",
            "let e=document.querySelector('[data-tab=stats]');e.click();e.focus();e.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}))",
        ),
        (
            "Catalog failure stays in Entrance",
            "document.getElementById('tab-presentation-status').textContent.includes('could not be loaded') && document.getElementById('sequence-intro').options.length>0",
            "document.querySelector('[data-tab=presentation]').click()",
        ),
        (
            "Automatic catalog retry from Entrance",
            "Boolean(window.__cafState?.performance.catalog) && document.getElementById('sequence-intro').options.length>1",
            "document.querySelector('#tab-presentation [data-performance-retry]').click()",
        ),
        (
            "AI catalog reuse",
            "document.getElementById('ai-sliders').children.length>0",
            "document.querySelector('[data-tab=ai]').click()",
        ),
        (
            "Stage and prepare voice clips",
            "window.__cafState?.performance.settings.voice && document.getElementById('voice-preload-status').textContent.includes('clips prepared')",
            "document.querySelector('[data-tab=voice]').click();document.getElementById('voice-apply').click()",
        ),
        (
            "Voice starts without a separate Play click",
            "!document.getElementById('voice-audio').paused && document.getElementById('voice-audio').currentTime>0",
            "document.getElementById('voice-play').click()",
        ),
        (
            "Next clip plays immediately",
            "document.getElementById('voice-slot').selectedIndex===1 && !document.getElementById('voice-audio').paused && document.getElementById('voice-audio').currentTime>0",
            "document.getElementById('voice-next').click()",
        ),
        (
            "WAV save through native download handling",
            "!document.getElementById('voice-save').disabled",
            "document.getElementById('voice-save').click()",
        ),
        (
            "Named UI donors",
            "document.getElementById('ui-donor').options.length>=3",
            "document.querySelector('[data-tab=ui]').click()",
        ),
        (
            "Pending controls stay pinned",
            "parseInt(document.getElementById('changes-summary').textContent)===window.__cafState.changes.length && document.getElementById('save').getBoundingClientRect().bottom<innerHeight && document.getElementById('changes-summary').getBoundingClientRect().top>64",
            "document.querySelector('.panel-scroll').scrollTop=99999;document.getElementById('pending-changes').open=true",
        ),
        (
            "Readiness checklist",
            "document.getElementById('export-ready').open && document.querySelectorAll('#export-checks li').length>=7 && !document.getElementById('export-ready-confirm').disabled",
            "document.getElementById('export-mod').click()",
        ),
        (
            "Save before cancelled ZIP picker",
            "!document.getElementById('export-ready').open && !window.__cafState.dirty",
            "document.getElementById('export-ready-confirm').click()",
        ),
        (
            "Return Home for retail",
            "document.querySelectorAll('.home-card').length===4",
            "document.getElementById('home-button').click()",
        ),
        (
            "Retail standalone start",
            "window.__retailState?.donors.length===3 && document.getElementById('retail-start').open",
            "document.querySelectorAll('.home-card')[2].querySelector('button').click()",
        ),
        (
            "Single start donor",
            "['combat-donor','body-donor','ui-donor','deployment-target'].every(id=>document.getElementById(id).value==='retail/teck')",
            "let e=document.getElementById('base-donor');e.value='retail/teck';e.dispatchEvent(new Event('change'))",
        ),
        (
            "Retail portable project and empty viewer",
            "window.__retailState?.document?.definition.inherits==='retail/teck' && !document.getElementById('retail-start').open && !document.getElementById('preview-empty').hidden && !document.getElementById('donor-mixing').open",
            "document.getElementById('new').click()",
        ),
        (
            "Retail compact shell and full IDs",
            "document.querySelector('header').getBoundingClientRect().height<=64 && document.documentElement.scrollWidth<=innerWidth && document.getElementById('pack').getBoundingClientRect().width>=185",
            "document.querySelector('[data-panel=details]').click()",
        ),
        (
            "Body import automatically previews",
            "window.__retailPreview?.ready && document.getElementById('preview-empty').hidden && document.getElementById('shape').options[0].value==='A001'",
            "document.querySelector('[data-panel=appearance]').click();document.getElementById('empty-body').click()",
        ),
        (
            "Retail keyboard tabs",
            "document.querySelector('[data-panel=ai]').getAttribute('aria-selected')==='true' && document.getElementById('ai-sliders').children.length>0",
            "let e=document.querySelector('[data-panel=combat]');e.click();e.focus();e.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}))",
        ),
        (
            "Retail AI staging",
            "Boolean(window.__retailState?.performance.settings.ai)",
            "document.getElementById('ai-apply').click()",
        ),
        (
            "Retail voice preparation",
            "window.__retailState?.performance.settings.voice && document.getElementById('voice-preload-status').textContent.includes('clips prepared')",
            "document.querySelector('[data-panel=voice]').click();document.getElementById('voice-apply').click()",
        ),
        (
            "Retail voice plays",
            "!document.getElementById('voice-audio').paused && document.getElementById('voice-audio').currentTime>0",
            "document.getElementById('voice-next').click()",
        ),
        (
            "Retail entrance staging",
            "window.__retailState?.performance.settings.intro==='CI_113A'",
            "document.querySelector('[data-panel=presentation]').click();document.getElementById('sequence-intro').value='CI_113A';document.getElementById('apply-intro').click()",
        ),
        (
            "Retail animated entrance",
            "Boolean(window.__cafAnimation?.ready && window.__cafAnimation.time>0)",
            "document.getElementById('preview-intro').click()",
        ),
        (
            "Retail animation pause",
            "document.getElementById('animation-play').textContent==='Play'",
            "document.getElementById('animation-play').click()",
        ),
        (
            "Retail animation scrub",
            "window.__cafAnimation?.time===10",
            "let e=document.getElementById('animation-time');e.value=10;e.dispatchEvent(new Event('input'))",
        ),
        ("Retail animation stop", "window.__cafAnimation===null", "document.getElementById('animation-stop').click()"),
        (
            "Retail moves preserve stats and performance",
            "window.__retailState?.document.definition.inherits==='retail/blaze' && window.__retailState.document.definition.components.stats.health===20 && window.__retailState.performance.settings.voice.preset==='retail/teck'",
            "document.querySelector('[data-panel=combat]').click();document.getElementById('combat-donor').value='retail/blaze';document.getElementById('combat').click()",
        ),
        (
            "Retail shared export readiness",
            "document.getElementById('export-ready').open && !document.getElementById('export-ready-confirm').disabled",
            "document.getElementById('export').click()",
        ),
        (
            "Retail saves before ZIP chooser",
            "!document.getElementById('export-ready').open && !window.__retailState.dirty",
            "document.getElementById('export-ready-confirm').click()",
        ),
        (
            "Home for appearance workflow",
            "document.querySelectorAll('.home-card').length===4",
            "document.getElementById('home').click()",
        ),
        (
            "Retail appearance workflow",
            "document.body.dataset.mode==='retail-edit' && !window.__retailState?.document",
            "document.querySelectorAll('.home-card')[3].querySelector('button').click()",
        ),
        (
            "Retail override preserves combat",
            "window.__retailState?.document?.deployment?.mode==='override' && document.getElementById('combat').disabled && document.getElementById('apply-stats').disabled",
            "document.getElementById('new').click()",
        ),
        (
            "New button reopens setup",
            "document.getElementById('retail-start').open",
            "document.getElementById('new-open').click()",
        ),
        (
            "Retail extra-outfit mode",
            "window.__retailState?.document?.deployment?.mode==='outfit' && document.getElementById('combat').disabled",
            "document.getElementById('deployment-mode').value='outfit';document.getElementById('new').click()",
        ),
    ]
    evidence, started, state = (
        [],
        time.monotonic(),
        dict(index=0, action=False, checking=False, since=time.monotonic(), done=False),
    )
    timer = QTimer(window)

    def finish(error=None):
        if state["done"]:
            return
        state["done"] = True
        timer.stop()
        try:
            assert (data / "save/UserData/45410049" / directory_name("UITEST") / "UITEST").read_bytes()
            saved = Container.read((data / "save/UserData/45410049" / directory_name("UITEST") / "UITEST").read_bytes())
            assert saved.payload[0x3210:0x321B] == b"STORY BYTES"
            assert len(list((workspace / "backups").glob("*.djprofile"))) == 1
            assert calls["performance_connect"] == 2
            assert calls["performance_audio"] == 6  # Both playback actions reused the prepared clips.
            assert calls["retail_performance_audio"] == 6
            assert calls["retail_performance_connect"] == 1
            assert calls["retail_appearance"] == calls["retail_preview"] == 1
            assert any("Mod" in title for title in pickers)
            assert "Save voice clip" in pickers
            with wave.open(str(output / "audition.wav"), "rb") as saved_audio:
                assert saved_audio.getnframes() == 48000
            assert len(projects.read(output / "fighter.ffnyfighter")[0]["outfits"]) == 1
            assert projects.read(output / "retail.ffnyfighter")[0]["performance"]["intro"] == "CI_113A"
        except Exception as exc:
            error = error or repr(exc)
        (output / "receipt.json").write_text(
            json.dumps(
                dict(
                    passed=not error,
                    error=error,
                    checks=evidence,
                    calls=dict(calls),
                    seconds=round(time.monotonic() - started, 2),
                    scope="Invented saves/geometry/catalogs; native pickers adapted; no original assets or native game acceptance.",
                ),
                indent=2,
            ),
            encoding="utf-8",
        )
        app.exit(1 if error else 0)

    def tick():
        if state["done"] or state["checking"]:
            return
        if state["index"] >= len(steps):
            finish()
            return
        label, predicate, action = steps[state["index"]]
        if time.monotonic() - state["since"] > 15:
            finish("Timed out: " + label)
            return
        state["checking"] = True

        def checked(ok):
            state["checking"] = False
            if ok:
                if label == "Stat editing through WebChannel" and calls["preview"] != 1:
                    finish("A nonvisual stat edit rebuilt the preview.")
                    return
                evidence.append(label)
                print("[CHECK] " + label, flush=True)
                if args.capture:
                    window.grab().save(str(output / (str(state["index"]) + ".png")))
                state["index"] += 1
                state["action"] = False
                state["since"] = time.monotonic()

        if action and not state["action"]:
            state["action"] = True
            window.page.runJavaScript("(()=>{" + action + "})()", lambda _: state.update(checking=False))
        else:
            window.page.runJavaScript("Boolean(" + predicate + ")", checked)

    timer.timeout.connect(tick)
    timer.start(100)
    QTimer.singleShot(90000, lambda: finish("Tour exceeded 90 seconds"))
    result = app.exec()
    window.bridge.pool.shutdown(wait=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
