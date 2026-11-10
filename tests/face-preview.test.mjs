import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {blendFace,faceDraft} from '../src/defjam_caf/resources/face-preview.mjs';

test('live blending matches Python Apply/export, including mixed controls and extremes',()=>{
  const root=fileURLToPath(new URL('../',import.meta.url));
  const run=spawnSync(process.platform==='win32'?'python':'python3',['tests/face_preview_fixture.py'],{cwd:root,env:{...process.env,PYTHONPATH:root+'src'},encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);
  const fixture=JSON.parse(run.stdout);
  for(const {values,expected} of fixture.cases){
    for(let m=0;m<fixture.basis.meshes.length;m++){
      const result=blendFace(fixture.basis.meshes[m],values);
      for(let i=0;i<result.length;i++)for(let axis=0;axis<3;axis++)assert.ok(Math.abs(result[i][axis]-expected[m].positions[i][axis])<1e-12);
    }
  }
});

test('rapid alternating drags and a return to zero never accumulate deformation',()=>{
  const mesh={positions:[[0,1,2]],controls:{width:[[.5,0,0]]}},original=structuredClone(mesh);
  for(const value of [1,-1,.73,-.15,0])assert.deepEqual(blendFace(mesh,{width:value}),[[value*.5,1,2]]);
  assert.deepEqual(mesh,original);
  for(const value of [NaN,Infinity,1.01])assert.throws(()=>blendFace(mesh,{width:value}));
});

test('draft values remain separate from committed values and clear at the baseline',()=>{
  const controls=[{id:'width'},{id:'nose'}],committed={width:.3,nose:-.2};
  assert.deepEqual(faceDraft(controls,committed,{width:.7,nose:-.2}),{width:.7,nose:-.2});
  assert.equal(faceDraft(controls,committed,{width:.3,nose:-.2}),null);
  assert.deepEqual(committed,{width:.3,nose:-.2});
});
