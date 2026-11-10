// Position-only audition. The original head and each unit control delta come
// from the same Python generator used by Apply/export, never from the last drag.
export function blendFace(mesh, values){
  const active=Object.entries(values).filter(([,value])=>value!==0);
  for(const [key,value] of active){
    if(!Number.isFinite(value)||value < -1||value > 1||!mesh.controls[key])throw new Error('Invalid face preview control');
  }
  return mesh.positions.map((point,i)=>point.map((value,axis)=>
    active.reduce((result,[key,weight])=>result+mesh.controls[key][i][axis]*weight,value)));
}

export function faceDraft(controls, committed, values){
  const result=Object.fromEntries(controls.map(({id})=>[id,Number(values[id]??0)]));
  return controls.some(({id})=>result[id]!==Number(committed[id]??0))?result:null;
}
