import copy

import pytest

from defjam_caf import projects, outfits
from defjam_caf.container import SaveError
from defjam_caf.editor import Editor
from test_projects import fields
from test_project_atlases import png


def source():
    return projects.with_atlas(projects.from_fields(fields()[0], 'Example'), 'a', png())


def test_export_keeps_one_fighter_and_all_outfit_atlases_and_portrait_references(tmp_path, monkeypatch):
    import base64, hashlib, json, zipfile
    from pathlib import Path
    from defjam_caf import fighter_mod
    runtime=tmp_path/'runtime';(runtime/'setup').mkdir(parents=True);(runtime/'scripts').mkdir()
    (runtime/'setup/fighter_caf.py').touch();(runtime/'scripts/fighter-contract.py').touch()
    data=tmp_path/'data';(data/'extracted').mkdir(parents=True)
    document=source();document['portrait']=base64.b64encode(png()).decode()
    document,second=outfits.add(document);document,third=outfits.add(document)
    for index,identity in enumerate(('default',second,third)):
        view=outfits.view(document,identity)
        view=projects.with_atlas(view,'a',png(color=(index,20,30,255)))
        document=outfits.replace_view(document,identity,view)
    def contract(runtime,args,temporary,workspace):
        if args[0]=='export-caf-portrait':
            destination=Path(args[args.index('--portrait-out')+1]);destination.mkdir(parents=True)
            (destination/'picture.xsh').write_bytes(b'invented portrait')
            return {'source':{'format':'fixture','picture':{'path':'picture.xsh','sha256':hashlib.sha256(b'invented portrait').hexdigest()}}}
        return {'ok':True,'native_compilation':True}
    monkeypatch.setattr(fighter_mod,'contract',contract)
    destination=tmp_path/'fighter.zip';fighter_mod.export_mod(document,destination,runtime,data,tmp_path/'work')
    prefix=document['identity']['pack']+'/'
    with zipfile.ZipFile(destination) as archive:
        manifest=json.loads(archive.read(prefix+'fighters.json'));raw=archive.read(prefix+'fighter.json');recipe=json.loads(raw)
        assert len(manifest['fighters'])==1 and len(manifest['resources'])==4
        assert manifest['resources'][0]['source']['format']=='caf-fighter-3'
        assert manifest['resources'][0]['source']['selection']['sha256']==hashlib.sha256(raw).hexdigest()
        assert len(recipe['outfits'])==2 and len(set(recipe['portraits'].values()))==3
        assert 'stats' not in recipe['outfits'][0] and 'finishers' not in recipe['outfits'][0]
        for index,outfit in enumerate([recipe,*recipe['outfits']]):
            descriptor=outfit['atlases']['a'];raw=archive.read(prefix+descriptor['path'])
            assert raw==png(color=(index,20,30,255)) and hashlib.sha256(raw).hexdigest()==descriptor['sha256']


def test_upgrade_copies_outfit_assets_with_one_shared_identity_and_combat():
    original = source(); saved = projects.encoded(original)
    document, second = outfits.add(original)
    document = outfits.rename(document, 'default', 'Shirtless')
    document = outfits.rename(document, second, 'Red jersey')
    document, third = outfits.add(document, second)
    assert projects.validate(document) is document
    assert document['schema'] == projects.SCHEMA3 and document['identity'] == original['identity']
    assert projects.encoded(original) == saved and len(outfits.entries(document)) == 3
    assert outfits.view(document, third)['textures'] == original['textures']
    assert 'stats' not in document['outfits'][0] and 'styles' not in document['outfits'][0]
    with pytest.raises(SaveError, match='three outfits'):
        outfits.add(document)


@pytest.mark.parametrize('damage', [
    lambda d: d['outfits'][0].update(id='default'),
    lambda d: d['outfits'][0].update(id='../escape'),
    lambda d: d['outfits'][0].update(name=''),
    lambda d: d['outfits'][0].update(stats={}),
    lambda d: d['outfits'][0]['caf_values'].__setitem__(0, 99),
    lambda d: d['outfits'][0]['caf_colors'].__setitem__(0, 3),
    lambda d: d.update(schema=projects.SCHEMA2),
])
def test_malformed_or_stale_outfits_are_refused(damage):
    document, _ = outfits.add(source()); damage(document)
    with pytest.raises(SaveError):
        projects.validate(document)


def editor(tmp_path):
    path = tmp_path / 'fighter.ffnyfighter'; projects.write(path, source())
    e = Editor(tmp_path); e.open_project(path)
    return e, path


def test_switching_is_view_only_and_all_staged_outfits_survive_save_copy_reopen(tmp_path):
    e, path = editor(tmp_path); e.request('outfit_add', {}); second = e.active_outfit
    e.request('outfit_rename', {'name': 'Jersey'})
    e.request('project_atlas', {'slot': 'a', 'png': __import__('base64').b64encode(png(color=(10, 20, 30, 7))).decode()})
    e.stage({'stats': {'health': 42}})
    e.request('outfit_select', {'id': 'default'})
    assert e.snapshot()['fields']['stats']['health'] == 42
    assert e.snapshot()['dirty']
    assert projects.read(path)[0]['schema'] == projects.SCHEMA2
    e.request('save', {})
    document = projects.read(path)[0]
    assert document['fighter']['stats']['health'] == 42
    assert outfits.view(document, second)['textures'] != outfits.view(document, 'default')['textures']
    e.request('outfit_select', {'id': second})
    assert not e.snapshot()['dirty']
    e.request('export', {'path': str(tmp_path / 'copy.ffnyfighter')})
    e.open_project(tmp_path / 'copy.ffnyfighter')
    assert e.project == document and len(e.snapshot()['outfits']) == 2
    e.create_project(tmp_path / 'variant.ffnyfighter')
    assert e.project['outfits'] == document['outfits'] and e.project['identity'] != document['identity']


def test_undo_and_reset_restore_outfit_collection_active_view_and_assets(tmp_path):
    e, _ = editor(tmp_path); e.request('outfit_add', {}); second = e.active_outfit
    e.request('outfit_rename', {'name': 'Tank'})
    e.request('outfit_select', {'id': 'default'})
    e.request('undo', {})
    assert e.active_outfit == second and e.snapshot()['outfits'][1]['name'] == 'Outfit 2'
    e.request('project_atlas_clear', {}); assert not e.snapshot()['atlas_slots']
    e.request('undo', {}); assert e.snapshot()['atlas_slots'] == ['a']
    e.request('reset', {})
    assert not e.snapshot()['dirty'] and e.active_outfit == 'default' and len(e.snapshot()['outfits']) == 1


def test_stale_outfit_can_be_switched_back_to_and_cleared_without_losing_other_art(tmp_path):
    e, _ = editor(tmp_path); e.request('outfit_add', {}); second = e.active_outfit
    values = e.snapshot()['fields']['caf_values'][:]; values[0] = 4
    e.stage({'caf_values': values})
    e.request('outfit_select', {'id': 'default'})
    e.request('outfit_select', {'id': second})
    assert e.snapshot()['fields']['caf_values'][0] == 4
    with pytest.raises(SaveError, match='Appearance changed'):
        e.request('save', {})
    e.request('project_atlas_clear', {}); e.request('save', {})
    assert 'a' in e.project['textures']['atlases'] and not e.project['outfits'][0]['textures']['atlases']


def test_remove_is_staged_and_first_outfit_is_retained(tmp_path):
    e, _ = editor(tmp_path)
    with pytest.raises(SaveError, match='first outfit'):
        e.request('outfit_remove', {})
    assert not e.snapshot()['dirty']
    e.request('outfit_add', {}); second = e.active_outfit; e.request('save', {})
    e.request('outfit_remove', {})
    assert len(e.snapshot()['outfits']) == 1 and e.active_outfit == 'default' and e.snapshot()['dirty']
    e.request('undo', {})
    assert e.active_outfit == second and len(e.snapshot()['outfits']) == 2 and not e.snapshot()['dirty']
