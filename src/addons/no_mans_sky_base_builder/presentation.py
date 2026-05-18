import os
import bpy

from .utils import material as _material
from bpy.types import Panel
from .addon_state import preview_collections

from .save_editor import check_dependencies

# File Buttons Panel ---
class NMS_PT_file_buttons_panel(Panel):
    bl_idname = "NMS_PT_file_buttons_panel"
    bl_label = "No Man's Sky Base Builder"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        file_box = layout.box()
        first_column = file_box.column(align=True)
        first_column.label(text="File")
        button_row = first_column.row(align=True)
        button_row.operator("object.nms_new_file")
        save_load_row = first_column.row(align=True)
        save_load_row.operator("object.nms_save_data", icon="FILE_TICK")
        save_load_row.operator("object.nms_load_data", icon="FILE_FOLDER")


        import_box = layout.box()
        second_column = import_box.column(align=True)
        second_column.label(text="Import & Export")
        nms_row = second_column.row(align=True)
        nms_row.operator("object.nms_import_nms_data", icon="PASTEDOWN")
        export_col = nms_row.column(align=True)
        export_col.operator("object.nms_export_nms_data", icon="COPYDOWN")
        export_col.operator("object.nms_export_nms_data_objects", icon="COPYDOWN")
        
        #community box
        communuity_box = layout.box()
        third_column = communuity_box.column(align=True)
        third_column.label(text="Commmunity")
        community_row = third_column.row(align=True)
        community_row.operator("object.nms_visit_guides", icon="WORLD_DATA")
        community_row.operator("object.nms_visit_community", icon="WORLD_DATA")
        
# Save Editor Panel ---
class NMS_PT_save_editor_panel(Panel):
    bl_idname = "NMS_PT_save_editor_panel"
    bl_label = "Save Editor"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        
        # Save Editor Box
        prefs = context.preferences.addons[__package__].preferences
        save_data = context.scene.nms_save_data
        
        lz4_found =  check_dependencies.check_package("lz4")
        
        if not lz4_found:
            print("lz4 not found")
        else:
            save_folder_box = layout.box()
            sf_column = save_folder_box.column(align=True)
            sf_column.label(text="Save Folder")
            savefile_col = sf_column.row(align=True)
            savefile_col.prop(prefs, "nms_save_folder_path")
            savefile_col.operator( "object.nms_select_save_folder", text="", icon='FILE_FOLDER')
            sf_column.prop(save_data, "nms_account_selected")

            save_data_box = layout.box()
            se_column = save_data_box.column(align=True)
            se_column.label(text="Save Data")
            se_column.prop(save_data, "nms_save_slot")
            
            se_column.separator()
            
            base_type_row = se_column.row(align=True)
            base_type_row.label(text="Base Type")
            base_type_row.prop(save_data, "nms_base_type",expand=True, text = "base type")
            se_column.prop(save_data, "nms_base_index", text="")
            
            se_column.separator()
            import_export_row = se_column.row(align=True)
            import_export_row.operator("object.nms_import_base_from_save", icon="IMPORT", text = "Import")
            import_export_row.operator("object.nms_export_base_to_save", icon="EXPORT", text = "Export")
        

# Base Property Panel ---
class NMS_PT_base_prop_panel(Panel):
    bl_idname = "NMS_PT_base_prop_panel"
    bl_label = "Base Properties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nms_tool = scene.nms_base_tool
        properties_box = layout.box()
        properties_column = properties_box.column(align=True)
        properties_column.prop(nms_tool, "string_base")
        properties_column.prop(nms_tool, "string_address")
        properties_column.prop(nms_tool, "string_userdata")
        
# Snap Panel ---
class NMS_PT_snap_panel(Panel):
    bl_idname = "NMS_PT_snap_panel"
    bl_label = "Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nms_tool = scene.nms_base_tool

        # Split into two columns of equal widths.
        split = layout.split(factor=0.5)
        tools_column, snap_column = (split.column(), split.column())

        # Create Part Count Box.
        part_box = tools_column.box()
        splitter = part_box.split(factor=0.7)
        splitter.label(text="Part Count:")
        part_count = len([obj for obj in bpy.data.objects if "ObjectID" in obj])
        splitter.label(text="{}".format(part_count))

        tools_box = tools_column.box()
        tools_col = tools_box.column(align=True)

        tools_col.label(text="Visibility")
        # Room Vis Button.
        label = "Normal"
        if nms_tool.room_vis_switch == 1:
            label = "Ghosted"
        elif nms_tool.room_vis_switch == 2:
            label = "Invisible"

        tools_col.operator("object.nms_toggle_room_visibility", icon="CUBE", text=label)

        tools_col.label(text="Duplicate")
        tools_col.operator("object.nms_duplicate", icon="DUPLICATE")
        dup_along_curve = tools_col.operator(
            "object.nms_duplicate_along_curve", icon="CURVE_DATA"
        )
        tools_col.label(text="Delete")
        tools_col.operator("object.nms_delete", icon="CANCEL")

        # Create Snapping box.
        snap_box = snap_column.box()
        snap_col = snap_box.column(align=True)
        snap_col.label(text="Snap")
        snap_op = snap_col.operator("object.nms_snap", icon="SNAP_ON")

        target_row = snap_col.row(align=True)
        target_row.label(text="Target")
        snap_target_prev = target_row.operator(
            "object.nms_snap", icon="TRIA_LEFT", text="Prev"
        )
        snap_target_next = target_row.operator(
            "object.nms_snap", icon="TRIA_RIGHT", text="Next"
        )

        source_row = snap_col.row(align=True)
        source_row.label(text="Source")
        snap_source_prev = source_row.operator(
            "object.nms_snap", icon="TRIA_LEFT", text="Prev"
        )
        snap_source_next = source_row.operator(
            "object.nms_snap", icon="TRIA_RIGHT", text="Next"
        )

        # Corvette Mirror Tools
        mirror_box = snap_column.box()
        mirror_col = mirror_box.column(align=True)
        mirror_col.label(text="Mirroring")
        mirror_op = mirror_col.operator("object.nms_mirror", icon="ARROW_LEFTRIGHT")
        mirror_op_x = mirror_col.operator(
            "object.nms_mirror_across_x", icon="ARROW_LEFTRIGHT"
        )
        flip_op = mirror_col.operator("object.nms_flip", icon="DECORATE_OVERRIDE")

        # Set Snap Operator assignments.
        # Default
        snap_op.prev_source = False
        snap_op.next_source = False
        snap_op.prev_target = False
        snap_op.next_target = False
        # Previous Target.
        snap_target_prev.prev_source = False
        snap_target_prev.next_source = False
        snap_target_prev.prev_target = True
        snap_target_prev.next_target = False
        # Next Target.
        snap_target_next.prev_source = False
        snap_target_next.next_source = False
        snap_target_next.prev_target = False
        snap_target_next.next_target = True
        # Previous Source.
        snap_source_prev.prev_source = True
        snap_source_prev.next_source = False
        snap_source_prev.prev_target = False
        snap_source_prev.next_target = False
        # Next Source.
        snap_source_next.prev_source = False
        snap_source_next.next_source = True
        snap_source_next.prev_target = False
        snap_source_next.next_target = False


# Colour Panel ---
class NMS_PT_colour_panel(Panel):
    bl_idname = "NMS_PT_colour_panel"
    bl_label = "Colour & Materials"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nms_tool = scene.nms_base_tool
        pcoll = preview_collections["main"]
        colour_area = layout.column(align=True)
        enum_row = colour_area.row(align=True)
        enum_row.prop(nms_tool, "material_switch")

        colours = _material.get_colours_from_palette(nms_tool.material_switch)

        grid = layout.grid_flow(columns=3, even_columns=True)

        for row in colours:
            index = row[3]
            name = row[5]
            colour = row[6]
            thumb = row[9]
            index, name, colour, thumb
            colour_icon = pcoll.get(os.path.splitext(thumb)[0], None)
            op = grid.operator(
                "object.nms_apply_colour",
                text=name,
                icon_value=colour_icon.icon_id if colour_icon else 0,
            )
            op.colour_index = int(index)


# Colour Panel ---
class NMS_PT_logic_panel(Panel):
    bl_idname = "NMS_PT_logic_panel"
    bl_label = "Cables and Logic"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nms_tool = scene.nms_base_tool

        layout = self.layout
        box = layout.box()
        col = box.column()
        col.label(text="Cables")
        enum_row = col.row()
        enum_row.prop(nms_tool, "line_switch")
        row = col.row()
        row.operator("object.nms_point", icon="EMPTY_DATA")
        row.operator("object.nms_connect", icon="PARTICLES")
        divide_row = col.row()
        divide_row.operator("object.nms_divide", icon="LINCURVE")
        divide_row.operator("object.nms_split", icon="MOD_PHYSICS")
        select_row = col.row()
        select_row.operator("object.nms_select_connected", icon="RESTRICT_SELECT_OFF")
        select_row.operator("object.nms_select_floating", icon="RESTRICT_INSTANCED_ON")

        col.label(text="Logic")
        logic_row = col.row()
        logic_row.operator("object.nms_logic_button")
        logic_row.operator("object.nms_logic_wall_switch")
        logic_row.operator("object.nms_logic_prox_switch")
        logic_row.operator("object.nms_logic_inv_switch")
        logic_row.operator("object.nms_logic_auto_switch")
        logic_row.operator("object.nms_logic_floor_switch")
        logic_row.operator("object.nms_logic_beat_switch")


# Build Panel ---
class NMS_PT_build_panel(Panel):
    bl_idname = "NMS_PT_build_panel"
    bl_label = "Build"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nms_tool = scene.nms_base_tool
        col = layout.column(align=True)
        col.operator("object.nms_launch_asset_browser", icon="DESKTOP")
        col.operator("object.nms_save_as_preset", icon="SCENE_DATA")
        row = col.row(align=True)
        row.operator("object.nms_get_more_presets", icon="WORLD_DATA")
        row.operator("object.nms_open_preset_folder", icon="FILE_FOLDER")
        layout.prop(nms_tool, "enum_switch", expand=True)
        layout.template_list(
            "NMS_UL_actions_list",
            "compact",
            context.scene,
            "col",
            context.scene,
            "col_idx",
        )
        
        
ui_classes = (
    NMS_PT_file_buttons_panel,
    NMS_PT_save_editor_panel,
    NMS_PT_base_prop_panel,
    NMS_PT_snap_panel,
    NMS_PT_colour_panel,
    NMS_PT_logic_panel,
    NMS_PT_build_panel,
)