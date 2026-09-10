"""Compact the station Outliner once after import or reference refresh."""
import bpy


def compact_window(window, rim):
    """Open only the path to the shared rim: Reference > Outside.

    Show Active opens the object's ancestors, leaving the object itself closed.
    It uses the view layer's active object, so restore that without touching
    selection or the active collection used to route new player parts.
    """
    view_layer = window.view_layer
    if rim.name not in view_layer.objects:
        return True
    original_active = view_layer.objects.active
    complete = True
    try:
        view_layer.objects.active = rim
        for area in window.screen.areas:
            if area.type != 'OUTLINER' or area.spaces.active.display_mode != 'VIEW_LAYER':
                continue
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            if region is None:
                continue
            with bpy.context.temp_override(window=window, area=area, region=region):
                # A filtered or not-yet-drawn tree may not contain the rim.
                # Leave that tree alone until Show Active can find it.
                if bpy.ops.outliner.show_active() != {'FINISHED'}:
                    complete = False
                    continue
                # Collapse data, objects and collections, then open only the rim's ancestors.
                for _ in range(32):
                    bpy.ops.outliner.show_one_level(open=False)
                complete &= bpy.ops.outliner.show_active() == {'FINISHED'}
            area.tag_redraw()
    finally:
        view_layer.objects.active = original_active
    return complete


def schedule(context, root):
    """Wait for Blender to draw the newly created tree; never run on file load."""
    if bpy.app.background:
        return
    scene = context.scene
    attempts = 0

    def apply():
        nonlocal attempts
        attempts += 1
        try:
            if root.name not in scene.collection.children:
                return None
            rim = next((o for o in root.all_objects if o.get('station_part_key') == 'entrance-rim'), None)
            if rim is None:
                return None
            complete = True
            for window in bpy.context.window_manager.windows:
                if window.scene == scene:
                    complete &= compact_window(window, rim)
            return None if complete or attempts >= 5 else 0.2
        except ReferenceError:
            # The user opened another file or removed the station before the timer ran.
            return None

    bpy.app.timers.register(apply, first_interval=0.2)
