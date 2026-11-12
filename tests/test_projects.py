import copy
import json
import struct

import pytest
from defjam_caf import projects
from defjam_caf.container import Container, SaveError
from defjam_caf.fields import read_fields
from defjam_caf.profiles import PROFILE_SIZE, discover, directory_name
from defjam_caf.editor import Editor


def fields():
    data=bytearray(PROFILE_SIZE)
    data[0x134:0x138]=bytes([0,255,255,87]);data[0x4d87]=87
    struct.pack_into('<38I',data,0x5558,*([2,2,1,1,1,1]+[1]*6+[0xffffffff]*26))
    data[0x2000:0x2006]=b'STORY!'
    data[0x14:0x18]=struct.pack('<I',12345)
    return read_fields(bytes(data)),bytes(data)


def test_project_drops_career_currency_and_paths_but_preserves_exact_choices(tmp_path):
    f,_=fields();p=projects.from_fields(f,'Example')
    raw=projects.encoded(p)
    assert b'STORY' not in raw and b'cash' not in raw and b'development' not in raw
    assert set(p['fighter'])=={'stats','styles','caf_values','caf_colors'}
    path=tmp_path/'example.ffnyfighter';digest=projects.write(path,p)
    loaded,actual=projects.read(path)
    assert loaded==p and actual==digest
    restored=read_fields(projects.container(p).payload)
    for key in p['fighter']:assert restored[key]==f[key]
    assert restored['cash']==0
    assert projects.container(p).payload[0x2000:0x2006]==bytes(6)


def test_project_stale_save_and_save_as_refuse_overwrite(tmp_path):
    p=projects.from_fields(fields()[0],'Example');path=tmp_path/'fighter.ffnyfighter'
    digest=projects.write(path,p)
    with pytest.raises(SaveError):projects.write(path,p)
    changed=copy.deepcopy(p);changed['metadata']['name']='External'
    path.write_bytes(projects.encoded(changed))
    with pytest.raises(SaveError,match='changed on disk'):projects.write(path,p,digest)
    assert projects.read(path)[0]==changed


@pytest.mark.parametrize('change',[
    lambda p:p.update(career='private'),lambda p:p['fighter'].update(cash=100),
    lambda p:p['identity'].update(pack='../escape'),lambda p:p['fighter'].update(styles=[1,1]),
    lambda p:p['fighter']['stats'].update(health=True),lambda p:p['metadata'].update(version='1'),
    lambda p:p['fighter']['caf_values'].__setitem__(0,99),
])
def test_invalid_or_unknown_project_data_is_rejected(change):
    p=projects.from_fields(fields()[0],'Example');change(p)
    with pytest.raises((SaveError,ValueError)):projects.validate(p)


def test_open_edit_save_and_copy_project_without_any_source_profile(tmp_path):
    p=projects.from_fields(fields()[0],'Example');path=tmp_path/'fighter.ffnyfighter';projects.write(path,p)
    e=Editor(tmp_path/'workspace');e.open_project(path)
    state=e.stage({'stats':{'health':42},'styles':[1,4]})
    assert state['dirty'] and e.profile is None
    with pytest.raises(SaveError,match='currency'):e.stage({'cash':1})
    e.request('save',{})
    assert not e.snapshot()['dirty']
    assert projects.read(path)[0]['fighter']['stats']['health']==42
    e.stage({'stats':{'speed':37}});copy_path=tmp_path/'copy.ffnyfighter'
    e.request('export',{'path':str(copy_path)})
    assert projects.read(copy_path)[0]['fighter']['stats']['speed']==37
    assert projects.read(path)[0]['fighter']['stats']['speed']!=37
    assert projects.read(path)[0]['identity']==projects.read(copy_path)[0]['identity']


def test_project_duplicate_json_keys_and_oversize_rejected(tmp_path):
    path=tmp_path/'bad.ffnyfighter';path.write_text('{"schema":1,"schema":2}')
    with pytest.raises(SaveError,match='Duplicate'):projects.read(path)
    path.write_bytes(b' '*(projects.MAX_PROJECT+1))
    with pytest.raises(SaveError,match='large'):projects.read(path)


def test_project_portrait_is_validated_and_survives_save_reopen(tmp_path):
    import base64,io
    from PIL import Image
    stream=io.BytesIO();Image.new('RGBA',(64,64),(255,0,0,255)).save(stream,format='PNG')
    encoded=base64.b64encode(stream.getvalue()).decode('ascii')
    p=projects.from_fields(fields()[0],'Example');path=tmp_path/'fighter.ffnyfighter';projects.write(path,p)
    e=Editor(tmp_path/'workspace');e.open_project(path)
    state=e.request('project_portrait',{'png':encoded})
    assert state['dirty'] and state['portrait_available'] and e.project.get('portrait') is None
    e.request('save',{});e.open_project(path)
    assert projects.portrait_bytes(e.project['portrait'])==stream.getvalue()
    with pytest.raises(SaveError):e.request('project_portrait',{'png':'bogus'})
    assert not e.snapshot()['dirty']


def test_project_details_draft_survives_other_edits_and_failed_save(tmp_path):
    p=projects.from_fields(fields()[0],'Example');path=tmp_path/'fighter.ffnyfighter';projects.write(path,p)
    e=Editor(tmp_path/'workspace');e.open_project(path)
    draft={'metadata':dict(p['metadata'],name='Draft',version=''), 'identity':p['identity']}
    state=e.request('project_metadata_draft',draft)
    assert state['dirty'] and state['project']['metadata']['name']=='Draft'
    assert e.stage({'stats':{'health':42}})['project']['metadata']['version']==''
    with pytest.raises(SaveError):e.request('save',{})
    assert projects.read(path)[0]==p and e.snapshot()['dirty']
    draft['metadata']['version']='1.2.3';e.request('project_metadata_draft',draft)
    e.request('save',{})
    assert projects.read(path)[0]['metadata']['name']=='Draft'
    assert projects.read(path)[0]['fighter']['stats']['health']==42
    e.request('project_metadata_draft',dict(draft,metadata=dict(draft['metadata'],name='Discard')))
    assert not e.request('reset',{})['dirty']
    assert e.snapshot()['project']['metadata']['name']=='Draft'


def test_failed_mod_validation_never_publishes_archive(tmp_path,monkeypatch):
    from defjam_caf import fighter_mod
    runtime=tmp_path/'runtime';(runtime/'setup').mkdir(parents=True);(runtime/'scripts').mkdir()
    (runtime/'setup/fighter_caf.py').touch();(runtime/'scripts/fighter-contract.py').touch()
    data=tmp_path/'data';(data/'extracted').mkdir(parents=True)
    def refuse(*args,**kwargs):raise SaveError('invalid asset')
    monkeypatch.setattr(fighter_mod,'contract',refuse)
    destination=tmp_path/'fighter.zip'
    with pytest.raises(SaveError,match='invalid asset'):
        fighter_mod.export_mod(projects.from_fields(fields()[0],'Example'),destination,runtime,data,tmp_path/'work')
    assert not destination.exists() and not list((tmp_path/'work').iterdir())


def test_invalid_compiler_receipt_is_an_actionable_export_error(tmp_path,monkeypatch):
    from defjam_caf import fighter_mod
    from types import SimpleNamespace
    monkeypatch.setattr(fighter_mod.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout='unexpected output',stderr=''))
    with pytest.raises(SaveError,match='invalid validation receipt'):
        fighter_mod.contract(tmp_path,[],tmp_path,tmp_path)


def test_new_variant_from_standalone_project_keeps_credits_but_gets_new_identity(tmp_path):
    p=projects.from_fields(fields()[0],'Example',{'author':'Creator','license':'Example credit'})
    path=tmp_path/'original.ffnyfighter';projects.write(path,p)
    e=Editor(tmp_path/'workspace');e.open_project(path);e.stage({'stats':{'health':27}})
    variant=tmp_path/'variant.ffnyfighter';e.create_project(variant)
    saved=projects.read(variant)[0]
    assert saved['identity']!=p['identity'] and saved['metadata']==p['metadata']
    assert saved['fighter']['stats']['health']==27 and projects.read(path)[0]==p


@pytest.mark.parametrize('earlier', projects.EARLIER_SCHEMAS)
def test_projects_saved_under_an_earlier_schema_open_unchanged_and_save_as_current(tmp_path, earlier):
    f, _ = fields(); p = projects.from_fields(f, 'Example')
    p['schema'] = earlier
    path = tmp_path / 'old.ffnyfighter'
    raw = (json.dumps(p, indent=2, sort_keys=True) + '\n').encode()
    path.write_bytes(raw)
    loaded, digest = projects.read(path)
    assert loaded['schema'] == projects.SCHEMA and loaded['fighter'] == p['fighter']
    # The disk digest still names the bytes that were read, so a concurrent edit is still caught.
    assert digest == projects.sha(raw)
    projects.write(path, loaded, digest)
    assert json.loads(path.read_text())['schema'] == projects.SCHEMA


def test_unknown_project_versions_are_refused(tmp_path):
    f, _ = fields(); p = projects.from_fields(f, 'Example')
    for schema in ('ffny-fighter-project-0', 'ffny-fighter-project-8', 'other'):
        p['schema'] = schema
        with pytest.raises(SaveError):
            projects.validate(p)


def test_every_optional_section_is_accepted_on_a_project_with_no_other_section():
    f, _ = fields()
    for section, value in (('outfit_name', 'Outfit 1'), ):
        p = projects.from_fields(f, 'Example'); p[section] = value
        with pytest.raises(SaveError):   # outfits need both their name and their list
            projects.validate(p)
    p = projects.from_fields(f, 'Example'); p.update(outfit_name='Outfit 1', outfits=[])
    assert projects.validate(p)['schema'] == projects.SCHEMA
    p = projects.from_fields(f, 'Example'); p['fighter']['finishers'] = ['00000001'] * 4
    assert projects.validate(p)['fighter']['finishers'] == ['00000001'] * 4
