// Preview-only posing from original bind-joint pivots. These are smooth
// analytical arm weights, not a decoder for the game's skinning or shop clips.
const armSlots = new Set(['12','16','17','18','23','24','28']);
const presets = {wardrobe: [75, 12], relaxed: [45, 7], tpose: [0, 0]};
const smooth = (lo, hi, x) => {const t=Math.max(0,Math.min(1,(x-lo)/(hi-lo)));return t*t*(3-2*t);};
const mix = (a,b,w) => a.map((v,i)=>v+(b[i]-v)*w);
function turn(v, origin, axis, angle){
  const p=v.map((x,i)=>x-origin[i]),c=Math.cos(angle),s=Math.sin(angle);
  const q=axis==='z'?[p[0]*c-p[1]*s,p[0]*s+p[1]*c,p[2]]:[p[0]*c+p[2]*s,p[1],-p[0]*s+p[2]*c];
  return q.map((x,i)=>x+origin[i]);
}
export function poseMesh(part, pose, pivots){
  if(!Object.hasOwn(presets,pose))throw new Error('Unknown preview pose');
  if(pose==='tpose'||!armSlots.has(String(part.slot)))return {positions:part.positions,normals:part.normals};
  const [upper,bend]=presets[pose].map(x=>x*Math.PI/180),positions=[],normals=[];
  for(let i=0;i<part.positions.length;i++){
    const p=part.positions[i],n=part.normals[i],side=p[0]>=0?1:-1;
    const shoulder=pivots[side>0?'L_arm1':'R_arm1'],elbow=pivots[side>0?'L_arm2':'R_arm2'];
    const w=smooth(Math.abs(shoulder[0])*.60,Math.abs(shoulder[0])*1.18,Math.abs(p[0]))*
            smooth(shoulder[1]-3,shoulder[1]-1,p[1]);
    const flex=smooth(Math.abs(elbow[0])-.35,Math.abs(elbow[0])+.35,Math.abs(p[0]));
    const q=turn(turn(p,elbow,'y',-side*bend*flex),shoulder,'z',-side*upper);
    const normal=turn(turn(n,[0,0,0],'y',-side*bend*flex),[0,0,0],'z',-side*upper);
    positions.push(mix(p,q,w));
    const blended=mix(n,normal,w),length=Math.hypot(...blended)||1;
    normals.push(blended.map(v=>v/length));
  }
  return {positions,normals};
}
