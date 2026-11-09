"""Exercise real atlas/portrait UI and persistence on marked disposable data.

Only native file pickers and confirmation responses are deterministic adapters.
The source project and atlas are read-only; every project write stays in output.
Original game assets must be supplied locally, never as test fixtures in Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog

from defjam_caf import desktop, projects


def main():
    parser = argparse.ArgumentParser()
    for name in ('data', 'workspace', 'project', 'atlas', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if not (args.data / '.caf-disposable-test-data').is_file():
        raise SystemExit('Refusing UI writes without the disposable-data marker')
    original, original_hash = projects.read(args.project)
    if not original.get('textures', {}).get('atlases'):
        raise SystemExit('This workflow requires a project with at least one imported atlas')
    atlas_raw = args.atlas.read_bytes()
    atlas_hash = hashlib.sha256(atlas_raw).hexdigest()
    args.output.mkdir(parents=True, exist_ok=False)
    working = args.output / 'source-copy.ffnyfighter'
    saved = args.output / 'saved-view.ffnyfighter'
    projects.write(working, original)
    paths = iter([working, saved])
    QFileDialog.getOpenFileName = lambda owner, title, *a, **k: (
        str(args.atlas if 'atlas' in title.lower() else next(paths)), 'PNG/project')
    QFileDialog.getSaveFileName = lambda *a, **k: (str(saved), 'Fighter project')

    class TestPage(desktop.Page):
        def javaScriptConfirm(self, origin, message):
            return True
    desktop.Page = TestPage
    app = QApplication(sys.argv[:1])
    window = desktop.Window(args.workspace, args.data)
    window.show()
    slots = json.dumps(sorted(original['textures']['atlases']), separators=(',', ':'))
    steps = [
        ('initial preview', 'window.__cafState?.selected && window.__cafPreview?.ready', None),
        ('open portable textured project', 'window.__cafState?.project && window.__cafPreview?.ready && JSON.stringify(window.__cafState.atlas_slots)===' + json.dumps(slots),
         "document.getElementById('open-project').click()"),
        ('atlas controls available', "!document.getElementById('import-atlas').disabled && !document.getElementById('atlas-slot').disabled",
         "document.querySelector('[data-tab=project]').click()"),
        ('clear is staged', 'window.__cafState.dirty && window.__cafState.atlas_slots.length===0 && window.__cafPreview?.ready',
         "document.getElementById('clear-atlases').click()"),
        ('reset restores saved art', '!window.__cafState.dirty && JSON.stringify(window.__cafState.atlas_slots)===' + json.dumps(slots) + ' && window.__cafPreview?.ready',
         "document.getElementById('reset').click()"),
        ('import through native picker', "window.__cafState.dirty && window.__cafState.atlas_slots.includes('a') && window.__cafPreview?.ready",
         "document.getElementById('atlas-slot').value='a';document.getElementById('import-atlas').click()"),
        ('capture textured portrait', 'window.__cafState.portrait_available && window.__cafState.dirty',
         "document.getElementById('capture-portrait').click()"),
        ('save portable copy', '!window.__cafState.dirty && window.__cafState.project_path===' + json.dumps(str(saved)),
         "document.getElementById('project-copy').click()"),
        ('reopen saved copy', '!window.__cafState.dirty && window.__cafState.portrait_available && window.__cafPreview?.ready',
         "document.getElementById('open-project').click()"),
    ]
    evidence = []
    state = {'index': 0, 'sent': False, 'checking': False, 'failed': None, 'started': time.monotonic()}
    timer = QTimer()

    def finish(error=None):
        timer.stop()
        if not error:
            try:
                result, _ = projects.read(saved)
                assert result['fighter'] == original['fighter']
                assert result['identity'] == original['identity']
                assert projects.atlas_bytes(result['textures']['atlases']['a']) == atlas_raw
                assert 'portrait' in result
                assert projects.read(args.project)[1] == original_hash
                assert hashlib.sha256(args.atlas.read_bytes()).hexdigest() == atlas_hash
            except Exception as exc:
                error = str(exc)
        state['failed'] = error
        window.grab().save(str(args.output / 'desktop-atlas.png'))
        (args.output / 'receipt.json').write_text(json.dumps({'passed': not error, 'error': error, 'steps': evidence,
                                                           'saved_project': str(saved)}, indent=2))
        print('FAILED: ' + error if error else 'Atlas UI and persistence passed', flush=True)
        QTimer.singleShot(500, lambda: app.exit(1 if error else 0))

    def tick():
        if state['checking']:
            return
        if state['index'] == len(steps):
            finish()
            return
        title, condition, action = steps[state['index']]
        if not state['sent']:
            state.update(sent=True, since=time.monotonic())
            if action:
                window.page.runJavaScript('(()=>{' + action + '})()')
        if time.monotonic() - state['since'] > (600 if state['index'] == 0 else 60):
            finish('Timed out during ' + title)
            return
        state['checking'] = True
        def checked(value):
            state['checking'] = False
            if value:
                evidence.append({'step': title, 'seconds': round(time.monotonic() - state['started'], 2)})
                print('PASS: ' + title, flush=True)
                state.update(index=state['index'] + 1, sent=False)
        window.page.runJavaScript('Boolean(' + condition + ')', checked)
    timer.timeout.connect(tick)
    timer.start(700)
    app.exec()
    window.bridge.pool.shutdown(wait=True)
    return 1 if state['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
