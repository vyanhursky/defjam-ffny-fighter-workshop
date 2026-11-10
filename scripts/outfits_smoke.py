"""Exercise real three-outfit UI and persistence on marked disposable data.

Only native file pickers and confirmation responses are deterministic adapters.
The source project is read-only; every project write stays in output.
Original game assets must be supplied locally, never as test fixtures in Git.
"""
import argparse
import json
from pathlib import Path
import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog

from defjam_caf import desktop, projects


def main():
    parser = argparse.ArgumentParser()
    for name in ('data', 'workspace', 'project', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if not (args.data / '.caf-disposable-test-data').is_file():
        raise SystemExit('Refusing UI writes without the disposable-data marker')
    original, original_hash = projects.read(args.project)
    if not original.get('textures', {}).get('atlases'):
        raise SystemExit('This workflow requires a project with at least one imported atlas')
    args.output.mkdir(parents=True, exist_ok=False)
    working = args.output / 'source-copy.ffnyfighter'
    saved = args.output / 'saved-view.ffnyfighter'
    projects.write(working, original)
    paths = iter([working, saved])
    QFileDialog.getOpenFileName = lambda owner, title, *a, **k: (
        str(next(paths)), 'PNG/project')
    QFileDialog.getSaveFileName = lambda *a, **k: (str(saved), 'Fighter project')

    class TestPage(desktop.Page):
        def javaScriptConfirm(self, origin, message):
            return True
    desktop.Page = TestPage
    app = QApplication(sys.argv[:1])
    window = desktop.Window(args.workspace, args.data)
    window.show()
    if len(original.get('outfits', [])) != 2:
        raise SystemExit('This workflow requires three outfits')
    second, third = [row['id'] for row in original['outfits']]
    def select(identity):
        return "let e=document.getElementById('outfit-select');e.value=" + json.dumps(identity) + ";e.dispatchEvent(new Event('change'))"
    active = lambda identity: 'window.__cafState.active_outfit===' + json.dumps(identity) + ' && window.__cafPreview?.ready'
    steps = [
        ('initial preview', 'window.__cafState?.selected && window.__cafPreview?.ready', None),
        ('open three-outfit project', 'window.__cafState?.outfits.length===3 && window.__cafPreview?.ready', "document.getElementById('open-project').click()"),
        ('native outfit menu limit', "document.getElementById('add-outfit').disabled && document.getElementById('remove-outfit').disabled", "document.querySelector('[data-tab=project]').click()"),
        ('switch to second outfit', active(second), select(second)),
        ('rename second outfit is staged', "window.__cafState.dirty && window.__cafState.outfits[1].name==='UI temporary'", "document.getElementById('outfit-name').value='UI temporary';document.getElementById('rename-outfit').click()"),
        ('undo outfit name', 'window.__cafState.outfits[1].name!==' + json.dumps('UI temporary'), "document.getElementById('undo').click()"),
        ('switch to third outfit', active(third), select(third)),
        ('remove is staged', 'window.__cafState.outfits.length===2 && window.__cafState.dirty', "document.getElementById('remove-outfit').click()"),
        ('copy adds third outfit', 'window.__cafState.outfits.length===3 && window.__cafState.active_outfit!==' + json.dumps(third), "document.getElementById('add-outfit').click()"),
        ('undo copy', 'window.__cafState.outfits.length===2', "document.getElementById('undo').click()"),
        ('undo removal', 'window.__cafState.outfits.length===3 && ' + active(third), "document.getElementById('undo').click()"),
        ('reset collection', '!window.__cafState.dirty && window.__cafState.outfits.length===3 && window.__cafPreview?.ready', "document.getElementById('reset').click()"),
        ('select red jersey', active(second), select(second)),
        ('capture red jersey portrait', 'window.__cafState.portrait_available && window.__cafState.dirty', "document.getElementById('capture-portrait').click()"),
        ('select black tank', active(third), select(third)),
        ('capture black tank portrait', 'window.__cafState.portrait_available', "document.getElementById('capture-portrait').click()"),
        ('select shirtless', active('default'), select('default')),
        ('capture shirtless portrait', 'window.__cafState.portrait_available', "document.getElementById('capture-portrait').click()"),
        ('save all outfits', '!window.__cafState.dirty && window.__cafState.project_path===' + json.dumps(str(saved)), "document.getElementById('project-copy').click()"),
        ('reopen all outfits', '!window.__cafState.dirty && window.__cafState.outfits.length===3 && window.__cafPreview?.ready', "document.getElementById('open-project').click()"),
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
                assert len(result['outfits']) == 2
                assert all('portrait' in row for row in [result,*result['outfits']])
                assert projects.read(args.project)[1] == original_hash
            except Exception as exc:
                error = str(exc)
        state['failed'] = error
        window.grab().save(str(args.output / 'desktop-outfits.png'))
        (args.output / 'receipt.json').write_text(json.dumps({'passed': not error, 'error': error, 'steps': evidence,
                                                           'saved_project': str(saved)}, indent=2))
        print('FAILED: ' + error if error else 'Outfit UI and persistence passed', flush=True)
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
