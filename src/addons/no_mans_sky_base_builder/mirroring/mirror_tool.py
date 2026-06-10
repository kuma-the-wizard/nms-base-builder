from . import mirror_utils
import bpy
import os
from ..utils import blend_utils
from ..utils import python as python_utils
from .. import builder, part
from .mirror_utils import ShowMessageBox

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
NICE_JSON = os.path.join(
    FILE_PATH,
    "..",
    "resources",
    "nice_names.json"
)

nice_name_dictionary = python_utils.load_dictionary(NICE_JSON)
BUILDER = builder.Builder()

class MirrorTool(bpy.types.PropertyGroup):
    
    check_show_advanced_options: bpy.props.BoolProperty(
        name="Show advanved options",
        default=False,
        options={'SKIP_SAVE'}
    )
    
    check_auto_duplicate: bpy.props.BoolProperty(
        name="Auto duplicate",
        default=False,
        options={'SKIP_SAVE'}
    )
    
    mirror_direction: bpy.props.EnumProperty(
        name="Mirror Direction",
        items = [
            ("X", "X", "mirror in X direction"),
            ("Y", "Y", "mirror in Y direction"),
            ("Z", "Z", "mirror in Z direction"),
        ],
        options={'SKIP_SAVE'},
        default = 'X'
    )
    
    center_of_reflection: bpy.props.EnumProperty(
        name="Reflection Center",
        items = [
            ("World Origin", "World Origin", "","OBJECT_ORIGIN",0),
            ("3D cursor", "3D cursor", "","CURSOR",1),
            ("Object", "Object", "","CON_PIVOT",2),
        ],
        options={'SKIP_SAVE'},
        default = 'World Origin'
    )
    
    target_object: bpy.props.PointerProperty(
        name="Target Object",
        type=bpy.types.Object
    )
    
    
    def mirror_across_axis(self, axis = None, center = (0,0,0)):
        """Mirror the object along X axis (if possible)."""
        # Store selection.
        selected_objects = bpy.context.selected_objects

        # Validate
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.", title="Mirror"
            )
            return

        # Get Selected item.
        new_items = []
        for target in selected_objects:
            # Part
            if "ObjectID" in target:
                object_id = target["ObjectID"]
                mirror_id = part.Part.get_mirror_part_id(object_id)
                
                if self.check_auto_duplicate:
                    new_item = target.copy()
                    new_item.data = target.data.copy()
                    bpy.context.collection.objects.link(new_item)
                else :
                    new_item = target
                    
                mirror_part_exist = False
                if mirror_id in nice_name_dictionary.keys():
                    # Build Item.
                    new_item = BUILDER.mirror_part(target)
                    mirror_part_exist = True

                # mirror part across x axis
                if axis:
                    mirrored_matrix_world = mirror_utils.mirror_matrix_world_universal(object_id, new_item.matrix_world, axis,center)
                    new_item.matrix_world = mirrored_matrix_world
                # mirror part on its location
                else:
                    # Apply mirroring fixes on parts that dont have a ingame asset to represent their mirror.
                    if not mirror_part_exist:
                        mirrored_matrix_world = mirror_utils.mirror_matrix_world_universal(object_id, new_item.matrix_world, axis,center)
                        new_item.matrix_world = mirrored_matrix_world
                        
                if hasattr(new_item, "object"):
                    new_items.append(new_item.object)
                else:
                    new_items.append(new_item)
        blend_utils.select(new_items)
        return {"FINISHED"}
    
    def advanced_mirror(self):
        mirror_direction = self.mirror_direction
        if self.center_of_reflection == "World Origin":
            self.mirror_across_axis(axis = mirror_direction, center=(0,0,0))
        elif self.center_of_reflection == "3D cursor":
            cursor_location = bpy.context.scene.cursor.location
            center = (
                cursor_location.x,
                cursor_location.y,
                cursor_location.z
            )
            self.mirror_across_axis(axis = mirror_direction, center = center)
        elif self.center_of_reflection == "Object":
            if self.target_object:
                center = (
                    self.target_object.location.x,
                    self.target_object.location.y,
                    self.target_object.location.z
                )
                self.mirror_across_axis(axis = mirror_direction, center = center)
            else:
                ShowMessageBox(
                    message="Make sure you have target object selected", title="Object Mirror"
                )