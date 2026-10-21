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
_curve_reseed_pending = False


def history_ready():
    return not restoring and time.monotonic() >= _resume_at


def curve_tracking_ready():
    return history_ready() and not _curve_reseed_pending


def _reseed_curves_when_idle():
    """Read restored Blender IDs only after the undo callback has returned."""
    global _curve_reseed_pending
    if not _curve_reseed_pending:
        return None
    if not history_ready():
        return max(.1, _resume_at - time.monotonic())
    from . import reset_curve_tracking
    try:
        reset_curve_tracking()
    except (ReferenceError, RuntimeError):
        # A new restore can invalidate an RNA wrapper while the timer is due.
        return .25
    _curve_reseed_pending = False
    return None


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
    global _resume_at, _curve_reseed_pending
    try:
        _curve_reseed_pending = True
        _resume_at = time.monotonic() + 1.5
        if not bpy.app.timers.is_registered(_reseed_curves_when_idle):
            bpy.app.timers.register(_reseed_curves_when_idle, first_interval=1.5)
    finally:
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
    global _curve_reseed_pending
    _curve_reseed_pending = False
    if bpy.app.timers.is_registered(_reseed_curves_when_idle):
        bpy.app.timers.unregister(_reseed_curves_when_idle)
    _release()
    for handlers, callback in (
            (bpy.app.handlers.undo_pre, before_history),
            (bpy.app.handlers.redo_pre, before_history),
            (bpy.app.handlers.undo_post, after_history),
            (bpy.app.handlers.redo_post, after_history),
            (bpy.app.handlers.load_post, after_history)):
        if callback in handlers:
            handlers.remove(callback)
