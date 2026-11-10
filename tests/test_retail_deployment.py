import json
import pytest
from defjam_caf import retail,projects
from defjam_caf.editor import Editor
from defjam_caf.container import SaveError
from test_retail_projects import pack


@pytest.mark.parametrize('mode',['override','outfit'])
def test_portable_deployment_save_reopen_history(tmp_path,mode):
    e=Editor(tmp_path/'work');s=e.retail;s.request('new',dict(donor='retail/example',mode=mode))
    assert s.snapshot()['document']['deployment']==dict(mode=mode,target='retail/example')
    path=tmp_path/'test.ffnyfighter';s.request('save',dict(path=str(path)))
    assert projects.read(path)[0]==s.document
    with pytest.raises(SaveError,match='retain target'):s.request('stats',dict(stats={'health':50}))
    assert not s.snapshot()['dirty']


def test_imported_retail_override_and_outfit_retain_target(tmp_path):
    root=tmp_path/'pack';value=pack(root);fighter=value['fighters'][0]
    value['fighters'][0]['outfit_of']='retail/example';(root/'fighters.json').write_text(json.dumps(value))
    assert retail.import_pack(root,'river')['deployment']==dict(mode='outfit',target='retail/example')
    value['fighters']=[];value['overrides']=[dict(target='retail/example',components=fighter['components'],supersedes=[])]
    (root/'fighters.json').write_text(json.dumps(value))
    restored=retail.import_pack(root,'retail/example')
    assert restored['deployment']==dict(mode='override',target='retail/example')
    assert retail.unblob(restored['assets']['body.bin'])==b'invented model input'
