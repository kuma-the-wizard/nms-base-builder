"""Configurable NMS menus in the Viewport's second (tool header) row."""

import bpy
from bpy.app.handlers import persistent

from .base_builder_menu_presentation import (
    VIEW3D_PT_nms_base_builder, VIEW3D_PT_nms_io_panel, TOOLBAR_GROUPS,
)
from .. import icons

TOOLBAR_ITEMS = (
    ('proxies', 'BBE', VIEW3D_PT_nms_base_builder.bl_idname, 'MESH_MONKEY'),
    ('io', 'I/O', VIEW3D_PT_nms_io_panel.bl_idname, 'IMPORT'),
    ('color', 'Color', 'VIEW3D_PT_bbe_toolbar_color', 'COLOR'),
    ('builder', 'Builder', 'VIEW3D_PT_bbe_toolbar_builder_tools', 'TOOL_SETTINGS'),
    ('transform', 'Transform', 'VIEW3D_PT_bbe_toolbar_transform', 'ORIENTATION_GIMBAL'),
    ('batch', 'Batch', 'VIEW3D_PT_bbe_toolbar_batch', 'MOD_ARRAY'),
    ('parts', 'Prefabs', 'VIEW3D_PT_bbe_toolbar_parts', 'ASSET_MANAGER'),
    ('cables', 'Logic', 'VIEW3D_PT_bbe_toolbar_cables', 'CURVE_PATH'),
    ('lighting', 'Lighting', 'VIEW3D_PT_bbe_toolbar_lighting', 'LIGHT'),
)
_ITEMS = {item[0]: item for item in TOOLBAR_ITEMS}
_enabled = False
_original_visibility = {}
_original_tool_settings = None


def _preferences(context):
    addon = context.preferences.addons.get(__package__.rsplit('.', 1)[0])
    return addon.preferences if addon else None


def toolbar_state(context):
    prefs = _preferences(context)
    order = []
    for key in (prefs.bbe_toolbar_order.split(',') if prefs else []):
        if key in _ITEMS and key not in order:
            order.append(key)
    order.extend(key for key in _ITEMS if key not in order)
    hidden = set(prefs.bbe_toolbar_hidden.split(',')) & _ITEMS.keys() if prefs else set()
    return order, hidden


def _redraw(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


class BBE_OT_toolbar_menu(bpy.types.Operator):
    bl_idname = 'bbe.toolbar_menu'
    bl_label = 'Customize Toolbar'
    bl_description = 'Show, hide, or move a menu in the Base Builder toolbar'
    bl_options = {'INTERNAL'}

    menu: bpy.props.StringProperty()
    action: bpy.props.EnumProperty(items=[
        ('TOGGLE', 'Show / Hide', 'Toggle this menu'),
        ('UP', 'Move Left', 'Move this menu one position to the left'),
        ('DOWN', 'Move Right', 'Move this menu one position to the right'),
        ('RESET', 'Reset', 'Restore the default menu order and visibility'),
    ])

    @classmethod
    def description(cls, context, properties):
        label = _ITEMS.get(properties.menu, ('', 'Menu'))[1]
        return {
            'TOGGLE': 'Show or hide ' + label,
            'UP': 'Move ' + label + ' left in the toolbar',
            'DOWN': 'Move ' + label + ' right in the toolbar',
            'RESET': 'Restore all menus in their default order',
        }.get(properties.action, cls.bl_description)

    def execute(self, context):
        prefs = _preferences(context)
        if prefs is None:
            return {'CANCELLED'}
        order, hidden = toolbar_state(context)
        if self.action == 'RESET':
            order, hidden = list(_ITEMS), set()
        elif self.menu not in _ITEMS:
            return {'CANCELLED'}
        elif self.action == 'TOGGLE':
            hidden.symmetric_difference_update({self.menu})
        else:
            index = order.index(self.menu)
            target = index + (-1 if self.action == 'UP' else 1)
            if 0 <= target < len(order):
                order[index], order[target] = order[target], order[index]
        prefs.bbe_toolbar_order = ','.join(order)
        prefs.bbe_toolbar_hidden = ','.join(key for key in order if key in hidden)
        _redraw(context)
        return {'FINISHED'}


def draw_toolbar_settings(layout, context):
    layout.label(text='Toolbar Menus')
    layout.label(text='Checked menus are visible. Arrows change their order.')
    order, hidden = toolbar_state(context)
    for index, key in enumerate(order):
        row = layout.row(align=True)
        _, label, _, icon = _ITEMS[key]
        op = row.operator('bbe.toolbar_menu', text='',
                          icon='CHECKBOX_DEHLT' if key in hidden else 'CHECKBOX_HLT')
        op.menu, op.action = key, 'TOGGLE'
        row.label(text=label, icon=icon)
        for action, arrow, available in (
            ('UP', 'TRIA_UP', index > 0),
            ('DOWN', 'TRIA_DOWN', index < len(order) - 1),
        ):
            move = row.row(align=True)
            move.enabled = available
            op = move.operator('bbe.toolbar_menu', text='', icon=arrow)
            op.menu, op.action = key, action
    layout.separator()
    row = layout.row(align=True)
    row.operator('bbe.toolbar_menu', text='Reset Layout', icon='LOOP_BACK').action = 'RESET'
    row.operator('wm.save_userpref', text='Save Layout', icon='FILE_TICK')


class VIEW3D_PT_bbe_toolbar_settings(bpy.types.Panel):
    bl_idname = 'VIEW3D_PT_bbe_toolbar_settings'
    bl_label = 'Toolbar Settings'
    bl_description = 'Choose which Base Builder menus are visible and reorder them'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 20

    def draw(self, context):
        draw_toolbar_settings(self.layout, context)


class VIEW3D_PT_bbe_toolbar_color(bpy.types.Panel):
    bl_idname = 'VIEW3D_PT_bbe_toolbar_color'
    bl_label = 'Color & Materials'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 22

    def draw(self, context):
        from .. import draw_colour_palette
        draw_colour_palette(self.layout, context)


class VIEW3D_PT_bbe_toolbar_lighting(bpy.types.Panel):
    bl_idname = 'VIEW3D_PT_bbe_toolbar_lighting'
    bl_label = 'Lighting & Scenes'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 24

    def draw(self, context):
        from ..stages import BBE_PT_stage
        BBE_PT_stage.draw(self, context)


def draw_toolbar(self, context):
    if not hasattr(context.scene, 'nms_main'):
        return
    layout = self.layout
    # Blender draws its own flexible spacer after draw_tool_settings. Pair it
    # with this one to center our group between the native controls.
    layout.separator_spacer()
    order, hidden = toolbar_state(context)
    row = layout.row(align=True)
    for key in order:
        if key in hidden:
            continue
        _, label, panel, icon = _ITEMS[key]
        if key == 'proxies':
            row.popover(panel=panel, text=label,
                        icon_value=icons.get_icons_pscroll()['plugin_icon'].icon_id)
        else:
            row.popover(panel=panel, text=label, icon=icon)
    row.popover(panel=VIEW3D_PT_bbe_toolbar_settings.bl_idname, text='', icon='PREFERENCES')


def _draw_tool_settings(self, context):
    # Keep the native selection/mode controls first and preserve every control
    # they draw. The main Viewport header is untouched.
    _original_tool_settings(self, context)
    draw_toolbar(self, context)


def _ensure_toolbar():
    if not _enabled:
        return None
    # Deferred until after addon_utils.enable has left restricted registration.
    # Scan only spaces, once a second; never read saves or assets here. Newly
    # opened workspaces get the row too. A user's later visibility choice wins.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            space = area.spaces.active
            pointer = space.as_pointer()
            if pointer not in _original_visibility:
                _original_visibility[pointer] = space.show_region_tool_header
                space.show_region_tool_header = True
    return 1.0


@persistent
def _load_toolbar(_dummy):
    _original_visibility.clear()
    if _enabled and not bpy.app.timers.is_registered(_ensure_toolbar):
        bpy.app.timers.register(_ensure_toolbar, first_interval=0.1)


classes = (
    VIEW3D_PT_nms_base_builder, VIEW3D_PT_nms_io_panel,
    *(panel for panel, _icon in TOOLBAR_GROUPS),
    BBE_OT_toolbar_menu, VIEW3D_PT_bbe_toolbar_settings, VIEW3D_PT_bbe_toolbar_color,
    VIEW3D_PT_bbe_toolbar_lighting,
)


def register_menu():
    global _enabled, _original_tool_settings
    bpy.types.Scene.enum_assets_quick_access_view_mode = bpy.props.EnumProperty(
        name='View Mode', description='Quick access assets',
        items=[('fav', 'Favourites', 'Favourite parts', 'HEART', 0),
               ('recent', 'Recent', 'Recently used parts', 'MOD_TIME', 1)],
        default='fav',
    )
    header = bpy.types.VIEW3D_HT_tool_header
    _original_tool_settings = header.draw_tool_settings
    header.draw_tool_settings = _draw_tool_settings
    _enabled = True
    if _load_toolbar not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_load_toolbar)
    if not bpy.app.timers.is_registered(_ensure_toolbar):
        bpy.app.timers.register(_ensure_toolbar, first_interval=0.1)


def unregister_menu():
    global _enabled
    _enabled = False
    if bpy.app.timers.is_registered(_ensure_toolbar):
        bpy.app.timers.unregister(_ensure_toolbar)
    if _load_toolbar in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_toolbar)
    header = bpy.types.VIEW3D_HT_tool_header
    if header.draw_tool_settings is _draw_tool_settings:
        header.draw_tool_settings = _original_tool_settings
    # During disable Blender may restrict bpy.data as it does during enable.
    # Do not touch scene data in that case or fail extension cleanup.
    for screen in getattr(bpy.data, 'screens', ()):
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                previous = _original_visibility.get(space.as_pointer())
                if previous is not None:
                    space.show_region_tool_header = previous
    _original_visibility.clear()
    if hasattr(bpy.types.Scene, 'enum_assets_quick_access_view_mode'):
        del bpy.types.Scene.enum_assets_quick_access_view_mode
