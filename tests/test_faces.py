from types import SimpleNamespace
import pytest
from defjam_caf import faces
from defjam_caf.container import SaveError


def cache():
    resources={};objects={'v2cp_532_0004_c':{}}
    for _,_,slot,prefix in faces.FIELDS:
        if prefix is None:continue
        for value in range(1,9):
            if slot in (7,8) or value>1 and (slot!=11 or value%2):
                resources[f'v2cp_{prefix}_{value:04}_a01_01']={'palettes':[f'pl{i:02}' for i in range(1,37)]}
            if slot not in (7,8) and value>1:objects[f'v2cp_{prefix}_{value:04}_c']={}
    resources['v2cp_551_9999_a01_01']={'images':{}}
    return SimpleNamespace(catalog={'resources':resources,'objects':objects})


def fields():return {'caf_values':[1]*38,'caf_colors':[0]*38}


def test_face_catalog_uses_available_original_parts_and_excludes_internal_resources():
    source=cache();choices=faces.catalog(source)
    assert len(choices)==8 and all(len(row['options'])==8 for row in choices[:-1])
    assert len(choices[-1]['options'])==36
    assert all(item['value']!=9999 for row in choices for item in row['options'])
    source.catalog['objects'].pop('v2cp_561_0008_c')
    nose=next(row for row in faces.catalog(source) if row['id']=='nose')
    assert {item['value'] for item in nose['options']}==set(range(1,8))


def test_changes_touch_only_explicit_facial_fields_and_preserve_unknown_values():
    original=fields();original['caf_values'][6]=900;original['caf_values'][17]=0xdeadbeef
    choices=faces.catalog(cache());before=(original['caf_values'][:],original['caf_colors'][:])
    values,colors=faces.change(original,{'face':8,'nose':7,'brow_color':35},choices)
    assert [(i,a,b) for i,(a,b) in enumerate(zip(before[0],values)) if a!=b]==[(5,1,8),(9,1,7)]
    assert [(i,a,b) for i,(a,b) in enumerate(zip(before[1],colors)) if a!=b]==[(8,0,35)]
    assert values[6]==900 and values[17]==0xdeadbeef and original['caf_values']==before[0]
    assert faces.selected(original,choices)[1]['value']==900


@pytest.mark.parametrize('value',[0,9,9999,True,1.5,'2'])
def test_unsupported_preset_is_refused_without_mutation(value):
    original=fields();before=repr(original)
    with pytest.raises(SaveError):faces.change(original,{'nose':value},faces.catalog(cache()))
    assert repr(original)==before


def test_ear_alias_preserves_the_users_selected_native_ordinal():
    original=fields();values,_=faces.change(original,{'ears':4},faces.catalog(cache()))
    assert values[11]==4
