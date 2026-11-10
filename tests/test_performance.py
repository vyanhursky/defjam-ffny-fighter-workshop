import base64
import copy
import io
import wave

import pytest
from defjam_caf import performance, projects, outfits
from defjam_caf.container import SaveError
from defjam_caf.editor import Editor
from test_projects import fields


def wav(channels=1):
    result=io.BytesIO()
    with wave.open(result,'wb') as stream:
        stream.setnchannels(channels);stream.setsampwidth(2);stream.setframerate(24000)
        stream.writeframes(b'\0\0'*(240*channels))
    return result.getvalue()


def settings():
    return dict(voice=dict(preset='retail/pockets',banks={},clips={}),intro='CI_113A',victory='CE_014A',
        ai=dict(preset='char0005',tendencies={level:[{} for _ in range(4)] for level in performance.DIFFICULTIES}))


def test_embedded_audio_round_trip_and_snapshot_redaction(tmp_path):
    value=performance.set_clip(settings(),'Character:0',wav())
    p=projects.from_fields(fields()[0],'Example');p['schema']=projects.SCHEMA7;p['performance']=value
    path=tmp_path/'test.ffnyfighter';projects.write(path,p)
    e=Editor(tmp_path/'work');e.open_project(path)
    assert e.snapshot()['performance']['settings']['voice']['clips']['Character:0']['samples']==240
    assert 'performance' not in e.snapshot()['project']
    assert projects.read(path)[0]['performance']==value
    assert performance.audio_bytes(value['voice']['clips']['Character:0'])==wav()


def test_shared_outfit_history_and_source_save_separation(tmp_path):
    p=projects.from_fields(fields()[0],'Example');p['schema']=projects.SCHEMA7;p['performance']=settings()
    p,second=outfits.add(p);path=tmp_path/'test.ffnyfighter';projects.write(path,p)
    e=Editor(tmp_path/'work');e.open_project(path);saved=path.read_bytes()
    e.request('performance_clear',dict(section='intro'))
    assert any('Entrance sequence' in s for s in e.changes())
    assert 'intro' not in e.project_document()['performance']
    e.request('outfit_select',dict(id=second));assert 'intro' not in e.project_document()['performance']
    e.request('undo',{});assert e.project_document()['performance']['intro']=='CI_113A'
    assert path.read_bytes()==saved
    original=projects.container(p).payload
    altered=copy.deepcopy(p);altered['performance']['intro']='CI_1000'
    assert projects.container(altered).payload==original


@pytest.mark.parametrize('change',[
    lambda s:s['ai']['tendencies']['hard'][0].update(Weapon_Frequency=6),
    lambda s:s['ai']['tendencies']['hard'][0].update(Weapon_Frequency=True),
    lambda s:s['voice']['banks'].update(Character=True),
    lambda s:s['voice']['clips'].update({'Character:255':base64.b64encode(wav()).decode()}),
    lambda s:s.update(intro='../bad'),lambda s:s.update(runtime='private-path'),
    lambda s:s['voice']['clips'].update({'intro':base64.b64encode(wav(2)).decode()}),
])
def test_refuses_unknown_fields_ranges_and_audio(change):
    s=settings();change(s)
    with pytest.raises(SaveError):performance.validate(s)


def test_old_schema_cannot_smuggle_performance():
    p=projects.from_fields(fields()[0],'Example');p['performance']=settings()
    with pytest.raises(SaveError):projects.validate(p)


def test_story_edit_is_refused_before_any_mutation(tmp_path):
    e=Editor(tmp_path)
    for action in ('performance_set','performance_clip','performance_clear'):
        with pytest.raises(SaveError,match='standalone'):e.request(action,{})
    assert e.history==[] and e.edits=={}
