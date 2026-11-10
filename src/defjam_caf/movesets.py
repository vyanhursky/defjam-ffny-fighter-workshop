"""Original fighter moveset choices, identified by stable retail symbols."""
import re
from .container import SaveError

TABLE=0x4ce5b1b2
CORE=0x232d89a7
NATIVE_TO_CAF=(1,0,4,3,2)


def name_hash(value):
    result=5381
    for byte in value.encode('ascii')+b'\0':result=(result*33+byte)&0xffffffff
    return result


class Catalog:
    def __init__(self,database):
        shop=database.shop;schema=shop.mapping(shop.word(12),b'SKMA')
        if (schema.get(CORE)!=(10,2) or schema.get(TABLE^name_hash('DisplayName'))!=(5,1)
                or schema.get(TABLE^name_hash('FightingStyle'))!=(9,6)):
            raise SaveError('Unsupported original fighter moveset schema')
        candidates={}
        for _,(offset,) in database.records(TABLE):
            core=shop.word(offset+40)
            if not 1<=core<=86:continue
            symbol=shop.string(shop.word(offset));label=shop.string(shop.word(offset+20)).strip()
            key='retail/'+re.sub('[^a-z0-9]+','-',symbol.lower()).strip('-')
            mask,primary=shop.word(offset+36),shop.word(offset+72)
            native=[i for i in range(5) if mask&(1<<i)]
            if not label or not 0<mask<=31 or not native:
                raise SaveError('Unsupported original fighter style metadata')
            preferred=[i for i in native if primary&(1<<i)]
            if preferred:
                first=preferred[0];native=[first]+[i for i in native if i!=first]
            row=dict(key=key,label=label,core=core,styles=[NATIVE_TO_CAF[i] for i in native])
            before=candidates.get(core)
            if before is None or (len(key),key)<(len(before['key']),before['key']):candidates[core]=row
        self.options=sorted(candidates.values(),key=lambda row:(row['label'].casefold(),row['key']))
        self.by_key={row['key']:row for row in self.options};self.by_core={row['core']:row for row in self.options}
        if not self.options or len(self.by_key)!=len(self.options):raise SaveError('No unambiguous retail movesets found')

    def select(self,key):
        if type(key) is not str or key not in self.by_key:raise SaveError('Choose a retail fighter from the loaded moveset catalog')
        return self.by_key[key]
