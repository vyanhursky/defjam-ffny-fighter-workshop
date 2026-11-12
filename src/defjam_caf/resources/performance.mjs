import * as THREE from 'three';

// Source-track playback is preview state only; it never enters project history.
export function performanceEditor(api){
  const {$,call,act,fail,state,parts,meshes,repose}=api;
  let catalog=null,settings={},aiDraft=null,clip=null,playing=false,time=0,last=null,epoch=0;
  const categories=['Character','Taunts','Enviro'];
  function options(id,rows,value){const el=$(id);el.replaceChildren(...rows.map(r=>new Option(r.label,String(r.key))));if(value!==undefined)el.value=String(value);}
  function preset(){return catalog?.fighters.find(r=>r.key===$('voice-preset').value);}
  function voiceSlots(){
    const category=$('voice-category').value,selected=preset(),bank=Number($('voice-bank-'+category).value||selected?.voice);
    const row=catalog?.banks.find(r=>r.category===category&&r.voice===bank);
    options('voice-slot',[...(row?Array.from({length:row.count},(_,i)=>({key:category+':'+i,label:`${category} clip ${i+1}`})):[]),{key:'intro',label:'Entrance speech'},{key:'extro',label:'Victory speech'}]);
    voiceStatus();
  }
  function voiceStatus(){
    const target=$('voice-slot').value,override=settings.voice?.clips?.[target];
    $('voice-clip-status').textContent=override?`Imported WAV · ${override.seconds.toFixed(2)} s · ${override.sample_rate} Hz`:'Original event slot. Ordinals retain the native bank’s event ordering.';
    $('voice-clear-clip').disabled=!override;$('voice-play-imported').disabled=!override;
  }
  function render(s){
    stop();$('voice-audio').pause();catalog=s.performance?.catalog;settings=s.performance?.settings||{};aiDraft=structuredClone(settings.ai||null);
    const enabled=Boolean(s.project&&catalog);
    for(const id of ['tab-voice','tab-presentation','tab-ai'])for(const el of $(id).querySelectorAll('input,select,button'))el.disabled=!enabled;
    $('performance-connect').disabled=!s.data;
    $('performance-status').textContent=!s.project?'Create or open a standalone project to author performance. Story saves retain their existing workflow.':!catalog?'Load the original voice and animation catalogs. This uses the game version chosen in Game setup.':`${catalog.banks.length} voice banks · ${catalog.cinematics.length} sequences · ${catalog.ai.length} AI profiles. Shared across all outfits.`;
    if(!catalog)return;
    options('voice-preset',catalog.fighters,settings.voice?.preset||s.project?.metadata.donor);
    for(const category of categories){
      options('voice-bank-'+category,[{key:'',label:'Use voice preset'},...catalog.banks.filter(r=>r.category===category).map(r=>({key:r.voice,label:`Bank ${r.voice} · ${r.count} clips`}))],settings.voice?.banks?.[category]??'');
    }
    voiceSlots();
    $('voice-import').disabled=!enabled||!settings.voice;
    for(const role of ['intro','victory'])options('sequence-'+role,[{key:'',label:'Inherit presentation donor'},...catalog.cinematics.filter(r=>r.role===role)],settings[role]||'');
    options('animation-bank',[...catalog.fighters.map(r=>({key:r.core,label:r.label+' · bank '+r.core})),...Array.from({length:55},(_,i)=>({key:87+i,label:'CAF animation bank '+(87+i)}))],catalog.fighters.find(r=>r.key===(s.retail_movesets?.selected||s.project?.metadata.donor))?.core);
    options('animation-clip',[]);
    options('ai-preset',catalog.ai,settings.ai?.preset||catalog.ai.find(r=>r.key==='char0005')?.key);
    if(!aiDraft)aiDraft={preset:$('ai-preset').value,tendencies:Object.fromEntries(['easy','normal','hard'].map(l=>[l,Array.from({length:4},()=>({}))]))};
    renderAI();
    if(!enabled)for(const id of ['tab-voice','tab-presentation','tab-ai'])for(const el of $(id).querySelectorAll('input,select,button'))el.disabled=true;
    $('performance-connect').disabled=!s.data;
  }
  async function save(section,value){return act('performance_set',{section,value},'Staging '+section+'…');}
  function renderAI(){
    const root=$('ai-sliders');root.replaceChildren();if(!aiDraft||!catalog)return;
    const difficulty=$('ai-difficulty').value,slot=Number($('ai-slot').value),edits=aiDraft.tendencies[difficulty][slot];
    const baseline=catalog.ai.find(r=>r.key===aiDraft.preset)?.tendencies[difficulty][slot]||{};
    for(const {id,label} of state().performance.ai_fields){
      const row=document.createElement('div'),head=document.createElement('label'),override=document.createElement('input');override.type='checkbox';override.checked=id in edits;head.append(override,document.createTextNode(label));
      const range=document.createElement('input');Object.assign(range,{type:'range',min:1,max:5,step:1,value:edits[id]??Math.max(1,Math.min(5,baseline[id]??3)),disabled:!override.checked});range.setAttribute('aria-label',label);
      const value=document.createElement('output');value.textContent=override.checked?String(edits[id]):'Inherited: '+baseline[id];
      range.oninput=()=>{edits[id]=Number(range.value);value.textContent=range.value;};
      override.onchange=()=>{range.disabled=!override.checked;if(override.checked)edits[id]=Number(range.value);else delete edits[id];value.textContent=override.checked?range.value:'Inherited: '+baseline[id];};
      row.className='ai-tendency';row.append(head,range,value);root.append(row);
    }
  }
  async function audition(imported=false){
    try{
      const target=$('voice-slot').value,selected=preset();let request;
      if(imported)request={override:target};
      else if(target==='intro'||target==='extro'){
        const stream=selected?.streams[target]?.[0];if(!stream)throw Error('This preset has no original speech stream in this slot.');request={stream};
      }else{const [category,index]=target.split(':');request={category,index:Number(index),voice:Number($('voice-bank-'+category).value||selected.voice)};}
      const result=await call('performance_audio',request,'Decoding voice audition…');
      $('voice-audio').src='data:'+result.mime+';base64,'+result.data;await $('voice-audio').play();
    }catch(error){fail(error);}
  }
  function resetBones(){for(const mesh of meshes())if(mesh.skeleton){const rig=mesh.userData.previewRig;mesh.skeleton.bones.forEach((b,i)=>{b.position.fromArray(rig[i].position);b.quaternion.fromArray(rig[i].quaternion);b.scale.fromArray(rig[i].scale);});}}
  function stop(){epoch++;clip=null;playing=false;time=0;last=null;window.__cafAnimation=null;resetBones();$('animation-play').textContent='Play';$('animation-time').value=0;$('animation-clock').textContent='0.00 s';repose();}
  function attach(data){
    const current=meshes();
    // Check every displayed part before replacing any mesh.
    for(const mesh of current){const source=mesh.userData.source,rig=data.models[source.source_model],skin=rig?.meshes[String(source.rm)];if(!skin||rig.source_sha256!==source.source_model_sha256||skin.indices.length!==source.positions.length)throw Error('Skin mapping differs for '+source.name);}
    for(const old of current){
      const source=old.userData.source,rig=data.models[source.source_model],skin=rig.meshes[String(source.rm)];
      let mesh=old;
      if(!old.isSkinnedMesh){mesh=new THREE.SkinnedMesh(old.geometry,old.material);mesh.userData=old.userData;const parent=old.parent;parent.remove(old);parent.add(mesh);}
      if(mesh.skeleton){for(const child of [...mesh.children])mesh.remove(child);mesh.skeleton.dispose();}
      mesh.geometry.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(skin.indices.flat(),4));mesh.geometry.setAttribute('skinWeight',new THREE.Float32BufferAttribute(skin.weights.flat(),4));
      const bones=rig.bones.map(row=>{const b=new THREE.Bone();b.position.fromArray(row.position);b.quaternion.fromArray(row.quaternion);b.scale.fromArray(row.scale);return b;});
      rig.bones.forEach((r,i)=>{if(r.parent>=0)bones[r.parent].add(bones[i]);else mesh.add(bones[i]);});
      mesh.updateMatrixWorld(true);mesh.bind(new THREE.Skeleton(bones));mesh.userData.previewRig=rig.bones;mesh.frustumCulled=false;
    }
  }
  function pose(){
    if(!clip)return;resetBones();const low=Math.floor(time),high=Math.min(low+1,clip.ticks),alpha=time-low;
    const qa=new THREE.Quaternion(),qb=new THREE.Quaternion();
    for(const channel of clip.channels)for(const mesh of meshes())for(let i=0;i<channel.bones.length;i++){
      const bone=mesh.skeleton.bones[channel.bones[i]],a=channel.samples[low][i],b=channel.samples[high][i];
      if(channel.role==='body'){qa.fromArray(a).normalize();qb.fromArray(b).normalize();bone.quaternion.slerpQuaternions(qa,qb,alpha);}else bone.position.set(...a.map((n,k)=>n+(b[k]-n)*alpha));
    }
    $('animation-time').value=String(time);$('animation-clock').textContent=(time/30).toFixed(2)+' / '+(clip.ticks/30).toFixed(2)+' s';
    window.__cafAnimation={clip:clip.clip,time,playing,ready:true,rotations:meshes()[0].skeleton.bones.map(b=>b.quaternion.toArray())};
  }
  async function load(request){
    stop();const stamp=epoch;
    try{
      const names=[...new Set(parts().map(r=>r.source_model))];if(!names.length)throw Error('Wait for the fighter preview to load.');
      const data=await call('performance_animation',{...request,models:names},'Decoding source animation…');if(stamp!==epoch)return;
      attach(data);clip=data;$('animation-time').max=data.ticks;repose();pose();playing=true;last=null;$('animation-play').textContent='Pause';$('animation-status').textContent=data.notice;
    }catch(error){if(stamp===epoch){stop();$('animation-status').textContent=error.message;fail(error);}}
  }
  function tick(now){if(!playing||!clip){last=null;return;}if(last!==null)time+=Math.min(.1,(now-last)/1000)*30*Number($('animation-speed').value);last=now;if(time>clip.ticks){if($('animation-loop').checked)time%=clip.ticks;else{time=clip.ticks;playing=false;$('animation-play').textContent='Play';}}pose();}
  $('performance-connect').onclick=()=>act('choose_performance_tools',{},'Reading original performance catalogs…');
  $('voice-preset').onchange=voiceSlots;$('voice-category').onchange=voiceSlots;$('voice-slot').onchange=voiceStatus;
  for(const category of categories)$('voice-bank-'+category).onchange=voiceSlots;
  $('voice-apply').onclick=()=>save('voice',{preset:$('voice-preset').value,banks:Object.fromEntries(categories.filter(c=>$('voice-bank-'+c).value!=='').map(c=>[c,Number($('voice-bank-'+c).value)])),clips:{}});
  $('voice-inherit').onclick=()=>act('performance_clear',{section:'voice'});
  $('voice-play').onclick=()=>audition();$('voice-play-imported').onclick=()=>audition(true);
  $('voice-import').onclick=()=>act('choose_voice_clip',{target:$('voice-slot').value},'Importing voice clip…');
  $('voice-clear-clip').onclick=()=>act('performance_clip',{target:$('voice-slot').value,wav:null});
  for(const role of ['intro','victory']){
    $('apply-'+role).onclick=()=>{const value=$('sequence-'+role).value;return value?save(role,value):act('performance_clear',{section:role});};
    $('preview-'+role).onclick=()=>{const value=$('sequence-'+role).value||catalog?.fighters.find(r=>r.key===state().project?.metadata.donor)?.[role];if(value)load({clip:value});else fail(Error('This donor has no simple original sequence.'));};
  }
  $('animation-list').onclick=async()=>{try{const r=await call('performance_animation',{operation:'list',core:Number($('animation-bank').value)},'Reading original animation bank…');options('animation-clip',r.clips.map(key=>({key,label:key})));$('animation-status').textContent=`${r.clips.length} supported clips. ${Object.keys(r.unsupported||{}).length} clips require additional decoders and are excluded.`;}catch(e){fail(e);}};
  $('animation-load').onclick=()=>load({core:Number($('animation-bank').value),clip:$('animation-clip').value});
  $('animation-play').onclick=()=>{if(!clip)return;playing=!playing;if(playing&&time===clip.ticks)time=0;last=null;$('animation-play').textContent=playing?'Pause':'Play';};
  $('animation-stop').onclick=stop;$('animation-time').oninput=()=>{if(!clip)return;time=Number($('animation-time').value);playing=false;$('animation-play').textContent='Play';pose();};
  $('ai-preset').onchange=()=>{aiDraft={preset:$('ai-preset').value,tendencies:Object.fromEntries(['easy','normal','hard'].map(l=>[l,Array.from({length:4},()=>({}))]))};renderAI();};
  $('ai-difficulty').onchange=$('ai-slot').onchange=renderAI;
  $('ai-apply').onclick=()=>save('ai',aiDraft);$('ai-inherit').onclick=()=>act('performance_clear',{section:'ai'});
  return {render,tick,stop,active:()=>Boolean(clip)};
}
