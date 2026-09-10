"""Supplement the installed catalog with native Cosmos station part geometry."""
from pathlib import Path
import bpy
IDS=frozenset({'STACONNECT','STATION_CORE','STATION_LSHELVE','STATION_SERVR','STA_HOLO3D','STA_SMALLSIGN','U_PARAGON'})
def load(object_id):
    if object_id not in IDS: return None
    path=Path(__file__).resolve().parents[1]/'resources/station/station_parts.blend'
    with bpy.data.libraries.load(str(path),link=False) as (source,target):
        target.objects=['StationPart::'+object_id]
    obj=target.objects[0]
    if obj is None: raise ValueError('Missing station part asset: '+object_id)
    obj.name=object_id
    return obj
