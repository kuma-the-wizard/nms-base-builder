"""Interactive thumbnail surface for the dedicated Asset Browser window.

Uses the existing category/search/favourite data and placement operators. The
window's left-hand native controls are unchanged. Geometry supplies both drawing
and hit testing, so image clicks do not depend on undocumented UI button sizes.
"""
import json
import math
from collections import OrderedDict
from array import array

import bpy
import blf
import gpu
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader
from .. import icons
from ..utils.asset_browser_utils import get_grid_settings, resolve_sub_categories

_sessions = {}
_resources = {}
_pending_windows = set()
_enabled = False


def mark_window_pending(window):
    _pending_windows.add(window.as_pointer())


def unmark_window_pending(window):
    try:
        _pending_windows.discard(window.as_pointer())
    except ReferenceError:
        pass


def release_stale_sessions(window_manager):
    """A just-closed pop-out may still own the pointer Blender reuses."""
    live = {(window.as_pointer(), area.as_pointer())
            for window in window_manager.windows for area in window.screen.areas
            if area.type == 'IMAGE_EDITOR'}
    for key, session in tuple(_sessions.items()):
        try:
            identity = (session._window.as_pointer(), session._area.as_pointer())
        except ReferenceError:
            identity = None
        if identity not in live:
            _release_session(key, window_manager)


def request_redraw():
    """Property callbacks request a frame immediately, without waiting for a timer."""
    for session in tuple(_sessions.values()):
        try:
            session._area.tag_redraw()
        except ReferenceError:
            pass  # The window cleanup timer owns disposal of closed sessions.


def _release_session(key, window_manager):
    # Blender invalidates an operator's RNA as soon as its window closes. Keep
    # cleanup handles outside that operator so closing the window is safe too.
    resources = _resources.pop(key, None)
    if resources:
        handler, timer, textures = resources
        bpy.types.SpaceImageEditor.draw_handler_remove(handler, 'WINDOW')
        try:
            window_manager.event_timer_remove(timer)
        except ReferenceError:
            pass  # The window may already have disposed of its event timer.
        textures.clear()
    _sessions.pop(key, None)


def _groups(scene):
    browser = scene.nms_asset_browser
    mode = browser.enum_asset_browser_what_to_display
    if mode == 'search':
        return browser.get_search_results()
    if mode == 'fav':
        return {'Favourite Objects': browser.get_favourite_objects_data()}
    if mode == 'recent':
        return {'Recent Objects': browser.get_recent_objects_data()}
    if mode == 'preset':
        return {'Presets': browser.get_preset_data()}
    return resolve_sub_categories(browser.get_categories_data(),
                                  browser.asset_browser_caterogies,
                                  browser.asset_browser_sub_caterogies)


def grid_geometry(groups, width, icon_size, columns, scale=1):
    """Return content-space rectangles; scroll is applied only at draw/hit time."""
    margin, gap = 10 * scale, 4 * scale
    columns = max(1, min(columns, int(max(width - margin * 2, 1) / (68 * scale))))
    tile_w = max(1, (width - margin * 2 - gap * (columns - 1)) / columns)
    image_h = max(32 * scale, min(icon_size * 20 * scale, tile_w - 8 * scale))
    tile_h = image_h + 48 * scale
    titles, tiles, top = [], [], margin
    for title, parts in groups.items():
        titles.append((margin, top, str(title)))
        top += 28 * scale
        for index, (object_id, data) in enumerate(parts.items()):
            x = margin + (index % columns) * (tile_w + gap)
            y = top + (index // columns) * (tile_h + gap)
            tiles.append((x, y, tile_w, tile_h, object_id, data))
        top += math.ceil(len(parts) / columns) * (tile_h + gap) + 10 * scale
    return titles, tiles, top


def _contains(rect, x, y):
    left, top, width, height = rect
    return left <= x < left + width and top <= y < top + height


def tile_action(tile, x, y, scale=1):
    left, top, width, height, _object_id, data = tile
    if not _contains((left, top, width, height), x, y):
        return None
    button = 24 * scale
    if not data.get('is_preset') and _contains((left, top, button, button), x, y):
        return 'options'
    if data.get('variants') and _contains((left + width - button, top, button, button), x, y):
        return 'variants'
    return 'place'


class BBE_OT_asset_grid(bpy.types.Operator):
    bl_idname = 'bbe.asset_grid'
    bl_label = 'Asset Browser Grid'
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        if context.area.type != 'IMAGE_EDITOR':
            return {'CANCELLED'}
        release_stale_sessions(context.window_manager)
        key = context.area.as_pointer()
        if key in _sessions:
            return {'CANCELLED'}
        self._window, self._area, self._key = context.window, context.area, key
        self._offset, self._hover, self._drag = 0, None, False
        self._pressed = None
        self._signature, self._geometry_key = None, None
        self._textures = OrderedDict()
        self._groups, self._tiles, self._titles = {}, [], []
        self._total, self._max_offset, self._view_height = 0, 0, 1
        self._scale = 1
        self._rect_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self._image_shader = gpu.shader.from_builtin('IMAGE')
        self._handler = bpy.types.SpaceImageEditor.draw_handler_add(
            self.draw_grid, (), 'WINDOW', 'POST_PIXEL')
        self._timer = context.window_manager.event_timer_add(.25, window=context.window)
        _sessions[key] = self
        _resources[key] = (self._handler, self._timer, self._textures)
        context.window_manager.modal_handler_add(self)
        self.refresh(context)
        return {'RUNNING_MODAL'}

    def refresh(self, context):
        scene = self._window.scene
        browser = scene.nms_asset_browser
        size, columns = get_grid_settings(context, 'asset_browser_icon_size_other',
                                         'asset_browser_number_of_columns_other')
        # Contents change through the browser's mutation methods. A revision
        # avoids walking every part and variant on every Blender timer event.
        signature = (scene.as_pointer(), browser.view_revision, size, columns,
                     browser.enum_asset_browser_what_to_display,
                     browser.asset_browser_caterogies, browser.asset_browser_sub_caterogies)
        if signature != self._signature:
            groups = _groups(scene)
            # Reset scroll only when the visible group changes; adding a recent
            # item or toggling a favourite should not jump the category view.
            if tuple(groups) != tuple(self._groups):
                self._offset = 0
            self._signature, self._groups = signature, groups
            self._size, self._columns = size, columns
            self._geometry_key = None
            self._hover = None
            self._area.tag_redraw()

    def finish(self, context):
        _release_session(self._key, context.window_manager)

    def modal(self, context, event):
        if not _enabled or self._key not in _sessions:
            return {'CANCELLED'}
        try:
            if self._area.type != 'IMAGE_EDITOR' or self._area not in tuple(self._window.screen.areas):
                self.finish(context)
                return {'CANCELLED'}
            if event.type == 'TIMER':
                self.refresh(context)
                return {'PASS_THROUGH'}
            region = next(r for r in self._area.regions if r.type == 'WINDOW')
            x, y = event.mouse_x - region.x, region.height - (event.mouse_y - region.y)
            inside = 0 <= x < region.width and 0 <= y < self._view_height
            if not inside and not self._drag:
                if self._hover is not None:
                    self._hover = None
                    self._area.tag_redraw()
                return {'PASS_THROUGH'}
            if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
                self._offset = max(0, min(self._max_offset, self._offset +
                                   (1 if event.type == 'WHEELDOWNMOUSE' else -1) * 100 * self._scale))
                self._area.tag_redraw()
                return {'RUNNING_MODAL'}
            if event.type == 'TRACKPADPAN':
                self._offset = max(0, min(self._max_offset, self._offset + event.mouse_prev_y - event.mouse_y))
                self._area.tag_redraw()
                return {'RUNNING_MODAL'}
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self._drag:
                self._drag = False
                return {'RUNNING_MODAL'}
            if self._drag or (event.type == 'LEFTMOUSE' and event.value == 'PRESS'
                              and x >= region.width - 14 * self._scale):
                self._drag = True
                self._offset = self._max_offset * min(1, max(0, y / max(1, self._view_height)))
                self._area.tag_redraw()
                return {'RUNNING_MODAL'}
            hit = next(((tile, tile_action(tile, x, y + self._offset, self._scale))
                        for tile in self._tiles if _contains(tile[:4], x, y + self._offset)), None)
            hover = (hit[0][4], hit[1]) if hit else None
            if hover != self._hover:
                self._hover = hover
                self._area.tag_redraw()
            if event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and event.value == 'PRESS':
                self._pressed = (hover, event.type)
                return {'RUNNING_MODAL'}
            if event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and event.value == 'RELEASE':
                pressed, self._pressed = self._pressed, None
                if hit and pressed == (hover, event.type):
                    tile, action = hit
                    if event.type == 'RIGHTMOUSE' or action == 'options':
                        self.show_options(context, tile)
                    else:
                        object_id, data = tile[4:]
                        bpy.ops.object.nms_asset_browser_object_selected(
                            'EXEC_DEFAULT', object_id=object_id, is_preset=bool(data.get('is_preset')),
                            has_variants=action == 'variants',
                            variants=json.dumps([object_id, *(data.get('variants') or [])]))
                    self.refresh(context)
                return {'RUNNING_MODAL'}
            # Keep Blender's image zoom/pan shortcuts from taking over the grid.
            if event.type in {'MIDDLEMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE'}:
                return {'RUNNING_MODAL'}
        except ReferenceError:
            self.finish(context)
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def show_options(self, context, tile):
        object_id, data = tile[4:]
        def menu(menu, _context):
            layout = menu.layout
            op = layout.operator('object.nms_asset_browser_object_selected', text='Place Part', icon='ADD')
            op.object_id, op.is_preset = object_id, bool(data.get('is_preset'))
            if data.get('variants'):
                op = layout.operator('object.nms_asset_browser_object_selected', text='Choose Variant', icon='PAUSE')
                op.object_id, op.has_variants = object_id, True
                op.variants = json.dumps([object_id, *data['variants']])
            if not data.get('is_preset'):
                layout.separator()
                op = layout.operator('object.nms_asset_browser_object_favourite', icon='HEART',
                    text='Remove from Favourites' if data.get('is_fav') else 'Add to Favourites')
                op.object_id = object_id
                op = layout.operator('object.nms_asset_browser_batch_replace', text='Replace Selected Objects')
                op.object_id = object_id
        context.window_manager.popup_menu(menu, title=data['name'])

    def rectangle(self, x, y, w, h, color):
        shader = self._rect_shader
        shader.bind()
        shader.uniform_float('color', color)
        batch_for_shader(shader, 'TRI_FAN', {'pos': ((x, y), (x+w, y), (x+w, y+h), (x, y+h))}).draw(shader)

    def label(self, x, y, label, width, size=12, color=(.85, .86, .88, 1)):
        blf.size(0, size * self._scale)
        label = str(label)
        if blf.dimensions(0, label)[0] > width:
            while label and blf.dimensions(0, label + '...')[0] > width:
                label = label[:-1]
            label += '...'
        blf.color(0, *color)
        blf.position(0, x, y, 0)
        blf.draw(0, label)

    def preview(self, object_id, x, y, size):
        if object_id not in self._textures:
            preview = icons.get_asset_icons_pcoll().get(object_id)
            if preview is None or not preview.image_size[0]:
                return
            width, height = preview.image_size
            # Bulk-copy the thumbnail into a contiguous buffer. Slicing the RNA
            # array creates tens of thousands of Python floats for each icon.
            values = array('f', [0.0]) * (width * height * 4)
            preview.image_pixels_float.foreach_get(values)
            pixels = gpu.types.Buffer('FLOAT', len(values), values)
            self._textures[object_id] = gpu.types.GPUTexture((width, height), format='RGBA8', data=pixels)
            # Only displayed previews become GPU textures. Cap the cache so a
            # long browsing session cannot load the complete library onto GPU.
            if len(self._textures) > 160:
                self._textures.popitem(last=False)
        self._textures.move_to_end(object_id)
        # Font drawing changes Blender's blend state between tiles.
        gpu.state.blend_set('ALPHA')
        shader = self._image_shader
        shader.bind()
        shader.uniform_sampler('image', self._textures[object_id])
        batch_for_shader(shader, 'TRI_FAN', {
            'pos': ((x,y), (x+size,y), (x+size,y+size), (x,y+size)),
            'texCoord': ((0,0), (1,0), (1,1), (0,1))}).draw(shader)

    def draw_grid(self):
        context = bpy.context
        if context.area is None or context.area.as_pointer() != self._key:
            return
        self.refresh(context)
        region = context.region
        width, height = region.width, region.height
        scale = max(.75, context.preferences.system.ui_scale)
        self._scale = scale
        self._view_height = max(1, height - 30 * scale)
        key = (width, height, scale, self._size, self._columns, self._signature)
        if key != self._geometry_key:
            self._titles, self._tiles, self._total = grid_geometry(
                self._groups, width - 14 * scale, self._size, self._columns, scale)
            self._max_offset = max(0, self._total - self._view_height)
            self._offset = min(self._offset, self._max_offset)
            self._geometry_key = key
        gpu.state.blend_set('ALPHA')
        try:
            self.rectangle(0, 0, width, height, (.19, .19, .19, 1))
            for x, top, title in self._titles:
                y = height - top + self._offset - 18 * scale
                if 30 * scale <= y <= height:
                    self.label(x, y, title, width - 30 * scale)
            for x, top, w, h, object_id, data in self._tiles:
                y = height - top - h + self._offset
                if y + h < 30 * scale or y > height:
                    continue
                hovered = self._hover and self._hover[0] == object_id
                self.rectangle(x, y, w, h, (.19, .25, .30, 1) if hovered else (.155, .155, .155, 1))
                size = min(w - 8 * scale, h - 48 * scale)
                self.preview(object_id, x + (w-size)/2, y + 26 * scale, size)
                self.label(x+6*scale, y+8*scale, data['name'], w-12*scale, 11)
                # These rectangles match tile_action's hit boxes exactly.
                if not data.get('is_preset'):
                    for line in range(3):
                        self.rectangle(x+8*scale, y+h-(8+line*4)*scale, 11*scale, scale, (.7,.7,.7,1))
                if data.get('variants'):
                    for line in range(2):
                        self.rectangle(x+w-(16-line*6)*scale, y+h-18*scale, 2*scale, 11*scale, (.85,.85,.85,1))
            if not self._tiles:
                self.label(12*scale, height-60*scale, 'No parts in this view.', width-24*scale)
            if self._max_offset:
                thumb = max(30*scale, self._view_height**2 / max(self._total, 1))
                top = self._offset / self._max_offset * (self._view_height-thumb)
                self.rectangle(width-9*scale, height-top-thumb, 5*scale, thumb, (.32,.32,.32,1))
            self.rectangle(0, 0, width, 30*scale, (.14,.14,.14,1))
            item = next((t for t in self._tiles if self._hover and t[4] == self._hover[0]), None)
            hint = item[5]['name'] + '  |  ' + item[4] if item else 'Click an image to place  |  Right-click for favourites and options'
            self.label(10*scale, 10*scale, hint, width-20*scale, 11)
        finally:
            gpu.state.blend_set('NONE')


@persistent
def _close_all(_dummy=None):
    for key in tuple(_resources):
        _release_session(key, bpy.context.window_manager)
    _pending_windows.clear()


def _saved_browser_target(window):
    areas = sorted(window.screen.areas, key=lambda area: area.x)
    if len(areas) < 2 or areas[0].type != 'PROPERTIES':
        return None
    pinned = areas[0].spaces.active.pin_id
    if getattr(pinned, 'name', None) != 'Asset Browser Window':
        return None
    right = areas[1]
    return right if right.type in {'PROPERTIES', 'IMAGE_EDITOR'} else None


def _restore_saved_windows(window_manager):
    """A saved Blender layout restores areas, but not their modal grid operator."""
    for window in tuple(window_manager.windows):
        if window.as_pointer() in _pending_windows:
            continue
        right = _saved_browser_target(window)
        if right is None:
            continue
        if right.as_pointer() in _sessions:
            continue
        if right.type == 'PROPERTIES':
            right.type = 'IMAGE_EDITOR'
        space = right.spaces.active
        space.show_region_ui = False
        space.show_region_toolbar = False
        space.show_region_header = False
        space.show_region_tool_header = False
        space.show_region_hud = False
        region = next((region for region in right.regions if region.type == 'WINDOW'), None)
        if region is None:
            continue  # The editor's region is created on the next UI update.
        with bpy.context.temp_override(window=window, area=right, region=region):
            bpy.ops.bbe.asset_grid('INVOKE_DEFAULT')


def _cleanup_closed():
    if not _enabled:
        return None
    live_areas = {area.as_pointer() for window in bpy.context.window_manager.windows
                  for area in window.screen.areas if area.type == 'IMAGE_EDITOR'}
    for key in tuple(_resources):
        if key not in live_areas:
            _release_session(key, bpy.context.window_manager)
    try:
        _restore_saved_windows(bpy.context.window_manager)
    except (ReferenceError, RuntimeError, TypeError, AttributeError) as exc:
        print(f'BBE Asset Browser: grid restore will retry: {exc}')
    return 1.0


def register():
    global _enabled
    bpy.utils.register_class(BBE_OT_asset_grid)
    _enabled = True
    bpy.app.handlers.load_pre.append(_close_all)
    bpy.app.timers.register(_cleanup_closed, first_interval=1, persistent=True)


def unregister():
    global _enabled
    _enabled = False
    if bpy.app.timers.is_registered(_cleanup_closed):
        bpy.app.timers.unregister(_cleanup_closed)
    bpy.app.handlers.load_pre.remove(_close_all)
    _close_all()
    bpy.utils.unregister_class(BBE_OT_asset_grid)
