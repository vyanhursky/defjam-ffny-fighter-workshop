import copy
from types import SimpleNamespace

import pytest

from defjam_caf import face_geometry as fg, projects, outfits, ui_art
from defjam_caf.container import SaveError
from defjam_caf.editor import Editor
from test_projects import fields


def reference():
    meshes = [dict(rm=0, positions=[[-1.,0.,0.],[1.,1.,0.],[0.,2.,1.]],
                   uvs=[[0.,0.],[1.,0.],[.5,1.]],indices=[0,1,2])]
    value = dict(schema='ffny-face-template-1',basis=[2,1,1,1,1,1],meshes=meshes)
    return dict(value,sha256=fg.digest(value))


def test_obj_round_trip_and_exact_coordinate_sculpt_without_changing_topology():
    ref=reference();raw=fg.obj(ref)
    sculpt=fg.import_obj(raw,ref)
    assert sculpt==fg.empty(ref)
    modified=raw.replace(b'v 1 1 0',b'v 1.2 1 0')
    imported=fg.import_obj(modified,ref)
    assert imported['meshes'][0]['deltas'][1]==pytest.approx([.2,0,0])
    assert fg.import_obj(fg.obj(ref,imported),ref)['meshes'][0]['deltas'][1]==pytest.approx([.2,0,0])


@pytest.mark.parametrize('before,after',[
    (b'f 1/1 2/2 3/3',b'f 1/1 3/3 2/2'),
    (b'vt 0 0',b'vt 0.1 0'), (b'v 1 1 0',b'v nan 1 0'),
    (b'v 1 1 0',b'v 2 1 0'), (b'v -1 0 0',b'v -0.9 0 0'),
    (b'f 1/1 2/2 3/3',b'f -1/1 2/2 3/3'),
    (b'v 1 1 0',b'v 1 1'),
])
def test_invalid_mesh_leaves_original_template_unchanged(before,after):
    ref=reference();original=copy.deepcopy(ref)
    with pytest.raises(SaveError):fg.import_obj(fg.obj(ref).replace(before,after),ref)
    assert ref==original


def test_sliders_are_absolute_bounded_and_preserve_neck():
    ref=reference();a=fg.sliders(ref,{'face_width':1,'nose_projection':.5})
    assert fg.sliders(ref,a['sliders'])==a
    assert a['meshes'][0]['deltas'][0]==[0,0,0]
    assert any(any(p) for p in a['meshes'][0]['deltas'])
    for values in ({'face_width':2},{'unknown':0},{'eye_size':float('nan')},{'ear_size':True}):
        with pytest.raises(SaveError):fg.sliders(ref,values)


def test_project_v5_preserves_sculpt_across_outfits_art_and_roundtrip(tmp_path):
    project=projects.from_fields(fields()[0],'Example')
    project.update(schema=projects.SCHEMA5,face_sculpt=fg.empty(reference()))
    path=tmp_path/'face.ffnyfighter';projects.write(path,project)
    loaded=projects.read(path)[0];assert loaded==project
    assert ui_art.upgrade(project)['schema']==projects.SCHEMA5
    combined,second=outfits.add(project)
    assert outfits.view(combined,second)['face_sculpt']==project['face_sculpt']
    selected=outfits.view(combined,second);selected.pop('face_sculpt')
    changed=outfits.replace_view(combined,second,selected)
    assert 'face_sculpt' not in outfits.view(changed,second)
    assert changed['face_sculpt']==project['face_sculpt']
    assert projects.validate(changed)
    wrong=copy.deepcopy(project);wrong['fighter']['caf_values'][9]=2
    with pytest.raises(SaveError,match='presets changed'):projects.validate(wrong)


def test_editor_import_save_undo_reset_and_bad_import_preserve_project(tmp_path,monkeypatch):
    ref=reference();project=projects.from_fields(fields()[0],'Example')
    path=tmp_path/'face.ffnyfighter';projects.write(path,project)
    editor=Editor(tmp_path/'work');editor.open_project(path)
    editor.appearance=SimpleNamespace();editor.cache=SimpleNamespace()
    # Snapshot availability comes from real cache in desktop acceptance; isolate
    # staging/persistence here without mirroring a game asset corpus.
    monkeypatch.setattr(editor,'snapshot',lambda:{'dirty':editor.project_document(False)!=editor.project})
    monkeypatch.setattr(fg,'template',lambda *args:ref)
    obj=tmp_path/'sculpt.obj';obj.write_bytes(fg.obj(ref).replace(b'v 1 1 0',b'v 1.2 1 0'))
    editor.request('face_import',{'path':str(obj)})
    assert 'face_sculpt' in editor.project_document() and path.read_bytes()==projects.encoded(project)
    editor.request('undo',{});assert 'face_sculpt' not in editor.project_document()
    editor.request('face_import',{'path':str(obj)})
    before=editor.project_document();obj.write_bytes(b'v nan 0 0')
    with pytest.raises(SaveError):editor.request('face_import',{'path':str(obj)})
    assert editor.project_document()==before
    editor.request('save',{});editor.open_project(path)
    assert editor.project_document()==before
    editor.request('face_clear',{});assert 'face_sculpt' not in editor.project_document()
    editor.request('reset',{});assert editor.project_document()==before
    with pytest.raises(SaveError,match='Clear the imported sculpt'):editor.request('face_sliders',{'values':{'face_width':.5}})


def test_profile_cannot_store_arbitrary_geometry(tmp_path):
    editor=Editor(tmp_path)
    for action in ('face_import','face_export','face_sliders','face_clear'):
        with pytest.raises(SaveError,match='standalone'):editor.request(action,{})
