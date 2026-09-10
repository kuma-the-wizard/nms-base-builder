"""Direct eye toggles for complete hull families and their large attachments."""
import json
import bpy

def capture(context):
    from . import station_reference as ref
    state={'objects':{},'families':{}}
    for layer in context.view_layer.layer_collection.children:
        if not layer.collection.get(ref.TAG):continue
        for child in layer.children:
            if child.collection.name!='Outside':continue
            state['outsideHidden']=child.hide_viewport
            for family in child.children:
                key=family.collection.get('station_family')
                if key:state['families'][key]=family.hide_viewport
        for obj in layer.collection.all_objects:
            key=obj.get('station_part_key')
            if key:state['objects'][key]=obj.hide_get()
    return state

def assemble(context,choices,visibility=None):
    from .station_cached_reference import assemble as assemble_cached
    return assemble_cached(context,choices,visibility)


def assemble_from_source(context,choices,visibility=None):
    """Offline reference builder; normal station imports use the prebuilt library."""
    from . import station_reference as ref
    data=ref.catalog(); loaded=[]; root=None
    previous=capture(context)
    state=visibility if isinstance(visibility,dict) else previous
    previous_sections={}
    for c in context.scene.collection.children:
        if c.get(ref.TAG):
            previous_sections.update({o.get('station_section',o.name):(o.hide_get(),o.hide_render)
                for o in c.all_objects if not o.get('station_part_key')})
    rows={r['name']:r for r in data['objects']+data['entranceRim']}
    for part in data['outsideParts']:
        rows.update({r['name']:r for r in part['rows']})
    try:
        with bpy.data.libraries.load(str(ref.ASSETS/'station_geometry.blend'),link=False) as (source,target):
            if set(rows)-set(source.objects):raise ValueError('Station library does not match its catalog')
            target.objects=list(rows)
        loaded=target.objects; by_name=dict(zip(rows,loaded))
        def mesh_for(selected,name):
            return ref.join_geometry([(by_name[r['name']],r['matrix']) for r in selected],name)
        root=ref.collection('Station Reference - preparing',context.scene.collection)
        exterior=ref.collection('Outside',root); interior=ref.collection('Inside',root)
        families={}
        for index,(family,label,_) in enumerate(ref.FAMILIES):
            c=ref.collection(f'{index+1:02d} {label}',exterior)
            c['station_family']=family;c['station_label']=f'{index+1:02d} {label}'
            families[family]=c
        for part in data['outsideParts']:
            obj=ref.make_object(mesh_for(part['rows'],part['name']),part['name'],families[part['family']])
            obj['station_part_key']=part['key'];obj['station_body']=part['body']
            hidden=state.get('objects',{}).get(part['key'],not part['defaultVisible'])
            obj.hide_set(hidden);obj.hide_render=hidden
        if data['entranceRim']:
            rim=ref.make_object(mesh_for(data['entranceRim'],'Entrance rim'),'Entrance rim',exterior)
            rim['station_part_key']='entrance-rim'
            rim.hide_set(state.get('objects',{}).get('entrance-rim',False))
        audit=ref.split_inside(mesh_for(data['objects'],'Station interior'),interior)
        root['partition_audit']=json.dumps(audit)
        root['appearance_choices']=json.dumps(choices)
        root['appearance_source']='Manual Outliner visibility; procedural seed not decoded'
        root['reference_mode']=data['referenceMode'];root['reference_version']=4
        for c in list(context.scene.collection.children):
            if c!=root and c.get(ref.TAG):ref.remove_tree(c)
        root.name='Station Reference';exterior.name='Outside';interior.name='Inside'
        for c in families.values():c.name=c['station_label']
        for obj in interior.objects:
            if obj['station_section'] in previous_sections:
                hidden,render_hidden=previous_sections[obj['station_section']]
                obj.hide_set(hidden);obj.hide_render=render_hidden
        context.view_layer.update()
        layer=next(c for c in context.view_layer.layer_collection.children if c.collection==root)
        outside=next(c for c in layer.children if c.collection==exterior)
        outside.hide_viewport=state.get('outsideHidden',True)
        selected_family=choices.get(data['familyGroup'],'_Type_Tet')
        for lc in outside.children:
            family=lc.collection['station_family']
            hidden=state.get('families',{}).get(family,family!=selected_family)
            lc.hide_viewport=hidden;lc.collection.hide_render=hidden
        from .station_tree_view import schedule
        schedule(context,root)
        return root
    except Exception:
        if root:ref.remove_tree(root);root=None
        raise
    finally:
        meshes={o.data for o in loaded if o}
        bpy.data.batch_remove(ids={o for o in loaded if o})
        bpy.data.batch_remove(ids={m for m in meshes if not m.users})
        if root:
            for obj in root.all_objects:obj.name=obj['station_section']
