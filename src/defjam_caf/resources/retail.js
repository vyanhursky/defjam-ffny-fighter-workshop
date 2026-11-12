import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {gameSetup} from './setup.mjs';
const $=id=>document.getElementById(id),pending=new Map();let serial=0,bridge,state,shapeRows=[],epoch=0,detailDraft=null,draftTimer;
// Home chooses the workflow: retail-new (a new fighter from a retail fighter) or retail-edit (change a retail fighter).
const params=new URLSearchParams(location.hash.slice(1)),workflow=params.get('mode')==='retail-edit'?'retail-edit':'retail-new',startKind=params.get('start')||'',startPath=params.get('path')||'';
document.body.dataset.mode=workflow;
function applyWorkflow(){
  const edit=workflow==='retail-edit',purpose=$('deployment-mode');
  $('mode-title').textContent=edit?'RETAIL FIGHTER EDITOR':'FIGHTER FROM A RETAIL FIGHTER';
  document.querySelector('.retail-left .eyebrow').textContent=edit?'CHANGE A RETAIL FIGHTER':'START A NEW FIGHTER';
  $('base-donor').closest('label').firstChild.textContent=edit?'Fighter to change':'Start from this fighter';
  purpose.closest('label').firstChild.textContent='What do you want to do?';
  for(const option of purpose.options){option.hidden=option.disabled=edit?option.value==='add':option.value!=='add';option.textContent={add:'New standalone fighter',override:'Replace how it looks',outfit:'Add an extra outfit'}[option.value];}
  purpose.closest('label').hidden=!edit;$('new').textContent=edit?'Start changing this fighter':'Start new fighter';
  for(const node of [$('deployment-target').closest('label'),$('apply-deployment'),$('deployment-status')])node.hidden=!edit||!state?.document;
}
async function startFlow(){
  if(state?.document)await act('retail_close');
  if(startKind==='open'){if(startPath)await act('retail_open',{path:startPath},'Opening fighter project…');else await act('choose_retail_open');}
}
function call(action,args={}){const id=String(++serial);return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});bridge.dispatch(JSON.stringify({id,action,args}));});}
function status(text,error=false){$('status-message').textContent=text;$('toast').textContent=text;$('toast').classList.toggle('error',error);$('toast').hidden=false;clearTimeout(status.timer);status.timer=setTimeout(()=>$('toast').hidden=true,10000);}
async function act(action,args={},label='Updating fighter…'){if(pending.size)return null;$('busy-label').textContent=label;$('busy').hidden=false;try{if(detailDraft){await call('retail_draft',detailDraft);detailDraft=null;}const result=await call(action,args);if(result?.retail)render(result);if(result?.snapshot)render(result.snapshot);if(result?.message)status(result.message);return result;}catch(e){if(/Game setup/.test(e.message))setup.open(state?.setup);status(e.message,true);return null;}finally{$('busy').hidden=true;}}
// Game setup is shared with the fighter editor; after it changes, the studio reloads its own catalog.
const setup=gameSetup({call,act:async(action,args,label)=>{const result=await act(action,args,label);if(action==='setup_use'||action==='choose_data')await act('retail_snapshot');return result;}});
$('setup-open').onclick=()=>setup.open(state?.setup);
const discard=()=>!state?.dirty||confirm('Discard unsaved retail fighter changes?');
function options(id,rows,value){const previous=value??$(id).value;$(id).replaceChildren(...rows.map(r=>new Option(r.name,r.id)));if(rows.some(r=>r.id===previous))$(id).value=previous;}
function render(s){state=s;window.__retailState=s;const d=s.document,selected=d?.definition.inherits;
  {const chip=setup.chip(s.setup);$('setup-open').textContent=chip.text;$('setup-open').className='chip '+chip.state;setup.offer(s.setup);}
  $('connection').textContent=s.data||'No game data chosen yet';$('saved').textContent=s.dirty?'● Unsaved changes':d?'● Saved project':'No project';
  for(const id of ['base-donor','body-donor','combat-donor','ui-donor','deployment-target'])options(id,s.donors,id==='combat-donor'?selected:id==='ui-donor'?d?.ui_art.donor:id==='deployment-target'?(d?.deployment?.target||selected):null);
  $('new').disabled=!s.donors.length;$('import').disabled=!s.runtime;$('fighter-name').textContent=d?.metadata.name||'YOUR FIGHTER';$('project-path').textContent=s.path||'Save a portable .ffnyfighter project.';
  for(const id of ['name','author','version','description','license']){$(id).value=d?.metadata[id]||'';$(id).disabled=!d;}
  for(const id of ['pack','fighter']){$(id).value=d?.identity[id]||'';$(id).disabled=!d;}
  for(const id of ['save','copy','details','combat','body','apply-stats','ui-import','ui-clear','ui-settings','preview','export','texture','clear-texture'])$(id).disabled=!d;
  $('deployment-mode').value=d?.deployment?.mode||(workflow==='retail-edit'?'override':'add');applyWorkflow();$('apply-deployment').disabled=!d;
  const appearanceOnly=d?.deployment&&d.deployment.mode!=='add';
  $('deployment-status').textContent=d?.deployment?.mode==='override'?'Replaces the existing retail appearance. No extra roster cell is created.':d?.deployment?.mode==='outfit'?'Adds this appearance to the target’s clothing selector. Original outfit stays available; combat, voice and stats remain shared.':'Creates a separate fighter in the roster.';
  for(const id of ['combat','apply-stats'])$(id).disabled=!d||appearanceOnly;
  if(d?.deployment?.mode==='override')for(const id of ['ui-import','ui-clear','ui-settings'])$(id).disabled=true;
  $('undo').disabled=!s.undo;$('reset').disabled=!d||!s.path;$('ui-scale').value=String(d?.ui_art.hd_scale||4);options('role',s.roles);options('shape',shapeRows.length?shapeRows:[{id:'',name:'Load the 3D preview to list the shapes'}]);$('shape').disabled=!shapeRows.length;
  const components=$('components');components.replaceChildren();
  for(const key of ['appearance','voice','blazin','intro','victory','portrait']){const label=document.createElement('label');label.textContent=key==='appearance'?'Model resource':key==='blazin'?'Blazin’ resource':key[0].toUpperCase()+key.slice(1)+' resource';const select=document.createElement('select');select.id='resource-'+key;
    const kind={intro:'cinematic',victory:'cinematic',blazin:'blazin'}[key]||key;const rows=(d?.resources||[]).filter(r=>r.kind===kind);
    select.append(new Option('Inherit from donor',''));for(const row of rows)select.append(new Option(row.id,(d?.identity.pack||'')+'/'+row.id));const chosen=d?.definition.components[key];select.value=chosen&&!chosen.startsWith('retail/')?(d.identity.pack+'/'+chosen.split('/')[1]):chosen||'';select.disabled=!d||(appearanceOnly&&!['appearance','portrait'].includes(key))||(key==='portrait'&&d?.deployment?.mode==='override');
    select.onchange=()=>act('retail_component',{component:key,resource:select.value});label.append(select);components.append(label);}
  const inherited=s.donors.find(r=>r.id===selected)?.stats||{},stats=d?.definition.components.stats||{};$('stats').replaceChildren();
  for(const key of ['health','speed','toughness','charisma']){const line=document.createElement('label');line.className='stat-line';line.textContent=key[0].toUpperCase()+key.slice(1);const input=document.createElement('input');input.id='stat-'+key;input.type='number';input.min=0;input.max=100;input.step=1;input.value=stats[key]??inherited[key]??0;input.disabled=!d;line.append(input);$('stats').append(line);}
  showArt();$('texture-status').textContent=d?Object.keys(d.textures).length+' texture overrides staged.':'';
}
function showArt(){const d=state?.document,role=$('role').value,raw=d?.ui_art.images[role];$('art-image').hidden=!raw;if(raw)$('art-image').src='data:image/png;base64,'+raw;else $('art-image').removeAttribute('src');$('art-status').textContent=d?Object.keys(d.ui_art.images).length+' imported roles · missing art inherits the UI donor.':'';}
$('role').onchange=showArt;
for(const id of ['name','author','version','description','license','pack','fighter'])$(id).oninput=()=>{const metadata={};for(const key of ['name','author','version','description','license'])metadata[key]=$(key).value;detailDraft={metadata,identity:{pack:$('pack').value,fighter:$('fighter').value}};if(state){state.dirty=true;$('saved').textContent='● Unsaved changes';}clearTimeout(draftTimer);const send=async()=>{if(!detailDraft)return;if(pending.size){draftTimer=setTimeout(send,150);return;}const draft=detailDraft;try{await call('retail_draft',draft);if(detailDraft===draft)detailDraft=null;}catch(e){status(e.message,true);}};draftTimer=setTimeout(send,120);};
for(const button of document.querySelectorAll('[data-panel]'))button.onclick=()=>{for(const section of document.querySelectorAll('[data-content]'))section.hidden=section.dataset.content!==button.dataset.panel;for(const item of document.querySelectorAll('[data-panel]'))item.classList.toggle('active',item===button);if(button.dataset.panel==='textures'&&!shapeRows.length&&state?.document?.definition.components.appearance&&!$('preview').disabled)$('preview').click();};
$('home').onclick=()=>act('open_home');window.__retailAct=(...args)=>act(...args);
$('new').onclick=()=>{if(discard())act('retail_new',{donor:$('base-donor').value,mode:$('deployment-mode').value});};$('open').onclick=()=>{if(discard())act('choose_retail_open');};$('import').onclick=()=>{if(discard())act('choose_retail_import',{},'Importing fighter assets…');};
$('save').onclick=()=>act('choose_retail_save');$('copy').onclick=()=>act('choose_retail_copy');$('undo').onclick=()=>act('retail_undo');$('reset').onclick=()=>{if(discard())act('retail_reset');};
$('details').onclick=()=>{const metadata={};for(const k of ['name','author','version','description','license'])metadata[k]=$(k).value;act('retail_details',{metadata,identity:{pack:$('pack').value,fighter:$('fighter').value}});};
$('apply-deployment').onclick=()=>act('retail_deployment',{mode:$('deployment-mode').value,target:$('deployment-target').value});
$('combat').onclick=()=>act('retail_combat',{donor:$('combat-donor').value});$('body').onclick=()=>act('retail_appearance',{donor:$('body-donor').value},'Importing original model resources…');
$('apply-stats').onclick=()=>act('retail_stats',{stats:Object.fromEntries(['health','speed','toughness','charisma'].map(k=>[k,Number($('stat-'+k).value)]))});
$('ui-settings').onclick=()=>act('retail_ui_settings',{donor:$('ui-donor').value,hd_scale:Number($('ui-scale').value)});$('ui-import').onclick=()=>act('choose_retail_ui',{role:$('role').value});$('ui-clear').onclick=()=>act('retail_ui',{role:$('role').value});
$('texture').onclick=()=>act('choose_retail_texture',{shape:$('shape').value});$('clear-texture').onclick=()=>act('retail_texture',{shape:$('shape').value});$('export').onclick=()=>act('choose_retail_export',{},'Compiling and validating the complete fighter…');
const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;$('viewport').append(renderer.domElement);
const scene=new THREE.Scene(),model=new THREE.Group();scene.add(model);const camera=new THREE.PerspectiveCamera(35,1,.01,5000),controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;let bounds,images=[];
function frame(direction=1){if(!bounds)return;const center=new THREE.Vector3(...bounds[0]).add(new THREE.Vector3(...bounds[1])).multiplyScalar(.5),height=bounds[1][1]-bounds[0][1];controls.target.copy(center);camera.position.set(center.x,center.y+height*.04,center.z+direction*height*1.9);camera.near=Math.max(.01,height/1000);camera.far=height*100;camera.updateProjectionMatrix();controls.update();}
$('fit').onclick=()=>frame();$('front').onclick=()=>frame();$('back').onclick=()=>frame(-1);$('wireframe').onchange=()=>{for(const mesh of model.children)mesh.material.wireframe=$('wireframe').checked;};
$('preview').onclick=async()=>{const mine=++epoch,result=await act('retail_preview',{},'Decoding the static model…');if(!result||mine!==epoch)return;
  for(const mesh of [...model.children]){mesh.geometry.dispose();mesh.material.dispose();model.remove(mesh);}for(const image of images)image.dispose();images=[];
  const loader=new THREE.TextureLoader(),textures={};await Promise.all(Object.entries(result.textures).map(async([key,url])=>{const texture=await loader.loadAsync(url);texture.colorSpace=THREE.SRGBColorSpace;texture.flipY=false;textures[key]=texture;images.push(texture);}));
  for(const part of result.meshes){const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(part.positions.flat(),3));geometry.setAttribute('normal',new THREE.Float32BufferAttribute(part.normals.flat(),3));geometry.setAttribute('uv',new THREE.Float32BufferAttribute(part.uv.flat(),2));geometry.setIndex(part.indices);model.add(new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({map:textures[part.atlas],side:THREE.DoubleSide,wireframe:$('wireframe').checked})));}
  bounds=result.bounds;shapeRows=result.shapes.map(r=>({id:r.name,name:r.name+' · '+r.width+'×'+r.height}));options('shape',shapeRows);$('shape').disabled=!state?.document;frame();$('preview-note').textContent=result.notices.join(' · ');window.__retailPreview={ready:true,meshes:result.meshes.length,shapes:result.shapes};
};
new ResizeObserver(()=>{const box=$('viewport');renderer.setSize(box.clientWidth,box.clientHeight,false);camera.aspect=box.clientWidth/Math.max(1,box.clientHeight);camera.updateProjectionMatrix();}).observe($('viewport'));renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
new QWebChannel(qt.webChannelTransport,channel=>{bridge=channel.objects.editor;bridge.response.connect(raw=>{const r=JSON.parse(raw),task=pending.get(r.id);if(!task)return;pending.delete(r.id);if(r.error)task.reject(new Error(r.error));else task.resolve(r.result);});act('retail_snapshot').then(startFlow);});
