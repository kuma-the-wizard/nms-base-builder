"""Protect history restores in scenes with asynchronously generated meshes.

Blender 5.1's incremental memfile restore can leave an object's material array
invalid after decal previews change between history steps. The UI regression
in qa/test_nmscribe_history_ui.py reproduces build_materials(null) on 18.1.53.
Use Blender's full restore only during undo/redo involving these meshes. Never
push a synthetic undo step: doing so would discard the user's redo history.
"""
import bpy
import time
from bpy.app.handlers import persistent

restoring = False
_preferences = None
_resume_at = 0.0


def history_ready():
    return not restoring and time.monotonic() >= _resume_at


def _release():
    global restoring, _preferences
    if _preferences is not None:
        developer_ui, legacy, dirty = _preferences
        prefs = bpy.context.preferences
        prefs.experimental.use_undo_legacy = legacy
        prefs.view.show_developer_ui = developer_ui
        prefs.is_dirty = dirty
        _preferences = None
    restoring = False


@persistent
def before_history(_):
    global restoring, _preferences
    if restoring:
        return
    restoring = True
    # Include unused meshes: undo can restore a decal that was just deleted.
    # This is one scan per undo/redo, with no additional idle polling.
    if not any(mesh.get('bbe_projected_decal') or mesh.get('bbe_hab_open_slots')
               for mesh in bpy.data.meshes):
        return
    prefs = bpy.context.preferences
    _preferences = (prefs.view.show_developer_ui,
                    prefs.experimental.use_undo_legacy, prefs.is_dirty)
    # Blender gates this restore path on BOTH flags. Restore both before the
    # event loop resumes, so it neither changes the UI nor saves preferences.
    prefs.view.show_developer_ui = True
    prefs.experimental.use_undo_legacy = True


@persistent
def after_history(_):
    global _resume_at
    try:
        from . import reset_curve_tracking
        reset_curve_tracking()
    finally:
        _resume_at = time.monotonic() + 1.5
        _release()


def register():
    for handlers, callback in (
            (bpy.app.handlers.undo_pre, before_history),
            (bpy.app.handlers.redo_pre, before_history),
            (bpy.app.handlers.undo_post, after_history),
            (bpy.app.handlers.redo_post, after_history),
            (bpy.app.handlers.load_post, after_history)):
        if callback not in handlers:
            handlers.append(callback)


def unregister():
    _release()
    for handlers, callback in (
            (bpy.app.handlers.undo_pre, before_history),
            (bpy.app.handlers.redo_pre, before_history),
            (bpy.app.handlers.undo_post, after_history),
            (bpy.app.handlers.redo_post, after_history),
            (bpy.app.handlers.load_post, after_history)):
        if callback in handlers:
            handlers.remove(callback)
