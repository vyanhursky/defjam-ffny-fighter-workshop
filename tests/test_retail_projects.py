"""Retail projects preserve portable assets and refuse unsafe/partial exports."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import pytest
from PIL import Image
from defjam_caf import projects,retail
from defjam_caf.editor import Editor
from defjam_caf.container import SaveError


def pack(root):
    root.mkdir();raw=b'invented model input';(root/'body.bin').write_bytes(raw)
    document={'schema':'fighter-registry-draft-1','id':'example','version':'1.0.0','requires':{},'overrides':[],
        'fighters':[{'id':'river','name':'River','inherits':'retail/example','components':{'appearance':'example/body'}}],
        'resources':[{'id':'body','kind':'appearance','compatibility':{'skeleton':'retail/binding-example'},
            'source':{'format':'invented-fixture','model':{'path':'body.bin','sha256':hashlib.sha256(raw).hexdigest()}}}]}
    (root/'fighters.json').write_text(json.dumps(document));return document


def test_portable_import_save_copy_reopen_and_stale_detection(tmp_path):
    root=tmp_path/'pack';pack(root);document=retail.import_pack(root,'river')
    assert retail.unblob(document['assets']['body.bin'])==b'invented model input'
    path=tmp_path/'river.ffnyfighter';digest=projects.write(path,document)
    assert projects.read(path)==(document,digest)
    assert str(root) not in path.read_text() and 'profile' not in document
    changed=copy.deepcopy(document);changed['metadata']['name']='River 2';projects.write(path,changed,digest)
    with pytest.raises(SaveError,match='changed on disk'):projects.write(path,document,digest)
    with pytest.raises(SaveError,match='already exists'):projects.write(path,document)


@pytest.mark.parametrize('change',[
    lambda d:d['assets']['body.bin'].update(data=base64.b64encode(b'changed').decode()),
    lambda d:d['assets'].update({'../body.bin':retail.blob(b'bad')}),
    lambda d:d['assets'].update({'BODY.bin':retail.blob(b'collision')}),
    lambda d:d['definition']['components'].update(stats={'health':True}),
    lambda d:d['definition']['components'].update(stats={'health':101}),
    lambda d:d['definition'].update(inherits='../wrong'),
    lambda d:d.update(profile='unexpected'),
])
def test_invalid_projects_are_refused(tmp_path,change):
    root=tmp_path/'pack';pack(root);d=retail.import_pack(root,'river');change(d)
    with pytest.raises(SaveError):retail.validate(d)


def test_transitive_json_assets_are_hash_checked(tmp_path):
    root=tmp_path/'pack';m=pack(root);raw=json.dumps({'sample':{'path':'body.bin','sha256':hashlib.sha256(b'invented model input').hexdigest()}}).encode()
    (root/'graph.json').write_bytes(raw);m['resources'][0]['source']['model']={'path':'graph.json','sha256':hashlib.sha256(raw).hexdigest()}
    (root/'fighters.json').write_text(json.dumps(m));d=retail.import_pack(root,'river')
    assert set(d['assets'])=={'graph.json','body.bin'}
    (root/'body.bin').write_bytes(b'changed')
    with pytest.raises(SaveError,match='hash changed'):retail.import_pack(root,'river')


def test_donor_changes_preserve_art_samples_transforms_and_undo(tmp_path):
    root=tmp_path/'pack';pack(root);e=Editor(tmp_path/'work');s=e.retail;s.request('import',{'folder':root,'fighter':'river'})
    original=copy.deepcopy(s.document);s.catalog={'fighters':[{'id':'other','name':'Other','components':{'stats':{'health':47}}}]}
    s.request('combat',{'donor':'retail/other'});native=retail.manifest(s.document)
    assert native['fighters'][0]['inherits']=='retail/other'
    assert native['resources'][0]['compatibility']=={'skeleton':'retail/binding-other'}
    assert s.document['assets']==original['assets'] and s.document['resources']==original['resources']
    s.request('undo',{});assert s.document==original


def test_component_fallback_and_export_only_stage_referenced_assets(tmp_path):
    root=tmp_path/'pack';pack(root);s=Editor(tmp_path/'work').retail;s.request('import',{'folder':root,'fighter':'river'})
    s.request('component',{'component':'appearance','resource':''})
    output=tmp_path/'stage';output.mkdir();native=s.stage(output,tmp_path)
    assert native['resources']==[] and not (output/'body.bin').exists()


def test_ui_bytes_history_and_failed_compilation_never_publish_zip(tmp_path,monkeypatch):
    s=Editor(tmp_path/'work').retail;s.request('new',{'donor':'retail/example'})
    stream=io.BytesIO();Image.new('RGBA',(32,32),(10,20,30,255)).save(stream,format='PNG');encoded=base64.b64encode(stream.getvalue()).decode()
    s.request('ui',{'role':'selector','png':encoded});assert s.document['ui_art']['images']['selector']==encoded
    s.request('undo',{});assert s.document['ui_art']['images']=={}
    data=tmp_path/'data';(data/'extracted').mkdir(parents=True);s.owner.data=data;s.runtime=tmp_path/'runtime'
    def refuse(*a):raise SaveError('rig mismatch')
    monkeypatch.setattr(s,'api',refuse);out=tmp_path/'fighter.zip'
    with pytest.raises(SaveError,match='rig mismatch'):s.request('export',{'path':out})
    assert not out.exists()


def test_incomplete_metadata_drafts_survive_other_actions_and_refuse_save(tmp_path):
    s=Editor(tmp_path/'work').retail;s.request('new',{'donor':'retail/example'})
    s.request('draft',{'metadata':{'name':'Draft','version':''},'identity':s.document['identity']})
    assert s.snapshot()['dirty'] and s.snapshot()['document']['metadata']['version']==''
    with pytest.raises(SaveError):s.request('save',{'path':tmp_path/'draft.ffnyfighter'})
    assert not (tmp_path/'draft.ffnyfighter').exists() and s.snapshot()['document']['metadata']['name']=='Draft'
    s.request('draft',{'metadata':{'name':'Draft','version':'1.0.0'},'identity':s.document['identity']})
    s.request('save',{'path':tmp_path/'draft.ffnyfighter'})
    assert projects.read(tmp_path/'draft.ffnyfighter')[0]['metadata']['name']=='Draft' and not s.snapshot()['dirty']


def test_portable_write_never_creates_an_unreadable_oversized_file(tmp_path,monkeypatch):
    monkeypatch.setattr(projects,'MAX_PROJECT',100)
    with pytest.raises(SaveError,match='size limit'):projects.write(tmp_path/'oversized.ffnyfighter',retail.new('retail/example'))
    assert not (tmp_path/'oversized.ffnyfighter').exists()


def test_texture_names_are_stable_scoped_and_four_portable_characters():
    mapping=retail.texture_namespace('example','body',['A001','br01','br02'])
    assert mapping==retail.texture_namespace('example','body',['A001','br01','br02'])
    assert mapping!=retail.texture_namespace('other','body',['A001','br01','br02'])
    assert all(len(v)==4 and v.isascii() and v.isalnum() for v in mapping.values()) and len(set(mapping.values()))==3
