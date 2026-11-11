import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {poseMesh} from './poses.mjs';
import {blendFace,faceDraft as makeFaceDraft} from './face-preview.mjs';
import {performanceEditor} from './performance.mjs';

const $ = id => document.getElementById(id);
$('retail-editor').onclick=()=>call('open_retail_editor');
let bridge, current=null, serial=0, busyCount=0, options=[], selectionKey=null, previewEpoch=0;
let auditionKey=null, categoryEpoch=0, previewTimer=null, sceneData=null, atlasTextures=[];
let faceDraft=null,faceFrame=null,faceSceneEpoch=-1;
const pending=new Map();
function toast(message,error=false){$('toast').textContent=message;$('toast').classList.toggle('error',error);$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,error?12000:6500);}
function call(action,args={},label=null){
  const id=String(++serial);
  if(label){busyCount++;$('busy-label').textContent=label;$('busy').hidden=false;}
  return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject,label});bridge.dispatch(JSON.stringify({id,action,args}));});
}
function fail(error){toast(error.message||String(error),true);$('status-message').textContent='Operation could not be completed';}
async function act(action,args={},label=null){try{const result=await call(action,args,label);if(result?.snapshot)renderState(result.snapshot);else if(result?.profiles)renderState(result);if(result?.message){toast(result.message);$('status-message').textContent=result.message;}return result;}catch(e){fail(e);return null;}}
function makeOptions(select,items,value){select.replaceChildren(...items.map(x=>new Option(x.label,String(x.value))));if(value!==undefined)select.value=String(value);select.disabled=!items.length;}
function discard(){return !current?.dirty||confirm('Discard unsaved changes to this fighter?');}
function projectDetails(){const metadata={};for(const key of ['name','author','version','description','license','donor'])metadata[key]=$('project-'+key).value;return {metadata,identity:{pack:$('project-pack').value,fighter:$('project-fighter').value}};}
function readyFighter(){return Boolean(current?.fields?.has_fighter);}
function renderState(state){
  faceDraft=null;if(faceFrame!==null)cancelAnimationFrame(faceFrame);faceFrame=null;
  window.__cafFacePreview=null;
  auditionKey=null;
  current=state;window.__cafState=state;
  $('data-path').textContent=state.data||'Choose your Recomp data directory to begin';
  $('fighter-name').textContent=state.selected||'YOUR FIGHTER';
  $('fighter-subtitle').textContent=state.project?'STANDALONE FIGHTER PROJECT · NO STORY PROGRESS':state.fields?(state.fields.has_fighter?'YOUR STORY FIGHTER · ORIGINAL GAME ASSETS':'NO STORY FIGHTER · CREATE ONE IN THE GAME'):'Open a profile to get started';
  $('save-status').textContent=state.dirty?'● Unsaved changes':state.project?'● Saved project':state.selected?'● Saved profile':'No fighter loaded';$('save-status').classList.toggle('dirty',state.dirty);
  $('profiles').replaceChildren();
  for(const p of state.profiles){const b=document.createElement('button');b.className='profile-card'+(!state.project&&p.name===state.selected?' selected':'');const mon=document.createElement('span');mon.className='profile-monogram';mon.textContent=p.name.slice(0,2);const text=document.createElement('span'),name=document.createElement('strong'),sub=document.createElement('small');name.textContent=p.name;sub.textContent=p.has_fighter?'Story fighter':'No Story fighter';text.append(name,sub);b.append(mon,text);b.onclick=()=>{if(discard())act('select_profile',{name:p.name},'Loading profile…');};$('profiles').append(b);}
  $('profile-note').textContent=state.issues.length?`${state.issues.length} save folder(s) could not be loaded. ${state.issues.map(x=>x.error).join('; ')}`:state.data?`${state.profiles.length} profiles found. Your global Options are kept separate.`:'Profiles are discovered from your local save data.';
  $('save').disabled=!state.dirty;$('undo').disabled=!state.undo;$('reset').disabled=!state.dirty;
  for(const id of ['export','duplicate'])$(id).disabled=!state.selected||Boolean(state.project);$('save').textContent=state.project?'Save project':'Save changes';
  $('import').disabled=!state.data;
  $('changes').replaceChildren(...(state.changes.length?state.changes:['No changes yet.']).map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));
  $('status-message').textContent=state.dirty?`${state.changes.length} pending change(s) · review before saving`:'Ready · changes stay local';
  const f=state.fields;
  makeOptions($('build'),'ABCDEF'.split('').map(v=>({value:v,label:`Build ${v}`})),f?'ABCDEF'[f.caf_values[0]]:'C');
  makeOptions($('skin'),state.skins.map(n=>({value:n,label:`Tone ${n}`})),f?.caf_values[1]);
  const category=$('category').value;
  $('category').replaceChildren();
  for(const section of [...new Set(state.groups.map(g=>g.section))]){const group=document.createElement('optgroup');group.label=section;for(const g of state.groups.filter(g=>g.section===section))group.append(new Option(g.label,g.id));$('category').append(group);}
  $('category').value=state.groups.some(g=>g.id===category)?category:'12';
  $('stats').replaceChildren();
  for(const [key,label] of [['upper','Upper power'],['lower','Lower power'],['speed','Speed'],['toughness','Toughness'],['health','Health']]){
    const row=document.createElement('div');row.className='stat-row';const heading=document.createElement('div');heading.className='stat-heading';const span=document.createElement('span');span.textContent=label;const number=document.createElement('input');Object.assign(number,{type:'number',min:'0',max:'50',value:String(f?.stats[key]||0)});number.id=`stat-${key}`;number.setAttribute('aria-label',label);const slider=document.createElement('input');Object.assign(slider,{type:'range',min:'0',max:'50',value:number.value});slider.setAttribute('aria-label',label+' slider');slider.oninput=()=>number.value=slider.value;number.oninput=()=>slider.value=number.value;const change=()=>{const value=Number(number.value);if(!Number.isInteger(value)||value<0||value>50){fail(new Error('Training stats must be 0–50.'));return;}act('stage',{edits:{stats:{[key]:value}}});};number.onchange=change;slider.onchange=change;heading.append(span,number);row.append(heading,slider);$('stats').append(row);
  }
  $('cash').value=f?.cash??0;$('development').value=f?.development??0;
  for(let i=0;i<3;i++)makeOptions($(`style-${i}`),[...(i?[{value:-1,label:'None'}]:[]),...state.style_names.map((name,n)=>({value:n,label:name}))],f?.styles[i]??-1);
  $('moveset').textContent=f?.styles.length?f.styles.map(i=>state.style_names[i]).join(' + '):'No fighting style assigned.';
  for(const el of document.querySelectorAll('.tab-content input,.tab-content select,.tab-content button'))el.disabled=!readyFighter()||(el.closest('#tab-appearance')&&!state.preview_available);
  $('cash').disabled=$('development').disabled=Boolean(state.project)||!readyFighter();
  $('new-project').disabled=!readyFighter();
  $('portrait-status').textContent=state.portrait_available?'Project portrait selected':'Portraits currently inherit the presentation donor.';
  $('atlas-status').textContent=state.atlas_slots?.length?'Imported: '+state.atlas_slots.join(', ').toUpperCase():'Using original CAF textures.';
  $('project-path').textContent=state.project_path||'Create a project to author a Custom Fighter Mod.';
  for(const key of ['name','author','version','description','license','donor']){const input=$('project-'+key);input.value=state.project?.metadata[key]||'';input.disabled=!state.project;}
  for(const key of ['pack','fighter']){$('project-'+key).value=state.project?.identity[key]||'';$('project-'+key).disabled=!state.project;}
  for(const id of ['save-project-details','project-copy','export-mod','capture-portrait','import-portrait','import-atlas','clear-atlases','atlas-slot'])$(id).disabled=!state.project;
  makeOptions($('outfit-select'),(state.outfits||[]).map((row,i)=>({value:row.id,label:`${i+1}. ${row.name}`})),state.active_outfit);
  $('outfit-select').disabled=!state.project;
  $('outfit-name').value=state.outfits?.find(row=>row.id===state.active_outfit)?.name||'';
  $('outfit-name').disabled=$('rename-outfit').disabled=!state.project;
  $('add-outfit').disabled=!state.project||(state.outfits?.length||0)>=3;
  $('remove-outfit').disabled=!state.project||state.active_outfit==='default';
  $('outfit-status').textContent=state.project?'Stats, fighting styles and Blazin’ moves are shared. Appearance, textures and portraits belong to the selected outfit.':'Create or open a fighter project to add outfits.';
  renderBlazin(state);
  renderUIArt(state);
  renderFacePresets(state);
  renderMovesets(state);
  performanceUI.render(state);
  loadCategory().catch(fail);
  queuePreview(0);
}
function renderMovesets(state){
  const data=state.retail_movesets||{};
  makeOptions($('retail-moveset'),(data.options||[]).map(row=>({value:row.key,label:row.label})),data.selected||data.options?.[0]?.key);
  $('moveset-mode').value=data.selected?'retail':'caf';
  $('moveset-status').textContent=data.error||'Retail names identify the full original moveset, including fighter-specific attacks.';
  updateMovesetMode();
}
function updateMovesetMode(){
  const retail=$('moveset-mode').value==='retail';
  $('caf-style-controls').hidden=retail;$('retail-style-controls').hidden=!retail;
  $('apply-styles').disabled=!readyFighter()||(retail&&!current?.retail_movesets?.options?.length);
  if(retail)$('moveset-status').textContent='Retail movesets require the companion CAF v5 runtime. Story career styles and training are preserved.';
  const row=current?.retail_movesets?.options.find(row=>row.key===$('retail-moveset').value);
  $('moveset').textContent=retail?(row?row.label+' · retail moveset':'Unavailable original moveset'):current?.fields?.styles.map(i=>current.style_names[i]).join(' + ')||'No fighting style assigned.';
}
function renderFaceSculpt(state){
  const data=state.face_sculpt||{},root=$('face-sliders');root.replaceChildren();
  for(const row of data.controls||[]){
    const label=document.createElement('label');label.textContent=row.label;
    const slider=document.createElement('input');slider.id='sculpt-'+row.id;slider.type='range';slider.min=-1;slider.max=1;slider.step=.01;slider.value=data.sliders?.[row.id]||0;slider.disabled=!data.available||data.imported;
    const output=document.createElement('output');output.textContent=Number(slider.value).toFixed(2);slider.oninput=()=>{
      output.textContent=Number(slider.value).toFixed(2);
      faceDraft=makeFaceDraft(data.controls,data.sliders||{},faceSliderValues());updateFacePreviewStatus();
      if(faceFrame===null)faceFrame=requestAnimationFrame(()=>{faceFrame=null;applyFacePreview();});
    };
    label.append(slider,output);root.append(label);
  }
  for(const id of ['apply-face-sliders','export-face','import-face','clear-face'])$(id).disabled=!data.available;
  $('apply-face-sliders').disabled=!data.available||data.imported;
  $('clear-face').disabled=!data.available||!data.present;
  updateFacePreviewStatus();
  $('face-sculpt-status').textContent=!data.available?'Create a standalone fighter project to use face sculpting. Story CAFs use the preset controls above.':data.imported?'Imported sculpt staged in this outfit.':data.present?'Slider sculpt staged in this outfit.':'Original head presets; no sculpt.';
}
function faceSliderValues(){return Object.fromEntries((current?.face_sculpt?.controls||[]).map(({id})=>[id,Number($('sculpt-'+id).value)]));}
function updateFacePreviewStatus(){
  const data=current?.face_sculpt||{};
  $('revert-face-preview').disabled=!faceDraft;
  $('export-face').disabled=!data.available||Boolean(faceDraft);
  $('face-preview-status').textContent=!data.available?'Create a standalone project to preview face proportions.':data.imported?'Imported sculpt: clear it under Expert to enable sliders.':faceDraft?'Preview only · Apply face proportions adds these changes to Pending Changes.':'Drag a slider to preview immediately. Apply adds the preview to Pending Changes; Save project writes it.';
}
function applyFacePreview(repose=true){
  if(!sceneData?.face_preview||faceSceneEpoch!==previewEpoch)return;
  const values=faceDraft||current?.face_sculpt?.sliders||{};
  const rows=new Map(sceneData.face_preview.meshes.map(row=>[row.rm,row]));
  const head=model.children.filter(mesh=>String(mesh.userData.source.slot)==='2');
  for(const mesh of head){const row=rows.get(mesh.userData.source.rm);if(row)mesh.userData.source.positions=blendFace(row,values);}
  if(repose)applyPose(head);
  window.__cafFacePreview={values:{...values},temporary:Boolean(faceDraft),head:head.map(mesh=>({rm:mesh.userData.source.rm,positions:Array.from(mesh.geometry.getAttribute('position').array)}))};
}
function revertFacePreview(){
  faceDraft=null;if(faceFrame!==null)cancelAnimationFrame(faceFrame);faceFrame=null;
  renderFaceSculpt(current);applyFacePreview();
}
function renderFacePresets(state){
  renderFaceSculpt(state);
  const root=$('face-presets');root.replaceChildren();
  for(const row of state.face_presets||[]){
    const label=document.createElement('label');label.textContent=row.label;
    const select=document.createElement('select');select.id='face-'+row.id;
    makeOptions(select,row.options,row.value);
    if(!row.options.some(option=>option.value===row.value)){
      const preserved=new Option('Unavailable saved preset · preserved',String(row.value));preserved.disabled=true;select.prepend(preserved);select.value=String(row.value);
    }
    select.disabled=!readyFighter()||!row.options.length;
    select.onchange=()=>act('appearance',{changes:{[row.id]:Number(select.value)}},'Updating face…');
    label.append(select);root.append(label);
  }
}
function renderBlazin(state){
  const catalog=state.blazin,rows=catalog?.options||[],sources=[...new Set(rows.map(row=>row.source))];
  for(let slot=0;slot<4;slot++){
    const select=$(`blazin-${slot}`),selected=catalog?.selected[slot];select.replaceChildren();
    const known=rows.some(row=>row.key===selected);
    const placeholder=new Option(selected&&!known?'Unavailable saved move · choose a replacement':state.project?'Inherited · choose a move':'Unassigned · choose a move','');
    placeholder.disabled=true;select.append(placeholder);
    for(const source of sources){const group=document.createElement('optgroup');group.label=source;for(const row of rows.filter(row=>row.source===source))group.append(new Option(row.label,row.key));select.append(group);}
    select.value=known?selected:'';select.disabled=!readyFighter()||!rows.length;
  }
  $('apply-blazin').disabled=!readyFighter()||!rows.length;
  $('inherit-blazin').hidden=!state.project;$('inherit-blazin').disabled=!readyFighter()||!rows.length;
  $('blazin-status').textContent=catalog?.error||`${rows.length} moves available · all fighters and styles`;
}
function groupKey(o){return `${o.garment}||${(Number(o.key.split(':')[1])&0xff00ffff)>>>0}`;}
async function loadCategory(){
  const epoch=++categoryEpoch;
  if(!readyFighter()||!current.preview_available){options=[];return;}
  const slot=$('category').value;if(!slot)return;
  const result=await call('options',{slot});if(epoch!==categoryEpoch)return;options=result;
  selectionKey=current.appearance_selected?.[slot];
  wardrobe();
}
function wardrobe(){
  const query=$('search').value.toLowerCase().trim(),filtered=options.filter(o=>o.label.toLowerCase().includes(query));
  const groups=new Map();for(const o of filtered)if(!groups.has(groupKey(o)))groups.set(groupKey(o),o.garment);
  const selected=options.find(o=>o.key===selectionKey),prior=$('garment').value;
  const value=selected&&groups.has(groupKey(selected))?groupKey(selected):groups.has(prior)?prior:groups.keys().next().value;
  makeOptions($('garment'),[...groups].map(([value,label])=>({value,label})),value);
  renderColors(selected);updateEquipped();
}
function garmentOptions(){return options.filter(o=>groupKey(o)===$('garment').value);}
function renderColors(selected=null){const rows=garmentOptions(),colors=[...new Set(rows.map(o=>o.color_name))];makeOptions($('color'),colors.map(v=>({value:v,label:v||'Default'})),selected&&rows.includes(selected)?selected.color_name:colors[0]);renderFittings(selected);}
function renderFittings(selected=null){const rows=garmentOptions().filter(o=>o.color_name===$('color').value),fits=[...new Set(rows.map(o=>o.fitting))];makeOptions($('fitting'),fits.map(v=>({value:v,label:v||'Default'})),selected&&rows.includes(selected)?selected.fitting:fits[0]);$('equip').disabled=!rows.length;}
function selectedOption(){return garmentOptions().find(o=>o.color_name===$('color').value&&o.fitting===$('fitting').value);}
function updateEquipped(){const selected=options.find(o=>o.key===selectionKey),audition=options.find(o=>o.key===auditionKey);$('equipped-label').textContent=audition&&audition.key!==selectionKey?'Trying on: '+audition.label+' · Equip to add to Pending Changes.':selected?'Equipped: '+selected.label:'Saved selection is preserved.';$('equip').disabled=!selectedOption()||selectedOption().key===selectionKey;}
function tryOn(){const selected=selectedOption();auditionKey=selected&&selected.key!==selectionKey?selected.key:null;updateEquipped();queuePreview();}

const scene=new THREE.Scene();scene.background=null;
const camera=new THREE.PerspectiveCamera(32,1,.01,1000);
const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0,0);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;
$('viewport').append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.075;controls.minDistance=.2;controls.maxDistance=100;
const fill=new THREE.HemisphereLight(0xe5edd6,0x3c4538,2.1);scene.add(fill);const key=new THREE.DirectionalLight(0xffedcc,3.5);key.position.set(3,5,5);scene.add(key);const rim=new THREE.DirectionalLight(0xaac7b7,2.5);rim.position.set(-4,3,-3);scene.add(rim);
let model=new THREE.Group(),bounds=null,baseline=null;scene.add(model);
function dispose(){performanceUI.stop();for(const child of model.children){child.geometry?.dispose();child.material?.dispose();child.skeleton?.dispose();}for(const texture of atlasTextures)texture.dispose();atlasTextures=[];scene.remove(model);model=new THREE.Group();scene.add(model);}
function frame(view='fit'){
  if(!bounds)return;const [lo,hi]=bounds;const center=new THREE.Vector3(...lo).add(new THREE.Vector3(...hi)).multiplyScalar(.5),height=hi[1]-lo[1];let target=center,distance=height*1.98;
  if(view==='face'){target=new THREE.Vector3(center.x,hi[1]-height*.12,center.z);distance=height*.61;}
  controls.target.copy(target);camera.position.set(target.x,target.y+(view==='face'?0:height*.03),target.z+(view==='back'?-distance:distance));camera.near=Math.max(.001,height*.001);camera.far=height*100;camera.updateProjectionMatrix();controls.update();
}
async function renderScene(data,keepCamera,epoch){
  const textures={};const loader=new THREE.TextureLoader();
  await Promise.all(Object.entries(data.textures).map(async([name,url])=>{const tex=await loader.loadAsync(url);tex.colorSpace=THREE.SRGBColorSpace;tex.flipY=false;tex.wrapS=tex.wrapT=THREE.ClampToEdgeWrapping;tex.magFilter=THREE.LinearFilter;tex.minFilter=THREE.LinearMipmapLinearFilter;tex.anisotropy=renderer.capabilities.getMaxAnisotropy();textures[name]=tex;}));
  if(epoch!==previewEpoch){for(const texture of Object.values(textures))texture.dispose();return false;}
  dispose();
  atlasTextures=Object.values(textures);sceneData=data;faceSceneEpoch=epoch;
  for(const part of data.meshes){const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(part.positions.flat(),3));geometry.setAttribute('normal',new THREE.Float32BufferAttribute(part.normals.flat(),3));geometry.setAttribute('uv',new THREE.Float32BufferAttribute(part.uv.flat(),2));geometry.setIndex(part.indices);const material=materialFor(textures[part.atlas],part.transparent);const mesh=new THREE.Mesh(geometry,material);mesh.userData={atlas:part.atlas,transparent:part.transparent,source:part};model.add(mesh);}
  bounds=data.bounds;applyFacePreview(false);applyPose();if(!keepCamera)frame();$('empty').hidden=true;$('empty').style.display='none';window.__cafPreview={meshes:data.meshes.length,bounds:data.bounds,ready:true,part:auditionKey,hideClothes:$('no-clothes').checked};updateViewState();return true;
}
function materialFor(texture,transparent){const config={map:texture,transparent:Boolean(transparent),side:THREE.FrontSide};return $('lighting').value!=='flat'?new THREE.MeshStandardMaterial({...config,roughness:.85,metalness:0}):new THREE.MeshBasicMaterial(config);}
function updateViewState(){const box=new THREE.Box3().setFromObject(model);window.__cafView={pose:$('pose').value,lighting:$('lighting').value,hideClothes:$('no-clothes').checked,materials:[...new Set(model.children.map(m=>m.material.type))],bounds:box.isEmpty()?null:[box.min.toArray(),box.max.toArray()]};$('preview-note').textContent=[performanceUI.active()?'Decoded source body/root animation · playback limits in Animation':$('pose').value==='tpose'?'Source T-pose':'Approximate static preview pose',...(sceneData?.notices||[])].join(' · ');}
function applyPose(meshes=model.children){if(!sceneData)return;for(const mesh of meshes){const posed=poseMesh(mesh.userData.source,performanceUI.active()?'tpose':$('pose').value,sceneData.arm_pivots);mesh.geometry.setAttribute('position',new THREE.Float32BufferAttribute(posed.positions.flat(),3));mesh.geometry.setAttribute('normal',new THREE.Float32BufferAttribute(posed.normals.flat(),3));mesh.geometry.computeBoundingBox();mesh.geometry.computeBoundingSphere();}updateViewState();}
function applyLighting(){
  const name=$('lighting').value,settings={studio:[0xe5edd6,0x3c4538,0xffedcc,0xaac7b7,2.1,3.5,2.5,1.2],warm:[0xffe5bf,0x423126,0xffcf9a,0xffbb77,1.8,3,1.5,1.05],cool:[0xc7e4ff,0x242c44,0xb5d5ff,0xa288ff,1.2,3.4,3.5,1.15],flat:[0xffffff,0x000000,0xffffff,0xffffff,0,0,0,1]}[name];
  fill.color.setHex(settings[0]);fill.groundColor.setHex(settings[1]);key.color.setHex(settings[2]);rim.color.setHex(settings[3]);fill.intensity=settings[4];key.intensity=settings[5];rim.intensity=settings[6];renderer.toneMappingExposure=settings[7];renderer.toneMapping=name==='flat'?THREE.NoToneMapping:THREE.ACESFilmicToneMapping;
  document.querySelector('.fighter-stage').dataset.lighting=name;
  for(const mesh of model.children){const old=mesh.material;mesh.material=materialFor(old.map,mesh.userData.transparent);old.dispose();}updateViewState();
}
function queuePreview(delay=140){clearTimeout(previewTimer);const epoch=++previewEpoch;window.__cafPreview={...window.__cafPreview,ready:false,loading:true};previewTimer=setTimeout(()=>updatePreview(epoch),delay);}
async function updatePreview(epoch){
  if(!readyFighter()||!current.preview_available){dispose();$('empty').hidden=false;$('empty').style.display='flex';$('empty').querySelector('h3').textContent=current?.selected?'No preview available':'Your fighter, your way.';$('empty').querySelector('p').textContent=current?.preview_error||'Create a Story fighter in the game to begin editing.';window.__cafPreview={ready:false};return;}
  $('status-message').textContent='Updating fighter preview…';
  try{const data=await call('preview',{changes:auditionKey?{part:auditionKey}:{},hide_clothes:$('no-clothes').checked});if(epoch!==previewEpoch)return;const same=baseline===current.selected;if(!await renderScene(data,same,epoch))return;baseline=current.selected;$('status-message').textContent=auditionKey?'Trying on · click Equip to add to Pending Changes':current.dirty?'Preview updated · unsaved changes':'Ready · profile loaded';}
  catch(e){if(epoch===previewEpoch){dispose();$('empty').hidden=false;$('empty').style.display='flex';$('empty').querySelector('h3').textContent='Preview needs attention';$('empty').querySelector('p').textContent=e.message;window.__cafPreview={ready:false,error:e.message};fail(e);}}
}
new ResizeObserver(()=>{const box=$('viewport');renderer.setSize(box.clientWidth,box.clientHeight,false);camera.aspect=box.clientWidth/Math.max(1,box.clientHeight);camera.updateProjectionMatrix();}).observe($('viewport'));
const performanceUI=performanceEditor({$,call,act,fail,state:()=>current,parts:()=>sceneData?.meshes||[],meshes:()=>[...model.children],repose:()=>applyPose()});
renderer.setAnimationLoop(now=>{performanceUI.tick(now);controls.update();renderer.render(scene,camera);});

let uiArtEpoch=0;
async function previewUIArt(){
  const epoch=++uiArtEpoch,role=$('ui-role').value;
  $('ui-image').hidden=true;
  const row=current?.ui_art?.roles.find(r=>r.id===role);
  $('ui-clear').disabled=!current?.project||!row?.own;
  $('ui-role-status').textContent=row?`${row.label} · ${row.origin.source}${row.origin.role?' · '+row.origin.role:''}`:'Create or open a fighter project to import UI artwork.';
  if(!current?.project||!role)return;
  try{const result=await call('ui_preview',{role});if(epoch!==uiArtEpoch)return;$('ui-image').hidden=!result?.png;if(result?.png)$('ui-image').src=result.png;window.__cafUIArt={role,ready:true,hasImage:Boolean(result?.png)};}catch(e){if(epoch===uiArtEpoch)fail(e);}
}
function renderUIArt(state){
  const ui=state.ui_art,role=$('ui-role').value;
  $('ui-donor').value=ui?.donor||'retail/blaze';$('ui-scale').value=String(ui?.hd_scale||4);
  $('ui-role').replaceChildren();const groups=new Map();
  for(const row of ui?.roles||[]){let group=groups.get(row.group);if(!group){group=document.createElement('optgroup');group.label=row.group;groups.set(row.group,group);$('ui-role').append(group);}group.append(new Option(row.label,row.id));}
  if((ui?.roles||[]).some(r=>r.id===role))$('ui-role').value=role;
  for(const id of ['ui-donor','ui-scale','ui-role','ui-apply-settings','ui-retail','ui-import','ui-clear-all'])$(id).disabled=!state.project;
  const outfit=state.outfits?.find(r=>r.id===state.active_outfit);
  $('ui-outfit').textContent=state.project?`Editing ${outfit?.name||'Outfit 1'}. ${state.active_outfit==='default'?'These UI defaults are shared with the other outfits.':'Overrides apply to this outfit.'}`:'UI artwork belongs to standalone fighter projects.';
  const variants=(ui?.roles||[]).filter(r=>r.group!=='All layouts');
  $('ui-coverage').textContent=ui?`${variants.filter(r=>r.available).length}/24 roles use project images. Remaining roles inherit the UI donor. ${ui.hd_scale===1?'Native output.':ui.hd_scale+'× HD tiles accompany the native fallback.'}`:'';
  previewUIArt();
}
$('ui-role').onchange=previewUIArt;
$('ui-import').onclick=()=>act('choose_ui_art',{role:$('ui-role').value},'Importing UI artwork…');
$('ui-clear').onclick=()=>act('ui_clear',{role:$('ui-role').value});
$('ui-clear-all').onclick=()=>act('ui_clear_all');
$('ui-apply-settings').onclick=()=>act('ui_settings',{donor:$('ui-donor').value,hd_scale:Number($('ui-scale').value)});
$('ui-retail').onclick=()=>act('choose_ui_retail',{},'Importing the complete retail UI set…');
for(const b of document.querySelectorAll('.tab'))b.onclick=()=>{for(const button of document.querySelectorAll('.tab'))button.classList.toggle('active',button===b);for(const panel of document.querySelectorAll('.tab-content'))panel.hidden=panel.id!==`tab-${b.dataset.tab}`;};
$('open-data').onclick=$('empty-open').onclick=()=>{if(discard())act('choose_data',{},'Loading profiles and original assets…');};
$('refresh').onclick=()=>{if(current?.data&&discard())act('open_data',{path:current.data},'Refreshing profiles…');};
$('import').onclick=()=>{if(discard())act('choose_import',{},'Importing complete profile…');};
$('export').onclick=()=>act('choose_export',{},'Exporting complete profile…');
$('duplicate').onclick=()=>act('choose_duplicate',{},'Duplicating profile…');
$('save').onclick=()=>{if(current.project){act('save',{},'Saving fighter project…');return;}const risky=current.retail_moveset_save;if(confirm((risky?risky+'\n\n':'')+'Save these changes to '+current.selected+'?\n\n'+current.changes.join('\n')+'\n\nA backup will be created first. Close the game before saving.'))act('save',risky?{acknowledge_retail_moveset:true}:{},'Saving profile and backup…');};
$('open-project').onclick=()=>{if(discard())act('choose_project',{},'Opening fighter project…');};
$('new-project').onclick=()=>act('choose_new_project',{},'Creating standalone fighter project…');
$('capture-portrait').onclick=()=>{if(faceDraft){fail(new Error('Apply or revert the face preview before capturing its portrait.'));return;}if(!window.__cafPreview?.ready||auditionKey||$('no-clothes').checked){fail(new Error('Finish or cancel try-on and show the full outfit before capturing its portrait.'));return;}const size=renderer.getSize(new THREE.Vector2()),ratio=renderer.getPixelRatio(),scale=Math.min(1,1024/Math.max(size.x,size.y));renderer.setPixelRatio(1);renderer.setSize(Math.round(size.x*scale),Math.round(size.y*scale),false);renderer.render(scene,camera);const png=renderer.domElement.toDataURL('image/png');renderer.setPixelRatio(ratio);renderer.setSize(size.x,size.y,false);renderer.render(scene,camera);act('project_portrait',{png});};
$('import-portrait').onclick=()=>act('choose_project_portrait',{},'Importing portrait PNG…');
$('import-atlas').onclick=()=>act('choose_project_atlas',{slot:$('atlas-slot').value},'Importing texture atlas…');
$('clear-atlases').onclick=()=>act('project_atlas_clear',{},'Clearing imported atlases…');
$('outfit-select').onchange=()=>act('outfit_select',{id:$('outfit-select').value},'Switching outfit…');
$('add-outfit').onclick=()=>act('outfit_add',{},'Copying outfit…');
$('rename-outfit').onclick=()=>act('outfit_rename',{name:$('outfit-name').value});
$('remove-outfit').onclick=()=>{if(confirm('Remove this outfit from the project? Save writes the change.'))act('outfit_remove');};
$('project-copy').onclick=()=>act('choose_project_copy',{},'Saving project copy…');
$('save-project-details').onclick=()=>act('project_metadata',projectDetails(),'Saving project & details…');
for(const key of ['name','author','version','description','license','donor','pack','fighter'])$('project-'+key).oninput=async()=>{try{const state=await call('project_metadata_draft',projectDetails());current=state;window.__cafState=state;$('save').disabled=!state.dirty;$('reset').disabled=!state.dirty;$('save-status').textContent=state.dirty?'● Unsaved changes':'● Saved project';$('save-status').classList.toggle('dirty',state.dirty);$('changes').replaceChildren(...state.changes.map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));}catch(e){fail(e);}};
$('export-mod').onclick=()=>act('choose_mod_export',{},'Validating and exporting fighter mod…');
$('export-face').onclick=()=>act('choose_face_export',{},'Exporting head template…');
  $('import-face').onclick=()=>act('choose_face_import',{},'Validating head sculpt…');
  $('clear-face').onclick=()=>act('face_clear');
  $('apply-face-sliders').onclick=()=>act('face_sliders',{values:faceSliderValues()},'Staging face proportions…');
  $('revert-face-preview').onclick=revertFacePreview;
  $('undo').onclick=()=>act('undo');$('reset').onclick=()=>{if(confirm('Reset all unsaved fighter changes?'))act('reset');};
$('build').onchange=()=>act('appearance',{changes:{build:$('build').value}});
$('skin').onchange=()=>act('appearance',{changes:{skin:Number($('skin').value)}});
$('category').onchange=()=>{auditionKey=null;$('search').value='';loadCategory().catch(fail);queuePreview();};$('search').oninput=()=>{wardrobe();tryOn();};
$('garment').onchange=()=>{renderColors();tryOn();};$('color').onchange=()=>{renderFittings();tryOn();};$('fitting').onchange=tryOn;
$('equip').onclick=()=>{const selected=garmentOptions().find(o=>o.color_name===$('color').value&&o.fitting===$('fitting').value);if(selected)act('appearance',{changes:{part:selected.key}});};
for(const id of ['cash','development'])$(id).onchange=()=>{const value=Number($(id).value);if(!Number.isInteger(value)||value<0||value>current.limits[id]){fail(new Error(`${id} must be between 0 and ${current.limits[id].toLocaleString()}.`));return;}act('stage',{edits:{[id]:value}});};
  $('moveset-mode').onchange=updateMovesetMode;$('retail-moveset').onchange=updateMovesetMode;
  $('apply-styles').onclick=()=>{if($('moveset-mode').value==='retail'){act('fighting_style',{mode:'retail',fighter:$('retail-moveset').value});return;}const styles=[0,1,2].map(i=>Number($(`style-${i}`).value));if(styles[1]===-1&&styles[2]!==-1){fail(new Error('Choose a second style before adding a third.'));return;}act('fighting_style',{mode:'caf',styles:styles.filter(s=>s!==-1)});};
$('apply-blazin').onclick=()=>{const moves=[0,1,2,3].map(i=>$(`blazin-${i}`).value);if(moves.some(key=>!key)){fail(new Error('Choose a move for all four Blazin’ slots.'));return;}act('blazin',{moves});};
$('inherit-blazin').onclick=()=>act('blazin_inherit');
for(const id of ['front','back','face','fit'])$(id).onclick=()=>frame(id);
$('pose').onchange=()=>{performanceUI.stop();applyPose();};$('lighting').onchange=applyLighting;$('no-clothes').onchange=()=>{queuePreview(0);updateViewState();};
applyLighting();

new QWebChannel(qt.webChannelTransport,channel=>{
  bridge=channel.objects.editor;
  bridge.response.connect(raw=>{const message=JSON.parse(raw),task=pending.get(message.id);if(!task)return;pending.delete(message.id);if(task.label){busyCount--;$('busy').hidden=busyCount<=0;}if(message.error)task.reject(new Error(message.error));else task.resolve(message.result);});
  bridge.progress.connect(message=>{$('busy-label').textContent=message;$('status-message').textContent=message;});
  act('boot',{},'Loading local fighter data…');
});
