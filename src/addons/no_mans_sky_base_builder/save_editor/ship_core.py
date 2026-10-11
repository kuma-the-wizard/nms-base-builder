"""Ship operations on isolated save drafts. No Blender or file writes here."""
import copy
import json
from pathlib import Path

RES = Path(__file__).parents[1] / 'resources'
KEYS = json.loads((RES / 'ship_management_keys.json').read_text())
CUSTOM_SLOTS = (3, 4, 5, 6, 7, 8, 17, 18, 19, 20, 21, 22)


def key(obj, name):
    return name if name in obj else KEYS.get(name, name)


def get(obj, name, default=None):
    return obj.get(key(obj, name), default)


def put(obj, name, value):
    obj[key(obj, name)] = value


def translate(value, english=True):
    mapping = {v: k for k, v in KEYS.items()} if english else KEYS
    if isinstance(value, dict):
        return {mapping.get(k, k): translate(v, english) for k, v in value.items()}
    if isinstance(value, list):
        return [translate(v, english) for v in value]
    return value


def contexts(root):
    return [c for c in ('Main', 'Season') if get(get(root, 'BaseContext' if c == 'Main' else 'ExpeditionContext', {}), 'PlayerStateData')]


def player(root, context):
    if context not in ('Main', 'Season'):
        raise ValueError('Choose Main or Expedition')
    p = get(get(root, 'BaseContext' if context == 'Main' else 'ExpeditionContext', {}), 'PlayerStateData')
    if not isinstance(p, dict):
        raise ValueError('This save has no data for the selected context')
    return p


def ships(root, context):
    values = get(player(root, context), 'ShipOwnership', [])
    if len(values) != 12:
        raise ValueError('Expected 12 ship slots; this save format is not supported')
    return values


def occupied(ship):
    return bool(get(get(ship, 'Resource', {}), 'Filename', '').strip())


def corvette(ship):
    return '/BIGGS/' in get(get(ship, 'Resource', {}), 'Filename', '').upper()


def kind(base):
    return get(get(base, 'BaseType', {}), 'PersistentBaseTypes', '')


def validate_links(root, context):
    owned = ships(root, context)
    seen = set()
    for base in get(player(root, context), 'PersistentPlayerBases', []):
        if kind(base) != 'PlayerShipBase':
            continue
        index = get(base, 'UserData')
        if type(index) is not int or not 0 <= index < 12 or index in seen or not corvette(owned[index]):
            raise ValueError('Corvette ownership links are ambiguous or broken; no changes were saved')
        seen.add(index)
    if any(corvette(s) and i not in seen for i, s in enumerate(owned)):
        raise ValueError('A Corvette is missing its build; no changes were saved')


def reorder(root, context, order):
    if sorted(order) != list(range(12)):
        raise ValueError('Ship order must contain each of the 12 slots exactly once')
    validate_links(root, context)
    p = player(root, context)
    old = copy.deepcopy(ships(root, context))
    inverse = {old_index: new_index for new_index, old_index in enumerate(order)}
    put(p, 'ShipOwnership', [old[i] for i in order])
    for base in get(p, 'PersistentPlayerBases', []):
        if kind(base) == 'PlayerShipBase':
            put(base, 'UserData', inverse[get(base, 'UserData')])
    # These arrays use slot numbers; cosmetic indices have a gap for vehicles.
    custom = get(p, 'CharacterCustomisationData', [])
    if custom:
        if len(custom) <= max(CUSTOM_SLOTS):
            raise ValueError('Unknown ship customisation layout')
        before = copy.deepcopy(custom)
        for new, old_index in enumerate(order):
            custom[CUSTOM_SLOTS[new]] = before[CUSTOM_SLOTS[old_index]]
    legacy = get(p, 'ShipUsesLegacyColours', [])
    if legacy:
        if len(legacy) != 12:
            raise ValueError('Unknown legacy colour layout')
        put(p, 'ShipUsesLegacyColours', [legacy[i] for i in order])
    for field in ('PrimaryShip', 'CorvetteEditAssociatedShipIndex'):
        old_index = get(p, field)
        if old_index in inverse:
            put(p, field, inverse[old_index])
    validate_links(root, context)


def add_minimal(root, context, index, name):
    validate_links(root, context)
    owned = ships(root, context)
    if not 0 <= index < 12 or occupied(owned[index]):
        raise ValueError('Select an EMPTY ship slot')
    if not name.strip():
        raise ValueError('Give the new Corvette a name')
    template = json.loads((RES / 'minimal_corvette.json').read_text())
    p = player(root, context)
    raw = 'ShipOwnership' not in p
    ship = translate(template['ship'], False) if raw else template['ship']
    base = translate(template['base'], False) if raw else template['base']
    put(ship, 'Name', name.strip())
    put(base, 'Name', name.strip())
    put(base, 'UserData', index)
    owned[index] = ship
    get(p, 'PersistentPlayerBases').append(base)
    custom = get(p, 'CharacterCustomisationData', [])
    if len(custom) > CUSTOM_SLOTS[index]:
        blank = template['custom']
        custom[CUSTOM_SLOTS[index]] = translate(blank, False) if raw else blank
    legacy = get(p, 'ShipUsesLegacyColours', [])
    if len(legacy) == 12:
        legacy[index] = False
    validate_links(root, context)


def default_keep(root, context):
    owned = ships(root, context)
    # A normal starship needs zero base parts, making it ideal for a clean copy.
    choices = [i for i, ship in enumerate(owned) if occupied(ship) and not corvette(ship)]
    active = get(player(root, context), 'PrimaryShip', 0)
    return active if active in choices else (choices[0] if choices else active)


def clean_copy(root, name, keep_ships, keep_bases):
    if not name.strip() or len(name.encode('utf8')) > 127:
        raise ValueError('Save name must contain 1–127 UTF-8 bytes')
    out = copy.deepcopy(root)
    for context in contexts(out):
        p = player(out, context)
        owned = ships(out, context)
        keep = set(keep_ships.get(context, []))
        available = {i for i, s in enumerate(owned) if occupied(s)}
        if available and (not keep or not keep <= available):
            raise ValueError('Keep at least one owned ship in each populated context')
        validate_links(out, context)
        bases = get(p, 'PersistentPlayerBases', [])
        retained = []
        for i, base in enumerate(bases):
            retain = get(base, 'UserData') in keep if kind(base) == 'PlayerShipBase' else i in keep_bases.get(context, [])
            if retain:
                retained.append(base)
        put(p, 'PersistentPlayerBases', retained)
        put(p, 'BaseBuildingObjects', [])
        template = json.loads((RES / 'minimal_corvette.json').read_text())
        for index in available - keep:
            blank = copy.deepcopy(template['empty'])
            owned[index] = translate(blank, False) if 'ShipOwnership' not in p else blank
        if keep:
            old_active = get(p, 'PrimaryShip', 0)
            active = old_active if old_active in keep else min(keep)
            put(p, 'PrimaryShip', active)
            ship = owned[active]
            put(p, 'CurrentShip', copy.deepcopy(get(ship, 'Resource')))
            put(p, 'ShipInventory', copy.deepcopy(get(ship, 'Inventory')))
            put(p, 'ShipLayout', copy.deepcopy(get(ship, 'InventoryLayout')))
            # The source may have been saved inside a now-removed Corvette/base.
            ctx = get(out, 'BaseContext' if context == 'Main' else 'ExpeditionContext')
            spawn = get(ctx, 'SpawnStateData', {})
            if spawn and (old_active != active or not corvette(ship)):
                put(spawn, 'LastKnownPlayerState', 'InShipLanded' if 'Landed' in str(get(spawn, 'LastKnownPlayerState', '')) or get(spawn, 'LastKnownPlayerState') == 'OnFoot' else 'InShip')
                for target, source in (('PlayerPositionInSystem','ShipPositionInSystem'),('PlayerTransformAt','ShipTransformAt')):
                    if get(spawn, source) is not None:
                        put(spawn, target, copy.deepcopy(get(spawn, source)))
            edit = get(p, 'CorvetteEditAssociatedShipIndex')
            if edit is not None and edit not in keep:
                put(p, 'CorvetteEditAssociatedShipIndex', -1)
        # SaveName is stored in common metadata, not necessarily PlayerStateData.
        validate_links(out, context)
    def rename(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ('SaveName', KEYS['SaveName']):
                    node[k] = name.strip()
                else:
                    rename(v)
        elif isinstance(node, list):
            for v in node:
                rename(v)
    rename(out)
    return out


def inventory(root, context, index, container):
    if container not in ('Inventory', 'Inventory_TechOnly', 'Inventory_Cargo'):
        raise ValueError('Invalid inventory')
    return translate(get(ships(root, context)[index], container, {}))


def validate_inventory(inv):
    width, height = inv.get('Width', 0), inv.get('Height', 0)
    if not 1 <= width <= 10 or not 1 <= height <= 12:
        raise ValueError('Unknown inventory dimensions')
    def cell(v):
        x, y = v.get('X'), v.get('Y')
        if type(x) is not int or type(y) is not int or not (0 <= x < 10 and 0 <= y < 12):
            raise ValueError('Inventory cell is out of bounds')
        return x, y
    unlocked = [cell(v) for v in inv.get('ValidSlotIndices', [])]
    if len(unlocked) != len(set(unlocked)):
        raise ValueError('Repeated unlocked cell')
    used = set()
    for item in inv.get('Slots', []):
        pos = cell(item['Index'])
        if pos not in unlocked or pos in used:
            raise ValueError('An item is in a locked or occupied cell')
        used.add(pos)
        if not -1 <= item['Amount'] <= item['MaxAmount']:
            raise ValueError('Amount exceeds the stack/charge capacity')
    for special in inv.get('SpecialSlots', []):
        cell(special['Index'])  # The game stores dormant special cells before they are unlocked.


def set_inventory(root, context, index, container, inv):
    validate_inventory(inv)
    ship = ships(root, context)[index]
    put(ship, container, copy.deepcopy(inv) if container in ship else translate(inv, False))


def unlock(inv, tech=False):
    inv['Width'], inv['Height'] = 10, (6 if tech else 12)
    inv['ValidSlotIndices'] = [{'X': x, 'Y': y} for y in range(inv['Height']) for x in range(10)]


def move_item(inv, start, end):
    if start == end:
        return
    valid = {(v['X'], v['Y']) for v in inv['ValidSlotIndices']}
    if end not in valid:
        raise ValueError('Unlock the destination cell first')
    for item in inv['Slots']:
        pos = (item['Index']['X'], item['Index']['Y'])
        if pos == start or pos == end:
            target = end if pos == start else start
            item['Index'] = dict(X=target[0], Y=target[1])


def move_supercharge(inv, pos, target):
    """Move one existing bonus cell; never add or delete one."""
    valid = {(v['X'], v['Y']) for v in inv['ValidSlotIndices']}
    if target not in valid:
        raise ValueError('Unlock the destination cell first')
    entries = inv.get('SpecialSlots', [])
    start = dict(X=pos[0],Y=pos[1]); end = dict(X=target[0],Y=target[1])
    found = next((v for v in entries if v['Index']==start and v['Type']['InventorySpecialSlotType']=='TechBonus'),None)
    if found is None:
        raise ValueError('Choose an existing hyperslot to move')
    if pos == target:
        return
    if any(v['Index']==end for v in entries):
        raise ValueError('Destination already has a special slot')
    found['Index'] = end


def set_class(root, context, index, value):
    if value not in ('C','B','A','S'):
        raise ValueError('Choose C, B, A or S class')
    ship=ships(root,context)[index]
    if not occupied(ship):
        raise ValueError('Select an owned ship')
    for container in ('Inventory','Inventory_TechOnly','Inventory_Cargo'):
        inv=get(ship,container)
        if not inv:continue
        current=get(inv,'Class')
        if not isinstance(current,dict):raise ValueError('Unknown inventory class layout')
        put(current,'InventoryClass',value)
