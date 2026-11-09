"""Real four-slot menu/persistence checks on marked disposable data only."""
import argparse
import json
from pathlib import Path
import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog

from defjam_caf import desktop, projects
from defjam_caf.assets import Database
from defjam_caf.blazin import Catalog
from defjam_caf.profiles import discover


def main():
    parser = argparse.ArgumentParser()
    for name in ('data', 'workspace', 'project', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if not (args.data / '.caf-disposable-test-data').is_file():
        raise SystemExit('Refusing UI writes without the disposable-data marker')
    args.output.mkdir(parents=True, exist_ok=False)
    catalog = Catalog(Database(args.data / 'extracted'))
    rows = sorted(catalog.options, key=lambda row: row['choice'])[:4]
    keys = [row['key'] for row in rows]
    expected = json.dumps(keys, separators=(',', ':'))
    reverse = json.dumps(keys[::-1], separators=(',', ':'))
    source, source_hash = projects.read(args.project)
    copied, saved = args.output / 'source-copy.ffnyfighter', args.output / 'edited-project.ffnyfighter'
    projects.write(copied, source)
    before_profiles = {p.name: p.container.payload for p in discover(args.data).profiles}
    save_paths = iter([args.output / 'profile-project.ffnyfighter', saved])
    open_paths = iter([copied, saved])
    QFileDialog.getSaveFileName = lambda *a, **k: (str(next(save_paths)), 'Fighter project')
    QFileDialog.getOpenFileName = lambda *a, **k: (str(next(open_paths)), 'Fighter project')

    class TestPage(desktop.Page):
        def javaScriptConfirm(self, origin, message):
            return True
    desktop.Page = TestPage
    app = QApplication(sys.argv[:1])
    window = desktop.Window(args.workspace, args.data)
    window.show()
    initial = 'window.__cafState.blazin.selected'
    equals = lambda value: 'JSON.stringify(' + initial + ')===' + json.dumps(value)
    choose = lambda value: 'let keys=' + value + ";keys.forEach((key,i)=>document.getElementById('blazin-'+i).value=key);"
    apply = "document.getElementById('apply-blazin').click()"
    steps = [
        ('load original catalog and profile', 'window.__cafState?.selected && window.__cafPreview?.ready && window.__cafState.blazin.options.length===' + str(len(catalog.options)), None),
        ('four complete named move selectors', "[0,1,2,3].every(i=>document.getElementById('blazin-'+i).querySelectorAll('optgroup option').length===" + str(len(catalog.options)) + ')', "window.__savedMoves=JSON.stringify(window.__cafState.blazin.selected);document.querySelector('[data-tab=blazin]').click()"),
        ('menu draft does not edit profile', '!window.__cafState.dirty', choose(expected)),
        ('apply stages four moves', 'window.__cafState.dirty && ' + equals(expected), apply),
        ('undo restores original assignments', '!window.__cafState.dirty && JSON.stringify(window.__cafState.blazin.selected)===window.__savedMoves', "document.getElementById('undo').click()"),
        ('duplicate moves are allowed', 'window.__cafState.dirty && ' + equals(json.dumps([keys[0]] * 4, separators=(',', ':'))), choose(json.dumps([keys[0]] * 4)) + apply),
        ('reset restores original assignments', '!window.__cafState.dirty', "document.getElementById('reset').click()"),
        ('stage profile assignments', 'window.__cafState.dirty && ' + equals(expected), choose(expected) + apply),
        ('save Story profile', '!window.__cafState.dirty && ' + equals(expected), "document.getElementById('save').click()"),
        ('reload Story assignments from disk', '!window.__cafState.dirty && ' + equals(expected), "document.querySelector('.profile-card.selected').click()"),
        ('convert edited CAF to project', 'window.__cafState.project && !window.__cafState.dirty && ' + equals(expected), "document.getElementById('new-project').click()"),
        ('inherit is staged for projects', 'window.__cafState.dirty && window.__cafState.blazin.selected.every(k=>k===null)', "document.getElementById('inherit-blazin').click()"),
        ('project undo restores four moves', '!window.__cafState.dirty && ' + equals(expected), "document.getElementById('undo').click()"),
        ('open textured project copy', 'window.__cafState.project_path===' + json.dumps(str(copied)) + ' && window.__cafPreview?.ready', "document.getElementById('open-project').click()"),
        ('apply different moves without invalidating art', 'window.__cafState.dirty && ' + equals(reverse) + ' && window.__cafPreview?.ready', choose(reverse) + apply),
        ('save edited portable copy', '!window.__cafState.dirty && window.__cafState.project_path===' + json.dumps(str(saved)), "document.getElementById('project-copy').click()"),
        ('reopen edited project', '!window.__cafState.dirty && ' + equals(reverse) + ' && window.__cafPreview?.ready', "document.getElementById('open-project').click()"),
    ]
    evidence = []
    state = dict(index=0, sent=False, checking=False, failed=None, started=time.monotonic())
    timer = QTimer()

    def finish(error=None):
        timer.stop()
        if not error:
            try:
                project = projects.read(saved)[0]
                assert project['fighter']['finishers'] == [row['record'] for row in rows[::-1]]
                assert project['identity'] == source['identity'] and project.get('textures') == source.get('textures')
                assert projects.read(args.project)[1] == source_hash
                changed = []
                for profile in discover(args.data).profiles:
                    before, after = before_profiles[profile.name], profile.container.payload
                    assert before[:0x120] == after[:0x120] and before[0x130:] == after[0x130:]
                    if before != after:
                        changed.append(profile.name)
                assert len(changed) == 1
            except Exception as exc:
                error = str(exc)
        state['failed'] = error
        window.grab().save(str(args.output / 'desktop-blazin.png'))
        (args.output / 'receipt.json').write_text(json.dumps(dict(passed=not error, error=error, steps=evidence,
            selected_moves=rows, saved_project=str(saved)), indent=2), encoding='utf-8')
        print('FAILED: ' + error if error else 'Blazin menu and persistence passed', flush=True)
        QTimer.singleShot(500, lambda: app.exit(1 if error else 0))

    def tick():
        if state['checking']:
            return
        if state['index'] == len(steps):
            finish(); return
        title, condition, action = steps[state['index']]
        if not state['sent']:
            state.update(sent=True, since=time.monotonic())
            if action:
                window.page.runJavaScript('(()=>{' + action + '})()')
        if time.monotonic() - state['since'] > (600 if state['index'] == 0 else 60):
            finish('Timed out during ' + title); return
        state['checking'] = True
        def checked(value):
            state['checking'] = False
            if value:
                evidence.append(dict(step=title, seconds=round(time.monotonic() - state['started'], 2)))
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
