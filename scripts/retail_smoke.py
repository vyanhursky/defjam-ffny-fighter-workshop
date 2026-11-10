"""Real Qt/WebChannel retail project workflow with isolated output copies."""
import argparse
import base64
import json
from pathlib import Path
import sys
import time
from PySide6.QtCore import QTimer,QUrl,Qt
from PySide6.QtWidgets import QApplication,QFileDialog
from defjam_caf import desktop,projects


def main():
    parser=argparse.ArgumentParser()
    for key in ('data','workspace','project','runtime','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    original,digest=projects.read(args.project);working=args.output/'working.ffnyfighter';saved=args.output/'saved.ffnyfighter';archive=args.output/'fighter.zip'
    projects.write(working,original)
    images=original['ui_art']['images'];sample=args.output/'portrait.png';sample.write_bytes(projects.portrait_bytes(images['selector']))
    opens=iter([working,saved]);saves=iter([saved,archive])
    QFileDialog.getOpenFileName=lambda owner,title,*a,**k:(str(sample if 'artwork' in title.lower() else next(opens)),'')
    QFileDialog.getSaveFileName=lambda *a,**k:(str(next(saves)),'')
    QFileDialog.getExistingDirectory=lambda *a,**k:str(args.runtime)
    class Page(desktop.Page):
        def javaScriptConfirm(self,origin,message):return True
    desktop.Page=Page
    app=QApplication(sys.argv[:1]);window=desktop.Window(args.workspace,None)
    window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating,True)
    window.bridge.editor.data=args.data.resolve()
    window.web.setUrl(QUrl.fromLocalFile(str(Path(desktop.__file__).parent/'resources/retail.html')));window.show()
    setvalue=lambda key,value:"document.getElementById("+json.dumps(key)+").value="+json.dumps(value)
    steps=[
        ('retail studio initializes','window.__retailState?.retail && !window.__retailState.document',None),
        ('verified runtime catalog loads','window.__retailState.donors.length===75',"document.getElementById('runtime').click()"),
        ('portable owned fighter opens',"window.__retailState.document?.metadata.name==='DMX' && !window.__retailState.dirty","document.getElementById('open').click()"),
        ('actual model preview decodes','window.__retailPreview?.ready && window.__retailPreview.meshes>0',"document.getElementById('preview').click()"),
        ('Teck combat donor and native stats',"window.__retailState.document.definition.inherits==='retail/teck' && document.getElementById('stat-health').value==='47'",None),
        ('static model exposes texture shapes',"document.getElementById('shape').options.length>0",None),
        ('stage changed native stats',"window.__retailState.dirty && window.__retailState.document.definition.components.stats.health===48",setvalue('stat-health','48')+";document.getElementById('apply-stats').click()"),
        ('undo restores inherited stats',"!window.__retailState.document.definition.components.stats && !window.__retailState.dirty","document.getElementById('undo').click()"),
        ('explicit finisher fallback stages',"!window.__retailState.document.definition.components.blazin && window.__retailState.dirty",setvalue('resource-blazin','')+";document.getElementById('resource-blazin').dispatchEvent(new Event('change'))"),
        ('undo preserves supplied DMX finisher',"Boolean(window.__retailState.document.definition.components.blazin)","document.getElementById('undo').click()"),
        ('UI master roles and advanced variants','document.getElementById(\'role\').options.length===30',"document.querySelector('[data-panel=art]').click()"),
        ('loading role previews exact source','document.getElementById(\'art-image\').src.startsWith(\'data:image/png;base64,\')',setvalue('role','loading')+";document.getElementById('role').dispatchEvent(new Event('change'))"),
        ('clear role stages without losing defaults',"!window.__retailState.document.ui_art.images.loading && window.__retailState.dirty","document.getElementById('ui-clear').click()"),
        ('undo restores loading artwork',"Boolean(window.__retailState.document.ui_art.images.loading)","document.getElementById('undo').click()"),
        ('project copy saves complete assets',"window.__retailState.path==="+json.dumps(str(saved))+" && !window.__retailState.dirty","document.getElementById('copy').click()"),
        ('saved project reopens',"window.__retailState.path==="+json.dumps(str(saved))+" && !window.__retailState.dirty && window.__retailState.document.asset_count>0","document.getElementById('open').click()"),
        ('complete actual native export',"document.getElementById('status-message').textContent.includes('Validated retail fighter exported')","document.getElementById('export').click()"),
    ]
    state={'index':0,'sent':False,'checking':False,'failed':None,'started':time.monotonic()};evidence=[];timer=QTimer()
    def finish(error=None):
        timer.stop()
        if not error:
            try:
                assert projects.read(args.project)[1]==digest
                assert projects.read(saved)[0]==original and archive.is_file()
            except Exception as exc:error=str(exc)
        state['failed']=error;window.grab().save(str(args.output/'retail-studio.png'))
        (args.output/'receipt.json').write_text(json.dumps({'passed':not error,'error':error,'steps':evidence,'project':str(saved),'zip':str(archive)},indent=2))
        print('FAILED: '+error if error else 'Retail studio workflow and native export passed',flush=True)
        QTimer.singleShot(300,lambda:app.exit(1 if error else 0))
    def tick():
        if state['checking']:return
        if state['index']==len(steps):finish();return
        title,condition,action=steps[state['index']]
        if not state['sent']:
            state.update(sent=True,since=time.monotonic())
            if action:window.page.runJavaScript('(()=>{'+action+'})()')
        if time.monotonic()-state['since']>180:finish('Timed out: '+title);return
        state['checking']=True
        def checked(value):
            state['checking']=False
            if value:
                evidence.append({'step':title,'seconds':round(time.monotonic()-state['started'],2)});print('PASS: '+title,flush=True)
                state.update(index=state['index']+1,sent=False)
        window.page.runJavaScript('Boolean('+condition+')',checked)
    timer.timeout.connect(tick);timer.start(600);app.exec();window.bridge.pool.shutdown(wait=True)
    return 1 if state['failed'] else 0


if __name__=='__main__':raise SystemExit(main())
