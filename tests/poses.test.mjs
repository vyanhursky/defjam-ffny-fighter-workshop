import {test} from 'node:test';
import assert from 'node:assert/strict';
import {poseMesh} from '../src/defjam_caf/resources/poses.mjs';

const pivots={L_arm1:[2,17,0],L_arm2:[5,17,0],R_arm1:[-2,17,0],R_arm2:[-5,17,0]};
const mesh={slot:'12',positions:[[8,17,0],[-8,17,0],[0,14,0],[1,12,0]],normals:[[0,1,0],[0,1,0],[0,1,0],[0,1,0]]};
test('T-pose reproduces the exact source; switching poses does not mutate it',()=>{
 const original=structuredClone(mesh);poseMesh(mesh,'wardrobe',pivots);
 assert.deepEqual(mesh,original);assert.deepEqual(poseMesh(mesh,'tpose',pivots),{positions:mesh.positions,normals:mesh.normals});
});
test('both arms lower symmetrically while the torso and lower body stay fixed',()=>{
 const result=poseMesh(mesh,'wardrobe',pivots);
 assert.ok(result.positions[0][1]<mesh.positions[0][1]-4);
 assert.ok(Math.abs(result.positions[0][0]+result.positions[1][0])<1e-8);
 assert.ok(Math.abs(result.positions[0][1]-result.positions[1][1])<1e-8);
 assert.deepEqual(result.positions.slice(2),mesh.positions.slice(2));
 for(const normal of result.normals)assert.ok(Math.abs(Math.hypot(...normal)-1)<1e-8);
});
test('accessories and skin at the same coordinate remain attached',()=>{
 const skin=poseMesh(mesh,'relaxed',pivots);
 for(const slot of ['16','17','18','23','24','28'])assert.deepEqual(poseMesh({...mesh,slot},'relaxed',pivots),skin);
 assert.deepEqual(poseMesh({...mesh,slot:'13'},'wardrobe',pivots).positions,mesh.positions);
});
test('wardrobe-inspired and relaxed presets produce different silhouettes',()=>{
 assert.ok(poseMesh(mesh,'wardrobe',pivots).positions[0][0]<poseMesh(mesh,'relaxed',pivots).positions[0][0]);
 assert.throws(()=>poseMesh(mesh,'unverified-retail-clip',pivots));
});
