"""Real role-import/retail-reference/export UI acceptance on disposable data."""
import argparse
import base64
import json
from pathlib import Path
import sys
import time

from PIL import Image,ImageDraw
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QFileDialog
from defjam_caf import desktop,projects,ui_art


def main():
    parser=argparse.ArgumentParser()
    for name in ('data','workspace','project','runtime','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if not (args.data/'.caf-disposable-test-data').is_file():raise SystemExit('Disposable-data marker is required')
    original,original_hash=projects.read(args.project)
    if len(original.get('outfits',[]))!=2:raise SystemExit('Use a three-outfit source project')
    args.output.mkdir(parents=True,exist_ok=False)
    working=args.output/'source-copy.ffnyfighter';saved=args.output/'saved-ui-project.ffnyfighter';archive=args.output/'ui-fighter.zip'
    projects.write(working,original)
    sample=args.output/'invented-ui-test.png';image=Image.new('RGBA',(80,40));draw=ImageDraw.Draw(image)
    draw.rectangle((4,4,38,35),fill=(220,30,60,255));draw.rectangle((42,4,75,35),fill=(20,100,230,255));image.save(sample)
    encoded=base64.b64encode(sample.read_bytes()).decode();expected='data:image/png;base64,'+encoded
    opens=iter([working,saved]);saves=iter([saved,archive])
    QFileDialog.getOpenFileName=lambda owner,title,*a,**k:(str(sample if 'portrait' in title.lower() or 'artwork' in title.lower() else next(opens)),'PNG/project')
    QFileDialog.getSaveFileName=lambda *a,**k:(str(next(saves)),'Project/ZIP')
    QFileDialog.getExistingDirectory=lambda *a,**k:str(args.runtime)
    class Page(desktop.Page):
        def javaScriptConfirm(self,origin,message):return True
    desktop.Page=Page
    app=QApplication(sys.argv[:1]);window=desktop.Window(args.workspace,args.data);window.show()
    second,third=[row['id'] for row in original['outfits']]
    select=lambda identity:"let e=document.getElementById('outfit-select');e.value="+json.dumps(identity)+";e.dispatchEvent(new Event('change'))"
    role=lambda key:"let e=document.getElementById('ui-role');e.value="+json.dumps(key)+";e.dispatchEvent(new Event('change'))"
    settings="document.getElementById('ui-donor').value='retail/pockets';document.getElementById('ui-scale').value='4';document.getElementById('ui-apply-settings').click()"
    imported='window.__cafState.ui_art.imported===24'
    preview='window.__cafUIArt?.ready && window.__cafUIArt.hasImage'
    steps=[
        ('profile controls stay protected',"window.__cafState?.selected && !window.__cafState.project && document.getElementById('ui-import').disabled",None),
        ('open original three-outfit copy','window.__cafState?.outfits.length===3 && window.__cafPreview?.ready',"document.getElementById('open-project').click()"),
        ('UI artwork tab and complete role menu',"document.getElementById('ui-role').options.length===30 && !document.getElementById('ui-import').disabled","document.querySelector('[data-tab=ui]').click()"),
        ('stage independent UI donor and HD scale',"window.__cafState.ui_art.donor==='retail/pockets' && window.__cafState.ui_art.hd_scale===4 && window.__cafState.dirty",settings),
        ('import 24 original retail roles',imported+' && '+preview,"document.getElementById('ui-retail').click()"),
        ('inspect selector titlecard',"window.__cafUIArt?.role==='selector_logo_2p' && "+preview,role('selector_logo_2p')),
        ('clear one override is staged','window.__cafState.ui_art.imported===23',"document.getElementById('ui-clear').click()"),
        ('undo restores titlecard',imported+' && '+preview,"document.getElementById('undo').click()"),
        ('PNG picker imports exact supplied bytes',"document.getElementById('ui-image').src==="+json.dumps(expected),"document.getElementById('ui-import').click()"),
        ('undo PNG preserves imported retail set',imported+" && document.getElementById('ui-image').src!=="+json.dumps(expected)+' && '+preview,"document.getElementById('undo').click()"),
        ('second outfit inherits default UI',"window.__cafState.active_outfit==="+json.dumps(second)+" && window.__cafState.ui_art.imported===0 && "+preview,select(second)),
        ('choose loading portrait',"window.__cafUIArt?.role==='loading_2p' && "+preview,role('loading_2p')),
        ('stage outfit-specific loading art',"document.getElementById('ui-image').src==="+json.dumps(expected),"document.getElementById('ui-import').click()"),
        ('clear override restores inherited artwork',"window.__cafState.ui_art.imported===0 && document.getElementById('ui-image').src!=="+json.dumps(expected)+' && '+preview,"document.getElementById('ui-clear').click()"),
        ('undo restores outfit override',"window.__cafState.ui_art.imported===1 && document.getElementById('ui-image').src==="+json.dumps(expected),"document.getElementById('undo').click()"),
        ('reset restores earlier project format',"!window.__cafState.dirty && window.__cafState.project.schema==="+json.dumps(original['schema']),"document.getElementById('reset').click()"),
        ('return to default outfit',"window.__cafState.active_outfit==='default'",select('default')),
        ('stage final placeholder settings',"window.__cafState.ui_art.donor==='retail/pockets' && window.__cafState.dirty",settings),
        ('stage final full UI set',imported,"document.getElementById('ui-retail').click()"),
        ('save complete portable copy',"!window.__cafState.dirty && window.__cafState.project_path==="+json.dumps(str(saved)),"document.getElementById('project-copy').click()"),
        ('reopen persistent UI assets',imported+' && !window.__cafState.dirty && '+preview,"document.getElementById('open-project').click()"),
        ('third outfit inherits saved art',"window.__cafState.active_outfit==="+json.dumps(third)+" && window.__cafState.ui_art.imported===0 && !window.__cafState.dirty && "+preview,select(third)),
        ('export actual fully compiled fighter',"document.getElementById('status-message').textContent.includes('Validated Custom Fighter Mod exported')","document.getElementById('export-mod').click()"),
    ]
    state=dict(index=0,sent=False,checking=False,failed=None,started=time.monotonic());evidence=[];timer=QTimer()
    def finish(error=None):
        timer.stop()
        if not error:
            try:
                document=projects.read(saved)[0]
                assert document['schema']==projects.SCHEMA4 and document['identity']==original['identity'] and document['fighter']==original['fighter']
                assert len(document['ui_art']['images'])==24 and document['ui_art']['donor']=='retail/pockets'
                assert all('ui_art' not in row for row in document['outfits'])
                assert projects.read(args.project)[1]==original_hash and archive.is_file()
            except Exception as exc:error=str(exc)
        state['failed']=error;window.grab().save(str(args.output/'desktop-ui-art.png'))
        (args.output/'receipt.json').write_text(json.dumps(dict(passed=not error,error=error,steps=evidence,project=str(saved),archive=str(archive)),indent=2))
        print('FAILED: '+error if error else 'Full UI artwork workflow and native export passed',flush=True)
        QTimer.singleShot(500,lambda:app.exit(1 if error else 0))
    def tick():
        if state['checking']:return
        if state['index']==len(steps):finish();return
        title,condition,action=steps[state['index']]
        if not state['sent']:
            state.update(sent=True,since=time.monotonic())
            if action:window.page.runJavaScript('(()=>{'+action+'})()')
        if time.monotonic()-state['since']>180:finish('Timed out during '+title);return
        state['checking']=True
        def checked(value):
            state['checking']=False
            if value:
                evidence.append(dict(step=title,seconds=round(time.monotonic()-state['started'],2)));print('PASS: '+title,flush=True)
                state.update(index=state['index']+1,sent=False)
        window.page.runJavaScript('Boolean('+condition+')',checked)
    timer.timeout.connect(tick);timer.start(700);app.exec();window.bridge.pool.shutdown(wait=True)
    return 1 if state['failed'] else 0


if __name__=='__main__':raise SystemExit(main())
