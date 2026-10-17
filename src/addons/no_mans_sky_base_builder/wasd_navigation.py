"""Optional, viewport-only RMB/WASD navigation. No scene or camera mutations."""
import math
import sys
import time

import bpy
from bpy.app.handlers import persistent
from mathutils import Quaternion, Vector

_keymaps = []
_active = None
_resources = None
MOVEMENT = {'W', 'A', 'S', 'D', 'Q', 'E', 'UP_ARROW', 'DOWN_ARROW', 'LEFT_ARROW', 'RIGHT_ARROW'}
CONTEXT_MENUS = {'OBJECT': 'VIEW3D_MT_object_context_menu', 'EDIT_MESH': 'VIEW3D_MT_edit_mesh_context_menu'}
# These long-lived browser listeners pass through events outside their grid.
# Their presence in a window does not mean the viewport is being edited.
PASSIVE_LISTENERS = {'BBE_OT_asset_grid', 'BBE_OT_sidebar_asset_grid'}


def input_is_owned(context):
    return any(operator.bl_idname not in PASSIVE_LISTENERS
               for operator in getattr(context.window, 'modal_operators', ()))


def preferences(context):
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon else None


def direction(keys, rotation):
    """Normalized view-relative travel with world-vertical Q/E."""
    x = int(bool(keys & {'D', 'RIGHT_ARROW'})) - int(bool(keys & {'A', 'LEFT_ARROW'}))
    z = int(bool(keys & {'S', 'DOWN_ARROW'})) - int(bool(keys & {'W', 'UP_ARROW'}))
    vertical = int('E' in keys) - int('Q' in keys)
    value = rotation @ Vector((x, 0, z)) + Vector((0, 0, vertical))
    return value.normalized() if value.length_squared else value


def draw_controls(layout, context):
    prefs = preferences(context)
    if prefs is None:
        return
    col = layout.column(align=True)
    col.prop(prefs, 'bbe_wasd_enabled', text='WASD Navigation', toggle=True, icon='ORIENTATION_VIEW')
    if prefs.bbe_wasd_enabled:
        from .save_editor.function_help import help_button
        help_button(col, 'NAVIGATION')
        col.label(text='Hold right mouse: look + WASD', icon='MOUSE_RMB')
        col.label(text='Q/E: down/up · Shift: fast · Ctrl: slow')
        col.prop(prefs, 'bbe_wasd_speed', text='Speed')
        col.prop(prefs, 'bbe_wasd_sensitivity', text='Look sensitivity')


def settings_changed(self, context):
    if not self.bbe_wasd_enabled:
        stop()


def stop():
    global _active
    if _active is not None:
        try:
            _active.finish()
        except ReferenceError:
            _active = None
            cleanup()


def cleanup():
    global _resources
    resources, _resources = _resources, None
    if resources is None:
        return
    wm, timer, window, area = resources
    for release in (lambda: wm.event_timer_remove(timer), lambda: window.cursor_modal_restore(),
                    lambda: area.header_text_set(None), lambda: area.tag_redraw()):
        try:
            release()
        except (ReferenceError, RuntimeError):
            pass


@persistent
def before_load(_):
    stop()


class BBE_OT_wasd_navigation(bpy.types.Operator):
    bl_idname = 'bbe.wasd_navigation'
    bl_label = 'BBE WASD Navigation'
    bl_description = 'Hold right mouse to look; WASD moves, Q/E moves vertically, wheel changes speed'
    bl_options = {'BLOCKING', 'GRAB_CURSOR'}

    @classmethod
    def poll(cls, context):
        prefs = preferences(context)
        return bool(prefs and prefs.bbe_wasd_enabled and _active is None
                    and context.area and context.area.type == 'VIEW_3D'
                    and context.region and context.region.type == 'WINDOW'
                    and context.region_data and context.mode in CONTEXT_MENUS)

    def invoke(self, context, event):
        global _active, _resources
        if not self.poll(context) or event.type != 'RIGHTMOUSE':
            return {'PASS_THROUGH'}
        # A controller / placement / transform session owns its input until it ends.
        if input_is_owned(context):
            return {'PASS_THROUGH'}
        for name, module in tuple(sys.modules.items()):
            if name.endswith('bbe_controller_companion') and getattr(module, '_session', None) is not None:
                return {'PASS_THROUGH'}
        select_mouse = getattr(getattr(context.window_manager.keyconfigs.active, 'preferences', None), 'select_mouse', 'LEFT')
        if select_mouse == 'RIGHT':
            self.report({'WARNING'}, 'WASD right-mouse navigation requires left-click selection in Blender Preferences')
            return {'PASS_THROUGH'}
        self._wm, self._window, self._area = context.window_manager, context.window, context.area
        self._region, self._view = context.region, context.region_data
        self._keys, self._moved, self._finished = set(), False, False
        self._shift, self._ctrl = False, False
        self._origin = (event.mouse_x, event.mouse_y)
        self._last_tick = time.monotonic()
        self._speed = preferences(context).bbe_wasd_speed
        self._timer = self._wm.event_timer_add(1 / 60, window=self._window)
        _resources = (self._wm, self._timer, self._window, self._area)
        self._window.cursor_modal_set('SCROLL_XY')
        _active = self
        self._wm.modal_handler_add(self)
        self._area.header_text_set('WASD: move | Q/E: down/up | Shift: fast | Ctrl: slow | Wheel: speed | Release RMB / Esc: stop')
        return {'RUNNING_MODAL'}

    def start_motion(self):
        if not self._moved:
            # Leave camera view, without moving or keyframing the camera object.
            self._view.view_perspective = 'PERSP'
            self._moved = True

    def finish(self):
        global _active
        if getattr(self, '_finished', True):
            return
        self._finished = True
        self._keys.clear()
        cleanup()
        if _active is self:
            _active = None

    def modal(self, context, event):
        if self._finished:
            return {'CANCELLED'}
        try:
            prefs = preferences(context)
            if (not prefs or not prefs.bbe_wasd_enabled or context.window != self._window
                    or self._area.type != 'VIEW_3D' or context.mode not in CONTEXT_MENUS
                    or event.type in {'ESC', 'WINDOW_DEACTIVATE'}):
                self.finish()
                return {'FINISHED'}
            if event.type == 'RIGHTMOUSE' and event.value == 'RELEASE':
                menu = CONTEXT_MENUS.get(context.mode) if not self._moved else None
                self.finish()
                if menu:
                    bpy.ops.wm.call_menu('INVOKE_DEFAULT', name=menu)
                return {'FINISHED'}
            self._shift, self._ctrl = event.shift, event.ctrl
            if event.type in MOVEMENT:
                if event.value == 'PRESS':
                    self.start_motion()
                    self._keys.add(event.type)
                elif event.value == 'RELEASE':
                    self._keys.discard(event.type)
                return {'RUNNING_MODAL'}
            if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
                self.start_motion()
                self._speed = max(.01, min(10000, self._speed * (1.25 if event.type == 'WHEELUPMOUSE' else .8)))
                prefs.bbe_wasd_speed = self._speed
            elif event.type == 'MOUSEMOVE':
                if not self._moved and math.hypot(event.mouse_x-self._origin[0], event.mouse_y-self._origin[1]) < 4:
                    return {'RUNNING_MODAL'}
                self.start_motion()
                view = self._view
                distance = max(.01, view.view_distance)
                eye = view.view_location + view.view_rotation @ Vector((0, 0, distance))
                dx = event.mouse_x-event.mouse_prev_x
                dy = event.mouse_y-event.mouse_prev_y
                sensitivity = prefs.bbe_wasd_sensitivity * .002
                rotation = Quaternion((0, 0, 1), -dx*sensitivity) @ view.view_rotation
                candidate = rotation @ Quaternion((1, 0, 0), dy*sensitivity)
                # Keep a small margin from the poles so yaw remains predictable.
                if abs((candidate @ Vector((0, 0, -1))).z) < .9998:
                    rotation = candidate
                view.view_rotation = rotation.normalized()
                view.view_location = eye - view.view_rotation @ Vector((0, 0, distance))
            elif event.type == 'TIMER':
                now = time.monotonic()
                dt = min(.1, max(0, now-self._last_tick))
                self._last_tick = now
                if self._keys:
                    multiplier = (4 if self._shift else 1) * (.25 if self._ctrl else 1)
                    self._view.view_location += direction(self._keys, self._view.view_rotation) * self._speed * multiplier * dt
            self._area.tag_redraw()
            return {'RUNNING_MODAL'}
        except Exception as exc:
            self.finish()
            self.report({'WARNING'}, f'WASD navigation stopped: {exc}')
            return {'CANCELLED'}

    def cancel(self, context):
        self.finish()


def register():
    bpy.utils.register_class(BBE_OT_wasd_navigation)
    config = bpy.context.window_manager.keyconfigs.addon
    if config:
        # Mode keymaps run before the generic 3D View context-menu binding.
        for name in ('Object Mode', 'Mesh'):
            km = config.keymaps.new(name=name, space_type='EMPTY', region_type='WINDOW')
            item = km.keymap_items.new(BBE_OT_wasd_navigation.bl_idname, 'RIGHTMOUSE', 'PRESS', head=True)
            _keymaps.append((km, item))
    if before_load not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(before_load)


def unregister():
    stop()
    if before_load in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(before_load)
    for km, item in _keymaps:
        km.keymap_items.remove(item)
    _keymaps.clear()
    bpy.utils.unregister_class(BBE_OT_wasd_navigation)
