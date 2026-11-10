import json
import hashlib
import zipfile
import pytest
from types import SimpleNamespace
from defjam_caf import projects,outfits,face_geometry as fg,fighter_mod
from test_face_geometry import reference
from test_projects import fields


@pytest.mark.parametrize('retail',[False,True])
def test_sculpt_export_declares_version_and_preserves_per_outfit_assets(tmp_path,monkeypatch,retail):
    runtime=tmp_path/'runtime';(runtime/'setup').mkdir(parents=True);(runtime/'scripts').mkdir()
    (runtime/'setup/fighter_caf.py').touch();(runtime/'scripts/fighter-contract.py').touch()
    data=tmp_path/'data';(data/'extracted').mkdir(parents=True)
    project=projects.from_fields(fields()[0],'Example')
    ref=reference();project.update(schema=projects.SCHEMA5,face_sculpt=fg.sliders(ref,{'face_width':.5}))
    project,second=outfits.add(project)
    project['outfits'][0]['face_sculpt']=fg.empty(ref)
    if retail:
        project['schema']=projects.SCHEMA6;project['fighter']['retail_moveset']='retail/blaze'
    from defjam_caf import appearance
    monkeypatch.setattr(appearance,'Appearance',lambda cache:SimpleNamespace())
    monkeypatch.setattr(fg,'template',lambda *a:ref)
    monkeypatch.setattr(fighter_mod,'contract',lambda *a,**k:dict(ok=True,native_compilation=True))
    path=tmp_path/'export.zip';fighter_mod.export_mod(project,path,runtime,data,tmp_path/'exports',asset_cache=object())
    prefix=project['identity']['pack']+'/'
    with zipfile.ZipFile(path) as archive:
        manifest=json.loads(archive.read(prefix+'fighters.json'))
        assert manifest['resources'][0]['source']['format']==('caf-fighter-5' if retail else 'caf-fighter-4')
        recipe=json.loads(archive.read(prefix+'fighter.json'))
        assert recipe.get('retail_moveset')==('retail/blaze' if retail else None)
        nodes=[recipe,*recipe['outfits']]
        for view,node in zip([outfits.view(project),outfits.view(project,second)],nodes):
            descriptor=node['face'];raw=archive.read(prefix+descriptor['path'])
            assert hashlib.sha256(raw).hexdigest()==descriptor['sha256']
            value=json.loads(raw);assert value['schema']=='caf-face-coordinates-1'
            assert value['meshes'][0]['positions']==ref['meshes'][0]['positions']
            assert value['meshes'][0]['deltas']==view['face_sculpt']['meshes'][0]['deltas']
