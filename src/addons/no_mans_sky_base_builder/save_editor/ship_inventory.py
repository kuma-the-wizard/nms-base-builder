"""Inventory catalogue, procedural IDs and adjacency, independent of Blender."""
import json
import re
from .ship_core import RES
CATALOGUE = json.loads((RES / 'ship_inventory_catalogue.json').read_text())
if isinstance(CATALOGUE, dict):
    CATALOGUE = CATALOGUE['items']
BY_ID = {v['id']: v for v in CATALOGUE}


def base_id(identifier):
    return identifier.lstrip('^').split('#', 1)[0]


def info(item):
    return BY_ID.get(base_id(item['Id']), {})


def set_roll(item, value):
    """Only replace the suffix. Preserve charge, damage and all other fields."""
    if '#' not in item['Id'] and not info(item).get('procedural'):
        raise ValueError('This technology has no procedural roll')
    value = str(value).strip()
    if not re.fullmatch(r'[0-9]{1,5}', value):
        raise ValueError('Enter a decimal roll from 0 to 99999')
    item['Id'] = item['Id'].split('#', 1)[0] + '#' + value.zfill(5)


def allowed(entry, ship, tech):
    if not tech:
        return entry['type'] in ('Product', 'Substance')
    if entry['type'] != 'Technology':
        return False
    from .ship_core import get
    resource = get(get(ship, 'Resource', {}), 'Filename', '').upper()
    category = 'Corvette' if '/BIGGS/' in resource else 'AlienShip' if '/BIOSHIP/' in resource else 'RobotShip' if '/SENTINELSHIP/' in resource else 'Ship'
    return entry['category'] in ('AllShips', category) or (category != 'AlienShip' and entry['category'] in ('AllShipsExceptAlien','Ship'))


def make_item(entry, pos, amount=1, roll='00000'):
    capacity = capacity_for(entry)
    if not 0 <= amount <= capacity:
        raise ValueError('Quantity exceeds this item capacity')
    item = dict(Type={'InventoryType':entry['type']}, Id='^'+entry['id'], Amount=amount if entry['type'] != 'Technology' or entry.get('chargeable') else capacity,
                MaxAmount=capacity, DamageFactor=0.0, FullyInstalled=True, AddedAutomatically=False,
                Index=dict(X=pos[0],Y=pos[1]))
    if entry.get('procedural'):
        set_roll(item, roll)
    return item


def capacity_for(entry):
    """A zero StackMultiplier is an individual product, not a ten-item stack."""
    if entry['type'] == 'Technology':
        return max(1, entry['charge'])
    multiplier = entry['stack']
    return 1 if multiplier <= 0 else multiplier * (9999 if entry['type'] == 'Substance' else 10)


def required_cells(entry, amount):
    if amount < 1:
        raise ValueError('Quantity must be positive')
    capacity = capacity_for(entry)
    return (amount + capacity - 1) // capacity


def place_items(inv, entry, start, amount, roll='00000', replace=None):
    """Allocate full stacks in unlocked empty cells, starting at the chosen cell."""
    if entry['type'] == 'Technology':
        if amount > capacity_for(entry) and entry.get('chargeable'):
            raise ValueError('Charge exceeds technology capacity')
        amount = capacity_for(entry) if not entry.get('chargeable') else amount
    positions = [(x,y) for y in range(12) for x in range(10)]
    if start not in positions:
        raise ValueError('Select an inventory cell')
    positions = positions[positions.index(start):] + positions[:positions.index(start)]
    valid = {(v['X'],v['Y']) for v in inv.get('ValidSlotIndices',[])}
    occupied = {(v['Index']['X'],v['Index']['Y']) for v in inv.get('Slots',[]) if v is not replace}
    available = [p for p in positions if p in valid and p not in occupied]
    needed = required_cells(entry, amount)
    if len(available) < needed:
        raise ValueError(f'{needed} unlocked empty slots are needed; only {len(available)} available')
    if replace is not None:
        inv['Slots'].remove(replace)
    cap = capacity_for(entry)
    for pos in available[:needed]:
        count = min(cap, amount)
        inv['Slots'].append(make_item(entry,pos,count,roll))
        amount -= count
    return needed


def links(inv):
    """Only orthogonally touching, installed, same-family technologies link."""
    cells = {}
    for item in inv.get('Slots', []):
        data = info(item)
        if item.get('Type',{}).get('InventoryType') != 'Technology' or not item.get('FullyInstalled',True) or item.get('DamageFactor',0) > 0:
            continue
        family = data.get('family')
        if not family or family in ('Ship','AllShips','AlienShip','RobotShip','Corvette'):
            continue
        cells[(item['Index']['X'],item['Index']['Y'])] = data
    return {p: d for p,d in cells.items() if any(cells.get((p[0]+x,p[1]+y),{}).get('family') == d['family'] for x,y in ((0,1),(0,-1),(1,0),(-1,0)))}


def known_rolls(root, identifier):
    from . import ship_core as c
    wanted = base_id(identifier)
    result = set()
    for ctx in c.contexts(root):
        for ship in c.ships(root,ctx):
            for container in ('Inventory','Inventory_TechOnly','Inventory_Cargo'):
                for item in c.translate(c.get(ship,container,{})).get('Slots',[]):
                    value=item.get('Id','')
                    if base_id(value)==wanted and '#' in value:
                        result.add(value.split('#',1)[1])
    return sorted(result)
