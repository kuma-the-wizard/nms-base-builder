import bpy
from bpy.types import Panel, PropertyGroup

# Snap Panel ---
class NMS_PT_mirror_panel(Panel):
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
        mirror_tool = context.scene.nms_mirror_tool

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
        

        # Create Snapping box.
        snap_box = snap_column.box()
        snap_col = snap_box.column(align=True)
        
        snap_button_row = snap_col.row(align = True)
        snap_button_split = snap_button_row.split(factor=0.33333)
        snap_label_col, snap_button_container = (snap_button_split.column(align = True), snap_button_split.column())
        
        snap_label_col.label(text="Snap")
        snap_label_col.label(text="Target")
        snap_label_col.label(text="Source")
        
        snap_op = snap_button_container.operator("object.nms_snap", icon="SNAP_ON")

        target_source_column = snap_button_container.column(align=True)
        source_row = target_source_column.row(align=True)
        target_row = target_source_column.row(align=True)
        
        snap_target_prev = target_row.operator( "object.nms_snap", icon="TRIA_LEFT", text="Prev" )
        snap_target_next = target_row.operator( "object.nms_snap", icon="TRIA_RIGHT", text="Next" )
        
        snap_source_prev = source_row.operator( "object.nms_snap", icon="TRIA_LEFT", text="Prev")
        snap_source_next = source_row.operator("object.nms_snap", icon="TRIA_RIGHT", text="Next")
        
        delete_box = snap_column.box()
        delete_col = delete_box.column(align = True)
        delete_col.label(text="Delete")
        delete_col.operator("object.nms_delete", icon="CANCEL")
        delete_col.operator("object.nms_cleanup_scene",icon = "BRUSH_DATA")

        # Corvette Mirror Tools
        orientation_box = layout.box()
        mirror_col = orientation_box.row(align=True)
        mirror_col.label(text="Orientation", icon = "ORIENTATION_GIMBAL")
        mirror_col.operator("object.nms_mirror", icon="ARROW_LEFTRIGHT")
        mirror_col.operator("object.nms_flip", icon="DECORATE_OVERRIDE")
        
        mirroring_box = layout.box()
        mirroring_box_column = mirroring_box.column(align = True)
        mirroring_box_column.label(text = "Mirroring", icon = "MOD_MIRROR")
        mirroring_box_column.prop(mirror_tool,"check_show_advanced_options", text = "Show advanced options")
        if not mirror_tool.check_show_advanced_options:
            mirroring_box_column.operator( "object.nms_universal_mirror_x", icon="ARROW_LEFTRIGHT" , text = "Mirror across X" )
            mirror_xyz_row = mirroring_box_column.row(align=True)
            mirror_xyz_row.operator("object.nms_universal_mirror_y", icon="CURVE_PATH", text = "Mirror across Y")
            mirror_xyz_row.operator("object.nms_universal_mirror_z", icon="EMPTY_SINGLE_ARROW", text = "Mirror across Z")
        
        else :
            mirroring_box_column.separator()
            
            mirroring_box_column.label(text = "Center of Reflection")
            center_of_reflection_row = mirroring_box_column.row(align = True)
            center_of_reflection_row.prop(mirror_tool,"center_of_reflection",expand=True)
            
            mirroring_box_column.label(text = "Direction")
            direction_row = mirroring_box_column.row(align = True)
            direction_row.prop(mirror_tool,"mirror_direction",expand=True)

            mirroring_box_column.separator()
            if mirror_tool.center_of_reflection == "Object":
                mirroring_box_column.label(text = "Target Object")
                mirroring_box_column.prop(mirror_tool, "target_object", text = "")
                mirroring_box_column.separator()
            mirroring_box_column.prop(mirror_tool,"check_auto_duplicate")
            mirroring_box_column.operator("object.nms_advanced_mirror", icon = "MOD_MIRROR", text = "Perform Mirror")

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
