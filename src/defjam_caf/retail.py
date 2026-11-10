"""Portable retail/owned fighters using the runtime's ordinary resource contract.

The editor stages assets and donor choices; the selected runtime remains the
authority for rig, event, resource and complete native compilation acceptance.
"""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import uuid
import zipfile

from . import projects, ui_art
from .container import SaveError

SCHEMA = 'ffny-retail-fighter-project-1'
MAX_ASSET = 64 * 1024**2
MAX_TOTAL = 64 * 1024**2
MAX_TEXTURE = 16 * 1024**2
KINDS = {'appearance':'appearance','moveset':'moveset','voice':'voice','ai':'ai',
         'portrait':'portrait','intro':'cinematic','victory':'cinematic','blazin':'blazin'}


def texture_namespace(pack, resource, shapes):
    alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';result={}
    for shape in shapes:
        number=int.from_bytes(hashlib.sha256((pack+'/'+resource+'/'+shape).encode()).digest()[:8],'little');token=''
        for _ in range(4):token+=alphabet[number%len(alphabet)];number//=len(alphabet)
        result[shape]=token
    projects.require(len(set(result.values()))==len(result),'Texture namespace collision; choose a different pack ID')
    return result


def relative(value):
    projects.require(type(value) is str and value and '\\' not in value and ':' not in value,
                     'Asset paths must be portable relative paths')
    path = PurePosixPath(value)
    projects.require(not path.is_absolute() and all(p not in ('', '.', '..') for p in path.parts)
                     and str(path) == value, 'Asset path leaves the project')
    return value


def blob(raw):
    projects.require(type(raw) is bytes and len(raw) <= MAX_ASSET, 'Asset exceeds 64 MiB')
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'data': base64.b64encode(raw).decode('ascii')}


def unblob(value):
    projects.require(type(value) is dict and set(value) == {'sha256','data'} and type(value['data']) is str
                     and len(value['data']) <= MAX_ASSET * 4 // 3 + 8, 'Invalid embedded asset')
    try: raw = base64.b64decode(value['data'], validate=True)
    except ValueError as exc: raise SaveError('Invalid embedded asset encoding') from exc
    projects.require(len(raw) <= MAX_ASSET and hashlib.sha256(raw).hexdigest() == value['sha256'], 'Embedded asset hash changed')
    return raw


def texture_bytes(value):
    from PIL import Image
    projects.require(type(value) is str and len(value)<=MAX_TEXTURE*4//3+8,'Body atlas PNG exceeds 16 MiB')
    try:
        raw=base64.b64decode(value,validate=True)
        projects.require(0<len(raw)<=MAX_TEXTURE,'Body atlas PNG exceeds 16 MiB')
        with Image.open(io.BytesIO(raw)) as image:
            projects.require(image.format=='PNG' and 32<=image.width<=2048 and 32<=image.height<=2048,'Body atlas must be a 32–2048px PNG')
            image.verify()
    except (ValueError,OSError) as exc:raise SaveError('Invalid body atlas PNG: '+str(exc)) from exc
    return raw


def descriptors(value):
    if isinstance(value, dict):
        if {'path','sha256'} <= set(value):
            relative(value['path'])
            projects.require(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']), 'Invalid asset digest')
            yield value
        else:
            for child in value.values(): yield from descriptors(child)
    elif isinstance(value, list):
        for child in value: yield from descriptors(child)


def validate(document):
    projects.require(type(document) is dict and set(document) == {'schema','identity','metadata','definition','resources','assets','ui_art','textures'}
                     and document['schema'] == SCHEMA, 'Unsupported retail fighter project fields')
    # Share identity/metadata validation without inventing a second policy.
    dummy = projects.from_fields({'has_fighter':True, 'stats':dict.fromkeys(('health','upper','lower','speed','toughness'),0),
        'styles':[0], 'caf_values':[0,0,0,0,0,1]+[0]*6+[0xffffffff]*26, 'caf_colors':[0]*38}, document['metadata']['name'])
    dummy.update(identity=document['identity'], metadata=document['metadata'])
    projects.validate(dummy)
    definition=document['definition']
    projects.require(type(definition) is dict and set(definition) == {'inherits','components'} and
        type(definition['inherits']) is str and re.fullmatch('retail/[a-z0-9]+(?:-[a-z0-9]+)*',definition['inherits']), 'Choose a retail combat donor')
    components=definition['components']
    projects.require(type(components) is dict and set(components)<=set(KINDS)|{'stats','tier'}, 'Unsupported fighter component')
    for key,value in components.items():
        if key=='stats':
            projects.require(type(value) is dict and set(value)<= {'health','speed','toughness','charisma'}
                and all(type(v) is int and 0<=v<=100 for v in value.values()), 'Retail stats must be integers from 0 to 100')
        elif key=='tier':projects.require(type(value) is int and value in (1,2,4,8),'Invalid roster tier')
        else:projects.require(type(value) is str and re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*',value),'Invalid component reference')
    resources=document['resources']
    projects.require(type(resources) is list and len(resources)<=128,'Too many fighter resources')
    ids=set()
    for resource in resources:
        projects.require(type(resource) is dict and {'id','kind','compatibility'}<=set(resource)
            and set(resource)<={'id','kind','compatibility','source'} and resource['kind'] in set(KINDS.values())
            and type(resource['id']) is str and projects.SLUG.fullmatch(resource['id']) and resource['id'] not in ids,
            'Invalid or duplicate resource')
        ids.add(resource['id'])
    assets=document['assets'];projects.require(type(assets) is dict and len(assets)<=4096,'Too many embedded assets')
    folded=set();used=0
    for name,value in assets.items():
        relative(name);projects.require(name.casefold() not in folded,'Case-colliding asset paths');folded.add(name.casefold());used+=len(unblob(value))
    projects.require(used<=MAX_TOTAL,'Embedded assets exceed 64 MiB')
    for spec in descriptors(resources):
        projects.require(spec['path'] in assets and assets[spec['path']]['sha256']==spec['sha256'],'Resource asset is missing or changed')
    ui_art.validate(document['ui_art'])
    for value in document['ui_art']['images'].values():used+=len(projects.portrait_bytes(value))
    textures=document['textures'];projects.require(type(textures) is dict and len(textures)<=64,'Invalid texture imports')
    for name,value in textures.items():
        projects.require(re.fullmatch('[A-Za-z0-9_]{4}',name) is not None,'Choose a four-character texture shape')
        used+=len(texture_bytes(value))
    projects.require(used<=MAX_TOTAL,'Combined native assets and PNG artwork exceed 64 MiB')
    return document


def new(donor, name='New fighter'):
    return validate({'schema':SCHEMA,'identity':{'pack':'fighter-'+uuid.uuid4().hex[:12],'fighter':'fighter'},
        'metadata':{'name':name,'author':'','version':'0.1.0','description':'','license':'','donor':donor},
        'definition':{'inherits':donor,'components':{}},'resources':[],'assets':{},'textures':{},
        'ui_art':{'images':{},'donor':donor,'hd_scale':4}})


def import_pack(folder, fighter_id):
    """Read one ordinary fighter and its hash-bound transitive JSON assets."""
    folder=Path(folder).resolve();path=folder/'fighters.json'
    projects.require(path.stat().st_size<=8*1024**2,'Pack manifest exceeds 8 MiB')
    manifest=json.loads(path.read_text(encoding='utf-8-sig'),object_pairs_hook=projects.unique)
    projects.require(manifest.get('schema')=='fighter-registry-draft-1' and not manifest.get('requires') and not manifest.get('overrides'),
        'Import an independent ordinary pack without global overrides or dependencies')
    fighter=next((f for f in manifest['fighters'] if f['id']==fighter_id),None)
    projects.require(fighter is not None,'Choose a fighter from this pack')
    projects.require(fighter.get('inherits','').startswith('retail/'),'Imported fighter needs a retail base')
    document=new(fighter['inherits'],fighter['name']);document['identity']={'pack':manifest['id'],'fighter':fighter_id}
    document['metadata']['version']=manifest['version']
    document['definition']={'inherits':fighter['inherits'],'components':copy.deepcopy(fighter['components'])}
    selected={v.split('/',1)[1] for k,v in fighter['components'].items() if k in KINDS and v.startswith(manifest['id']+'/')}
    document['resources']=[copy.deepcopy(r) for r in manifest['resources'] if r['id'] in selected]
    projects.require(len(selected)==len(document['resources']),'Fighter references a missing local resource')
    queue=list(descriptors(document['resources']));used=0
    while queue:
        spec=queue.pop();name=relative(spec['path'])
        if name in document['assets']:
            projects.require(document['assets'][name]['sha256']==spec['sha256'],'Asset has conflicting hashes');continue
        unresolved=folder/name
        projects.require(not any(p.is_symlink() for p in [unresolved,*unresolved.parents] if p!=folder.parent),'Source assets cannot use links')
        source=unresolved.resolve()
        projects.require(source.is_relative_to(folder) and source.is_file(),'Asset leaves source pack')
        projects.require(source.stat().st_size<=MAX_ASSET,'Source asset exceeds budget')
        raw=source.read_bytes();used+=len(raw);projects.require(used<=MAX_TOTAL,'Imported assets exceed 64 MiB')
        projects.require(hashlib.sha256(raw).hexdigest()==spec['sha256'],'Source asset hash changed')
        document['assets'][name]=blob(raw)
        if name.endswith('.json'):
            queue.extend(descriptors(json.loads(raw,object_pairs_hook=projects.unique)))
    return validate(document)


def manifest(document):
    """Bind declared owned data to the combat donor; native compiler proves joins.

    Source geometry, transforms, graph rig hashes, samples and event metadata
    remain unchanged. A family label never bypasses actual compiler admission.
    """
    validate(document);result=copy.deepcopy(document)
    pack=result['identity']['pack'];components=result['definition']['components'];ids={r['id'] for r in result['resources']}
    for key,value in list(components.items()):
        if key in KINDS and value.split('/',1)[1] in ids and not value.startswith('retail/'):
            components[key]=pack+'/'+value.split('/',1)[1]
    family='retail/binding-'+result['definition']['inherits'].split('/',1)[1]
    for resource in result['resources']:
        for key in resource['compatibility']:resource['compatibility'][key]=family
        if resource['kind']=='appearance' and 'source' in resource:resource['source']['donor']=result['definition']['inherits']
    return {'schema':'fighter-registry-draft-1','id':pack,'version':result['metadata']['version'],'requires':{},
        'resources':result['resources'],'fighters':[{'id':result['identity']['fighter'],'name':result['metadata']['name'],**result['definition']}],'overrides':[]}


class Session:
    def __init__(self, owner):
        self.owner=owner;self.runtime=None;self.data=None;self.catalog=None;self.document=None;self.saved=None;self.path=None;self.digest=None;self.history=[];self.draft=None

    def effective(self):
        document=copy.deepcopy(self.document)
        if document is not None and self.draft is not None:
            document['metadata'].update(copy.deepcopy(self.draft['metadata']));document['identity'].update(copy.deepcopy(self.draft['identity']))
        return document

    def api(self, arguments, temporary):
        from .fighter_mod import contract
        projects.require(self.runtime is not None,'Choose the compatible runtime checkout first')
        workspace=self.owner.workspace/'retail';workspace.mkdir(parents=True,exist_ok=True)
        return contract(self.runtime,arguments,temporary,workspace)

    def game(self):
        data=self.data or self.owner.data
        projects.require(data is not None and (data/'extracted').is_dir(),'Choose the Recomp data directory first')
        return data/'extracted'

    def commit(self, document):
        validate(document)
        if document!=self.document:self.history.append(copy.deepcopy(self.document));self.history=self.history[-50:];self.document=document
        self.draft=None
        return self.snapshot()

    def snapshot(self):
        rows=[]
        if self.catalog:
            rows=[{'id':'retail/'+r['id'],'name':r['name'],'stats':r['components']['stats']} for r in self.catalog['fighters']]
        view=self.effective()
        if view is not None:
            view['asset_count']=len(view.pop('assets'))
        data=self.data or self.owner.data
        return {'retail':True,'data':str(data) if data else None,'runtime':str(self.runtime) if self.runtime else None,
            'donors':rows,'document':view,'path':str(self.path) if self.path else None,'dirty':self.effective()!=self.saved,
            'undo':bool(self.history) or self.draft is not None,'roles':[{'id':r,'name':ui_art.MASTERS.get(r,r.replace('_',' '))} for r in ui_art.ROLES]}

    def request(self, action, args):
        workspace=self.owner.workspace/'retail';workspace.mkdir(parents=True,exist_ok=True)
        if action=='snapshot':return self.snapshot()
        if action=='draft':
            projects.require(self.document is not None and set(args)=={'metadata','identity'} and all(type(v) is dict for v in args.values()),'Invalid project details draft')
            projects.require(set(args['metadata'])<=set(self.document['metadata']) and set(args['identity'])=={'pack','fighter'},'Unknown project details draft fields')
            self.draft=copy.deepcopy(args);return {'draft':True,'dirty':self.effective()!=self.saved}
        if action=='configure':
            runtime=Path(args['runtime']).resolve()
            old=self.runtime;self.runtime=runtime
            try:
                with tempfile.TemporaryDirectory(dir=workspace) as temporary:
                    self.catalog=self.api(['catalog','--game',str(self.game())],temporary)['baseline']
            except Exception:self.runtime=old;raise
            return self.snapshot()
        if action in ('new','open','import'):
            if action=='new':document=new(args['donor'])
            elif action=='open':document,digest=projects.read(args['path']);projects.require(document['schema']==SCHEMA,'Open CAF projects in the CAF editor')
            else:document=import_pack(args['folder'],args['fighter'])
            self.document=document;self.saved=copy.deepcopy(document) if action=='open' else None
            self.path=Path(args['path']) if action=='open' else None;self.digest=digest if action=='open' else None;self.history=[];self.draft=None
            return self.snapshot()
        projects.require(self.document is not None,'Create or open a retail fighter project')
        if action=='undo':
            if self.draft is not None:self.draft=None
            elif self.history:self.document=self.history.pop()
            return self.snapshot()
        if action=='reset':
            projects.require(self.saved is not None,'Save this new project before resetting it')
            self.document=copy.deepcopy(self.saved);self.history=[];self.draft=None;return self.snapshot()
        if action=='save':
            target=Path(args['path']) if args.get('path') else self.path
            projects.require(target is not None,'Choose a project destination')
            expected=self.digest if self.path==target else None
            document=validate(self.effective())
            self.digest=projects.write(target,document,expected);self.document=document;self.draft=None;self.path=target;self.saved=copy.deepcopy(document);self.history=[]
            return self.snapshot()
        candidate=self.effective()
        if action=='details':
            candidate['metadata'].update(args['metadata']);candidate['identity'].update(args['identity']);return self.commit(candidate)
        if action=='combat':
            projects.require(self.catalog and any('retail/'+r['id']==args['donor'] for r in self.catalog['fighters']),'Unknown combat donor')
            candidate['definition']['inherits']=args['donor'];candidate['definition']['components'].pop('moveset',None)
            candidate['definition']['components'].pop('stats',None);return self.commit(candidate)
        if action=='component':
            key=args['component'];projects.require(key in KINDS,'Unknown fighter component')
            if args.get('resource'):candidate['definition']['components'][key]=args['resource']
            else:candidate['definition']['components'].pop(key,None)
            return self.commit(candidate)
        if action=='stats':candidate['definition']['components']['stats']=args['stats'];return self.commit(candidate)
        if action=='ui':
            role=args['role'];projects.require(role in ui_art.ROLES,'Unknown artwork role')
            if args.get('png'):
                projects.portrait_bytes(args['png'])
                if role in ui_art.MASTERS:
                    covered={role}|({'grid_normal','grid_selected'} if role=='icon' else set())
                    for key in list(candidate['ui_art']['images']):
                        if ui_art.master(key) in covered:candidate['ui_art']['images'].pop(key)
                candidate['ui_art']['images'][role]=args['png']
            else:candidate['ui_art']['images'].pop(role,None)
            return self.commit(candidate)
        if action=='ui_settings':candidate['ui_art'].update(donor=args['donor'],hd_scale=args['hd_scale']);return self.commit(candidate)
        if action=='texture':
            if args.get('png'):candidate['textures'][args['shape']]=args['png']
            else:candidate['textures'].pop(args['shape'],None)
            return self.commit(candidate)
        if action in ('preview','appearance','export'):
            with tempfile.TemporaryDirectory(prefix='retail-',dir=workspace) as temporary:
                root=Path(temporary)/self.document['identity']['pack'];root.mkdir()
                if action=='appearance':
                    output=Path(temporary)/'appearance'
                    report=self.api(['export-retail-appearance','--game',str(self.game()),'--donor',args['donor'],'--portrait-out',str(output)],temporary)
                    resource={'id':'retail-body','kind':'appearance','compatibility':{'skeleton':'retail/binding-'+args['donor'].split('/')[1]},'source':report['source']}
                    resource['source'].update(format='eagl-appearance-2',shape_names=texture_namespace(candidate['identity']['pack'],'retail-body',report['shapes']))
                    for spec in descriptors(resource):
                        raw=(output/spec['path']).read_bytes();spec['path']='retail-body/'+spec['path'];candidate['assets'][spec['path']]=blob(raw)
                    candidate['resources']=[r for r in candidate['resources'] if r['id']!='retail-body']+[resource]
                    candidate['definition']['components']['appearance']=candidate['identity']['pack']+'/retail-body';candidate['textures']={}
                    return self.commit(candidate)
                native=self.stage(root,temporary)
                if action=='preview':
                    report=self.api(['preview-fighter','--game',str(self.game()),'--pack',str(root)],temporary)
                    return report['preview']
                report=self.api(['validate','--pack',str(root),'--game',str(self.game())],temporary)
                projects.require(report.get('native_compilation') is True,'Runtime did not confirm native compilation')
                destination=Path(args['path']);projects.require(not destination.exists(),'ZIP destination already exists')
                destination.parent.mkdir(parents=True,exist_ok=True);created=False
                try:
                    with destination.open('xb') as output:
                        created=True
                        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
                            for path in sorted(root.rglob('*')):
                                if path.is_file():archive.write(path,root.name+'/'+path.relative_to(root).as_posix())
                except Exception:
                    if created:destination.unlink(missing_ok=True)
                    raise
                return {'snapshot':self.snapshot(),'message':'Validated retail fighter exported to '+str(destination),'report':report}
        raise SaveError('Unsupported retail fighter action')

    def stage(self, root, temporary):
        document=self.effective();native=manifest(document)
        for name,value in document['assets'].items():
            path=root/relative(name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(unblob(value))
        if document['textures']:
            spec={name:{'path':'texture-imports/'+name+'.png','sha256':hashlib.sha256(texture_bytes(value)).hexdigest()}
                  for name,value in document['textures'].items()}
            for name,value in document['textures'].items():
                path=root/spec[name]['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(texture_bytes(value))
            # Typed texture sources are compiled by the runtime, never renamed PNGs.
            key=native['fighters'][0]['components'].get('appearance')
            resource=next((r for r in native['resources'] if key==native['id']+'/'+r['id']),None)
            projects.require(resource is not None,'Import a native appearance before painting its textures')
            mapping=dict(resource['source'].get('shape_names',{}))
            mapping.update(texture_namespace(native['id'],resource['id'],[shape for shape in spec if shape not in mapping]))
            resource['source']={**resource['source'],'format':'eagl-appearance-png-1','images':spec,'shape_names':mapping}
        art=document['ui_art']
        if art['images']:
            source={'format':'eagl-portrait-png-1','donor':art.get('donor',document['metadata']['donor']),
                    'hd_scale':art.get('hd_scale',4),'images':{}}
            for role,value in art['images'].items():
                raw=projects.portrait_bytes(value);name='ui-art/'+hashlib.sha256(raw).hexdigest()+'.png'
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
                source['images'][role]={'path':name,'sha256':hashlib.sha256(raw).hexdigest()}
            native['resources']=[r for r in native['resources'] if r['id']!='workshop-ui']
            native['resources'].append({'id':'workshop-ui','kind':'portrait','compatibility':{},'source':source})
            native['fighters'][0]['components']['portrait']=native['id']+'/workshop-ui'
        selected={v for k,v in native['fighters'][0]['components'].items() if k in KINDS}
        native['resources']=[r for r in native['resources'] if native['id']+'/'+r['id'] in selected]
        # Keep only transitively declared assets; unused imported resources must
        # not leak original art into the export or violate ordinary inventory.
        needed=set();queue=list(descriptors(native['resources']))
        while queue:
            spec=queue.pop();name=spec['path']
            if name in needed:continue
            needed.add(name)
            path=root/name
            projects.require(path.is_file(),'Declared asset is unavailable')
            if name.endswith('.json'):queue.extend(descriptors(json.loads(path.read_bytes(),object_pairs_hook=projects.unique)))
        for path in root.rglob('*'):
            if path.is_file() and path.relative_to(root).as_posix() not in needed:path.unlink()
        (root/'fighters.json').write_text(json.dumps(native,indent=2)+'\n',encoding='utf-8')
        (root/'README.md').write_text('# '+document['metadata']['name']+'\n\n'+document['metadata']['description']+'\n\nAuthor: '+document['metadata']['author']+'\nNative compilation is separate from gameplay acceptance.\n',encoding='utf-8')
        (root/'LICENSE.txt').write_text(document['metadata']['license'] or 'Original and supplied artwork remains outside the source-code license.\n',encoding='utf-8')
        return native
