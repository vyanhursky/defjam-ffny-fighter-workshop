import base64
import copy
import pytest
from defjam_caf import projects,outfits,ui_art
from defjam_caf.container import SaveError
from defjam_caf.editor import Editor
from test_projects import fields
from test_project_atlases import png


def encoded(color=(120,30,20,255)):
    return base64.b64encode(png(color=color)).decode()


def source():return projects.from_fields(fields()[0],'Example')


def test_old_projects_remain_unchanged_until_explicit_ui_edit():
    for original in (source(),outfits.upgrade(source())):
        before=projects.encoded(original)
        status=ui_art.status(original,'default')
        assert len(status['roles'])==30 and status['imported']==0
        assert projects.encoded(original)==before
        changed=ui_art.edit(original,'default',role='selector',png=encoded())
        assert changed['schema']==projects.SCHEMA4 and projects.validate(changed) is changed
        assert projects.encoded(original)==before
    invalid=source();invalid['ui_art']={'images':{}}
    with pytest.raises(SaveError,match='version 4'):projects.validate(invalid)


@pytest.mark.parametrize('pack',[
    {'images':{'unknown':encoded()}}, {'images':{'selector':'bad base64'}},
    {'images':{},'hd_scale':True}, {'images':{},'hd_scale':3},
    {'images':{},'donor':'../escape'}, {'images':{},'commands':['run']},
    {'images':{'icon':encoded((0,0,0,0))}},
])
def test_ui_assets_refuse_unknown_roles_paths_sizes_and_transparent_images(pack):
    with pytest.raises(SaveError):ui_art.validate(pack)


def test_default_images_inherit_and_local_master_beats_parent_specific_variant():
    project,second=outfits.add(source())
    project=ui_art.edit(project,'default',role='selector_2p',png=encoded())
    inherited=ui_art.resolved(project,second)
    assert inherited['images']['selector_2p']==encoded()
    different=encoded((40,80,120,255))
    project=ui_art.edit(project,second,role='selector',png=different)
    assert ui_art.resolved(project,second)['images']['selector_2p']==different
    assert ui_art.resolved(project,'default')['images']['selector_2p']==encoded()
    project=ui_art.edit(project,second,role='selector')
    assert ui_art.resolved(project,second)['images']['selector_2p']==encoded()
    project,third=outfits.add(project)
    assert 'ui_art' not in ui_art.node(project,third)
    assert ui_art.resolved(project,third)['images']['selector_2p']==encoded()


def test_aggregate_ui_budget_covers_every_outfit(monkeypatch):
    project,second=outfits.add(source());project=ui_art.edit(project,'default',role='selector',png=encoded())
    project=ui_art.edit(project,second,role='loading',png=encoded())
    monkeypatch.setattr(ui_art,'MAX_TOTAL',len(base64.b64decode(encoded()))+1)
    with pytest.raises(SaveError,match='Combined UI'):projects.validate(project)


def test_editor_ui_import_switch_undo_reset_save_copy_and_variant(tmp_path):
    path=tmp_path/'fighter.ffnyfighter';project,second=outfits.add(source());projects.write(path,project)
    editor=Editor(tmp_path);editor.open_project(path)
    editor.request('ui_settings',{'donor':'retail/pockets','hd_scale':4})
    editor.request('ui_import',{'role':'titlecard','png':encoded()})
    editor.request('outfit_select',{'id':second})
    state=editor.snapshot();assert state['ui_art']['donor']=='retail/pockets' and state['dirty']
    preview=editor.request('ui_preview',{'role':'loading_logo_4p'});assert preview['png'].endswith(encoded())
    other=encoded((40,80,120,255));editor.request('ui_import',{'role':'loading_2p','png':other})
    assert editor.request('ui_preview',{'role':'loading_2p'})['png'].endswith(other)
    editor.request('undo',{});assert editor.request('ui_preview',{'role':'loading_2p'})['png'] is None
    editor.request('ui_import',{'role':'loading_2p','png':other})
    editor.request('save',{});saved=projects.read(path)[0]
    assert saved['fighter']==project['fighter'] and saved['identity']==project['identity']
    assert saved['outfits'][0]['ui_art']['images']['loading_2p']==other
    editor.request('ui_clear_all',{});assert editor.snapshot()['dirty']
    editor.request('reset',{});assert not editor.snapshot()['dirty']
    assert editor.request('ui_preview',{'role':'loading_2p'})['png'].endswith(other)
    copy_path=tmp_path/'copy.ffnyfighter';editor.request('export',{'path':str(copy_path)})
    assert projects.read(copy_path)[0]==saved
    editor.create_project(tmp_path/'variant.ffnyfighter')
    assert editor.project['identity']!=saved['identity'] and editor.project['ui_art']==saved['ui_art']
    assert editor.project['outfits']==saved['outfits']


def test_failed_ui_import_keeps_saved_file_and_staged_state(tmp_path):
    path=tmp_path/'source.ffnyfighter';projects.write(path,source());editor=Editor(tmp_path);editor.open_project(path)
    editor.request('ui_import',{'role':'titlecard','png':encoded()});before=editor.project_document()
    with pytest.raises(SaveError):editor.request('ui_import',{'role':'selector','png':'not an image'})
    assert editor.project_document()==before and projects.read(path)[0]['schema']==projects.SCHEMA


def test_export_embeds_exact_role_pngs_and_all_outfit_references(tmp_path, monkeypatch):
    import hashlib,json,zipfile
    from defjam_caf import fighter_mod
    runtime=tmp_path/'runtime';(runtime/'setup').mkdir(parents=True);(runtime/'scripts').mkdir()
    (runtime/'setup/fighter_caf.py').touch();(runtime/'scripts/fighter-contract.py').touch()
    data=tmp_path/'data';(data/'extracted').mkdir(parents=True)
    project,second=outfits.add(source())
    project=ui_art.edit(project,'default',role='titlecard',png=encoded())
    project=ui_art.edit(project,'default',role='selector',png=encoded((80,100,120,255)))
    override=encoded((100,200,30,255))
    project=ui_art.edit(project,second,role='loading_3p',png=override)
    calls=[]
    def contract(runtime,args,temporary,workspace):
        calls.append(args[0]);return {'ok':True,'native_compilation':True}
    monkeypatch.setattr(fighter_mod,'contract',contract)
    destination=tmp_path/'fighter.zip';fighter_mod.export_mod(project,destination,runtime,data,tmp_path/'work')
    assert calls==['validate']
    prefix=project['identity']['pack']+'/'
    with zipfile.ZipFile(destination) as archive:
        manifest=json.loads(archive.read(prefix+'fighters.json'))
        recipe=json.loads(archive.read(prefix+'fighter.json'))
        assert manifest['resources'][0]['source']['format']=='caf-fighter-3'
        assert set(recipe['portraits'])=={'default',second} and len(recipe['outfits'])==1
        resources=manifest['resources'][1:];assert len(resources)==2
        for resource in resources:
            spec=resource['source'];assert spec['format']=='eagl-portrait-png-1'
            assert spec['donor']==project['metadata']['donor'] and spec['hd_scale']==4
            for part,descriptor in spec['images'].items():
                raw=archive.read(prefix+descriptor['path'])
                assert hashlib.sha256(raw).hexdigest()==descriptor['sha256']
                expected=ui_art.resolved(project,'default' if resource==resources[0] else second)['images'][part]
                assert raw==base64.b64decode(expected)
        assert resources[1]['source']['images']['loading_3p']['sha256']==hashlib.sha256(base64.b64decode(override)).hexdigest()
