import copy
import struct
from types import SimpleNamespace
import pytest
from defjam_caf import projects,outfits,movesets
from defjam_caf.container import SaveError
from defjam_caf.fields import apply_fields,read_fields
from defjam_caf.editor import Editor
from test_projects import fields
from test_editing import profile


def test_original_catalog_deduplicates_costumes_and_preserves_stable_motion_identity():
    words={12:123};strings={};records=[]
    for i,(symbol,label,core,mask,primary) in enumerate([
            ('Example_Alt','Example alternate',5,8,8),('Example','Example',5,8,8),
            ('Four_Styles','Four styles',6,23,16),('Hero','Created fighter',141,1,1)]):
        offset=100+i*100;records.append((i,(offset,)))
        words.update({offset:1000+i*2,offset+20:1001+i*2,offset+40:core,offset+36:mask,offset+72:primary})
        strings[1000+i*2]=symbol;strings[1001+i*2]=label
    schema={movesets.CORE:(10,2),movesets.TABLE^movesets.name_hash('DisplayName'):(5,1),
            movesets.TABLE^movesets.name_hash('FightingStyle'):(9,6)}
    shop=SimpleNamespace(word=lambda p:words[p],string=lambda p:strings[p],mapping=lambda *a:schema)
    c=movesets.Catalog(SimpleNamespace(shop=shop,records=lambda table:records))
    assert len(c.options)==2 and c.select('retail/example')['core']==5
    assert c.by_core[6]['styles']==[2,1,0,4]
    assert 141 not in c.by_core
    with pytest.raises(SaveError):c.select('retail/example-alt')
    schema[movesets.CORE]=(9,2)
    with pytest.raises(SaveError,match='schema'):movesets.Catalog(SimpleNamespace(shop=shop))


def catalog():
    return SimpleNamespace(options=[dict(key='retail/blaze',label='Blaze',core=5,styles=[3]),dict(key='retail/d-mob',label='D-Mob',core=51,styles=[2,3])],
        by_core={5:dict(key='retail/blaze',label='Blaze',core=5),51:dict(key='retail/d-mob',label='D-Mob',core=51)})


def editor(tmp_path):
    p=projects.from_fields(fields()[0],'Example');path=tmp_path/'source.ffnyfighter';projects.write(path,p)
    e=Editor(tmp_path/'work');e.open_project(path);e.movesets=catalog()
    e.movesets.by_key={row['key']:row for row in e.movesets.options}
    e.movesets.select=lambda key:e.movesets.by_key[key]
    return e,path


def test_project_moveset_is_shared_and_history_save_reopen_preserve_caf_fallback(tmp_path):
    e,path=editor(tmp_path);original=copy.deepcopy(e.project);e.request('outfit_add',{})
    second=e.active_outfit
    e.request('fighting_style',dict(mode='retail',fighter='retail/d-mob'))
    doc=e.project_document();assert doc['schema']==projects.SCHEMA
    assert doc['fighter']['retail_moveset']=='retail/d-mob' and doc['fighter']['styles']==original['fighter']['styles']
    e.request('outfit_select',{'id':'default'});assert e.snapshot()['retail_movesets']['selected']=='retail/d-mob'
    e.request('save',{});e.open_project(path)
    assert e.snapshot()['retail_movesets']['selected']=='retail/d-mob'
    e.request('fighting_style',dict(mode='caf',styles=[1,4]))
    assert 'retail_moveset' not in e.project_document()['fighter']
    e.request('undo',{});assert e.project_document()['fighter']['retail_moveset']=='retail/d-mob'
    e.request('reset',{});assert len(e.snapshot()['outfits'])==2


def test_profile_moveset_edits_only_battle_core_and_save_reopen_preserves_career(profile,tmp_path):
    e,_=editor(tmp_path);e.data=profile.path.parents[4];e.select_profile(profile.name)
    original=e.profile.path.read_bytes();payload=e.profile.container.payload
    e.request('fighting_style',dict(mode='retail',fighter='retail/blaze'))
    assert e.current().payload[:0x137]==payload[:0x137]
    assert e.current().payload[0x138:]==payload[0x138:]
    assert e.current().payload[0x137]==5 and e.profile.path.read_bytes()==original
    e.request('undo',{});assert e.current().payload==payload
    e.request('fighting_style',dict(mode='retail',fighter='retail/d-mob'))
    # The save is refused until the player acknowledges what a retail core in a real save means.
    assert e.snapshot()['retail_moveset_save'] and any('retail-moveset support' in c for c in e.snapshot()['changes'])
    with pytest.raises(SaveError,match='Story save'):e.request('save',{})
    with pytest.raises(SaveError,match='Story save'):e.request('save',{'acknowledge_retail_moveset':'yes'})
    assert e.profile.path.read_bytes()==original and not list((tmp_path/'work').glob('backups/*'))
    e.request('save',{'acknowledge_retail_moveset':True});e.select_profile(profile.name)
    assert e.current().payload[0x137]==51 and e.snapshot()['retail_movesets']['selected']=='retail/d-mob'
    e.request('fighting_style',dict(mode='retail',fighter='retail/blaze'))
    e.request('fighting_style',dict(mode='caf',styles=[1,4]))
    assert e.current().payload[0x137]>86 and e.current().payload[0x4d87]==payload[0x4d87]
    assert 'moveset_core' not in e.edits


@pytest.mark.parametrize('core',[0,87,True,'5',-1])
def test_invalid_profile_retail_core_is_refused(core):
    with pytest.raises(SaveError):apply_fields(projects.empty_container(),{'moveset_core':core})


def test_project6_keeps_art_sculpt_finishers_and_rejects_unversioned_or_bad_mode():
    from test_face_geometry import reference
    from defjam_caf import face_geometry as fg,ui_art
    p=projects.from_fields(fields()[0],'Example');p.update(face_sculpt=fg.empty(reference()))
    p['fighter']['retail_moveset']='retail/blaze';p['fighter']['finishers']=['00000001']*4
    assert projects.validate(p)
    assert projects.validate(ui_art.upgrade(p))['schema']==projects.SCHEMA
    p,second=outfits.add(p);assert outfits.view(p,second)['fighter']['retail_moveset']=='retail/blaze'
    for bad in ('bad','retail/../../x',5):
        q=copy.deepcopy(p);q['fighter']['retail_moveset']=bad
        with pytest.raises(SaveError):projects.validate(q)
    q=copy.deepcopy(p);q['schema']='ffny-fighter-project-8'  # a version this build does not know
    with pytest.raises(SaveError):projects.validate(q)


def test_a_save_that_does_not_add_a_retail_moveset_needs_no_acknowledgement(profile,tmp_path):
    e,_=editor(tmp_path);e.data=profile.path.parents[4];e.select_profile(profile.name)
    e.request('fighting_style',dict(mode='caf',styles=[1,4]))
    assert e.snapshot()['retail_moveset_save'] is None
    e.request('save',{})
    # A profile that already holds a retail core can be saved again for another reason without a new warning.
    e.request('fighting_style',dict(mode='retail',fighter='retail/blaze'));e.request('save',{'acknowledge_retail_moveset':True})
    assert e.snapshot()['retail_moveset_save'] is None
