"""Portable UI PNGs: shared defaults and per-outfit role overrides."""
import copy
import io
import re
from . import projects

MASTERS={'selector':'Selector portrait · all layouts','loading':'Loading portrait · all layouts',
         'icon':'Small portrait · results and grid','titlecard':'Titlecard · all screens',
         'grid_normal':'Grid icon · normal','grid_selected':'Grid icon · selected'}
PARTS=tuple(f'{role}_{count}p' for role in ('selector','result','selector_logo','result_logo','loading','loading_logo','grid_normal','grid_selected') for count in (2,3,4))
ROLES=tuple(MASTERS)+PARTS
MAX_TOTAL=48*1024**2


def validate(pack):
    projects.require(type(pack) is dict and {'images'}<=set(pack) and set(pack)<={'images','donor','hd_scale'},'Invalid UI artwork fields')
    if 'donor' in pack:
        projects.require(type(pack['donor']) is str and re.fullmatch(r'retail/[a-z0-9]+(?:-[a-z0-9]+)*',pack['donor']),'Choose a retail UI layout donor')
    if 'hd_scale' in pack:
        projects.require(type(pack['hd_scale']) is int and pack['hd_scale'] in (1,2,4),'UI output scale must be 1, 2 or 4')
    images=pack['images'];projects.require(type(images) is dict and set(images)<=set(ROLES),'Unknown UI artwork role')
    from PIL import Image
    for value in images.values():
        raw=projects.portrait_bytes(value)
        with Image.open(io.BytesIO(raw)) as picture:
            projects.require(picture.convert('RGBA').getchannel('A').getbbox() is not None,'UI PNG is entirely transparent')
    return pack


def check_budget(document):
    from PIL import Image
    used=pixels=0
    for item in [document,*document.get('outfits',[])]:
        for encoded in item.get('ui_art',{}).get('images',{}).values():
            raw=projects.portrait_bytes(encoded);used+=len(raw)
            with Image.open(io.BytesIO(raw)) as image:pixels+=image.width*image.height
    projects.require(used<=MAX_TOTAL and pixels<=64*1024**2,'Combined UI artwork exceeds 48 MiB or 64 megapixels')


def upgrade(document):
    result=copy.deepcopy(document);result['schema']=document['schema'] if document['schema'] in (projects.SCHEMA5,projects.SCHEMA6) else projects.SCHEMA4
    result.setdefault('outfit_name','Outfit 1');result.setdefault('outfits',[])
    return result


def node(document,identity):
    if identity=='default':return document
    found=next((r for r in document.get('outfits',[]) if r['id']==identity),None)
    projects.require(found is not None,'This outfit is unavailable');return found


def master(part):
    if part in MASTERS:return part
    role=part.rsplit('_',1)[0]
    return 'titlecard' if role.endswith('logo') else 'icon' if role=='result' else role


def pick(images,part):
    keys=[part,master(part)]
    if part.startswith('grid_'):keys.append('icon')
    return next(((images[k],k) for k in keys if k in images),(None,None))


def resolved(document,identity):
    selected=node(document,identity);root=document.get('ui_art',{});local=selected.get('ui_art',{}) if identity!='default' else {}
    settings={'donor':document['metadata']['donor'],'hd_scale':4}
    for pack in (root,local):settings.update({k:pack[k] for k in ('donor','hd_scale') if k in pack})
    images={};origins={}
    full_ui=any('ui_art' in item for item in [document,*document.get('outfits',[])])
    for part in ROLES:
        value,key=pick(local.get('images',{}),part);origin='This outfit'
        if value is None:
            value,key=pick(root.get('images',{}),part);origin='Default outfit' if identity!='default' else 'This outfit'
        if value is None and master(part) in ('selector','icon','grid_normal','grid_selected',*(['loading'] if full_ui else [])) and selected.get('portrait'):
            value=selected['portrait'];key='portrait';origin='Captured/imported portrait'
        if value is not None:images[part]=value;origins[part]={'source':origin,'role':key}
    for role in MASTERS:
        if role not in images:
            representative=next((p for p in PARTS if master(p)==role and p in images),None)
            if representative:
                images[role]=images[representative];origins[role]=origins[representative]
    return dict(settings,images=images,origins=origins)


def edit(document,identity,*,role=None,png=None,settings=None,clear_all=False):
    result=upgrade(document);target=node(result,identity)
    if clear_all:
        target.pop('ui_art',None);return result
    pack=target.setdefault('ui_art',{'images':{}})
    if settings is not None:pack.update(settings)
    if role is not None:
        projects.require(role in ROLES,'Unknown UI artwork role')
        if png is None:pack['images'].pop(role,None)
        else:
            projects.portrait_bytes(png)
            if role in MASTERS:
                covered={role}|({'grid_normal','grid_selected'} if role=='icon' else set())
                for key in list(pack['images']):
                    if master(key) in covered:pack['images'].pop(key)
            pack['images'][role]=png
    validate(pack)
    return result


def status(document,identity):
    effective=resolved(document,identity);local=node(document,identity).get('ui_art',{}).get('images',{})
    return dict(donor=effective['donor'],hd_scale=effective['hd_scale'],imported=len(local),
                roles=[dict(id=role,label=MASTERS.get(role,role.replace('_',' ')),group='All layouts' if role in MASTERS else role.rsplit('_',1)[1].upper(),
                            own=role in local,available=role in effective['images'],origin=effective['origins'].get(role,{'source':'Retail UI donor'})) for role in ROLES])
