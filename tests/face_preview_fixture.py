"""Invented bind-space points; parity oracle is the actual export generator."""
import json
from defjam_caf import face_geometry as fg

points=[[x,y,z] for x in (-1.,-.5,0.,.5,1.) for y in (19.,19.4,20.,20.6,21.) for z in (0.,1.,2.)]
meshes=[dict(rm=0,positions=points,uvs=[[0.,0.] for _ in points],indices=[0,1,2])]
ref=dict(schema='ffny-face-template-1',basis=[0,1,1,1,1,1],meshes=meshes)
ref['sha256']=fg.digest(ref)
cases=[{}, {key:1 for key,_ in fg.CONTROLS}, {key:-1 for key,_ in fg.CONTROLS},
       dict(face_width=.73,nose_projection=-.49,eye_size=.22,brow_height=.16,jaw_width=-.64)]
print(json.dumps(dict(basis=fg.preview_basis(ref),cases=[dict(values=v,expected=fg.apply(dict(meshes=meshes),fg.sliders(ref,v))['meshes']) for v in cases])))
