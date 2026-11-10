"""Verified retail CAF facial selectors; no custom geometry in Story saves."""
from .container import SaveError

FIELDS=(('face','Face type',5,None),('eyes','Eye shape',6,541),
        ('eye_color','Eye color',7,542),('eyebrows','Eyebrow shape',8,551),
        ('nose','Nose shape',9,561),('lips','Lip shape',10,571),('ears','Ear shape',11,581))


def catalog(cache):
    resources=cache.catalog['resources'];objects=cache.catalog['objects'];result=[]
    for key,label,slot,prefix in FIELDS:
        options=[]
        for value in range(1,9):
            if key=='face':
                available='v2cp_532_0004_c' in objects
            elif slot in (7,8):
                available=f'v2cp_{prefix}_{value:04}_a01_01' in resources
            elif value==1:
                available=True
            else:
                native=2 if slot==11 and value==4 else value
                available=f'v2cp_{prefix}_{native:04}_c' in objects
                if slot!=11 or native%2:
                    available=available and f'v2cp_{prefix}_{native:04}_a01_01' in resources
            if available:
                name=f'{label} {value}'
                if slot in (6,9,10,11) and value==1:name='Default · 1'
                if slot==11 and value==4:name='Ear preset 4 · original alias of 2'
                options.append({'value':value,'label':name})
        result.append({'id':key,'label':label,'slot':slot,'options':options})
    palettes=resources.get('v2cp_551_0001_a01_01',{}).get('palettes',[])
    colors=[{'value':i,'label':f'Shade {i+1}'} for i in range(36) if f'pl{i+1:02}' in palettes]
    result.append({'id':'brow_color','label':'Eyebrow color','slot':8,'color':True,'options':colors})
    return result


def selected(fields, choices):
    return [dict(row,value=fields['caf_colors' if row.get('color') else 'caf_values'][row['slot']]) for row in choices]


def change(fields,changes,choices):
    values=fields['caf_values'][:];colors=fields['caf_colors'][:]
    for row in choices:
        key=row['id']
        if key not in changes:continue
        value=changes[key]
        if type(value) is not int or value not in {item['value'] for item in row['options']}:
            raise SaveError('Choose a supported original '+row['label'].lower()+' preset')
        (colors if row.get('color') else values)[row['slot']]=value
    return values,colors
