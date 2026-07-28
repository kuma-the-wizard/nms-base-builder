import bpy
import math

class ResetTransformations(bpy.types.Operator):
    """Reset Scale and Rotation of an object"""

    bl_idname = "object.nms_reset_transformations"
    bl_label = "Reset Transformations"

    def execute(self, context):
        selected_objects = bpy.context.selected_objects
                
        bpy.ops.object.rotation_clear(clear_delta=False)
        bpy.ops.object.scale_clear(clear_delta=False)
        
        for obj in selected_objects:
            if "ObjectID" in obj:
                obj.rotation_euler.x = math.pi/2
        return {"FINISHED"}
    
class CopyTransformations(bpy.types.Operator):
    """Copy Transformation of active object"""

    bl_idname = "object.nms_copy_transformations"
    bl_label = "Copy Transformations"

    def execute(self, context):
                
        scene = context.scene
        proeprties = scene.nms_properties
        
        active_object = bpy.context.active_object
        if active_object is not None:
            proeprties.copied_position = active_object.location
            proeprties.copied_rotation = active_object.rotation_euler
            proeprties.copied_scale = active_object.scale
        
        return {"FINISHED"}
    
class PasteTransformations(bpy.types.Operator):
    """Paste Copied transformations"""

    bl_idname = "object.nms_paste_transformations"
    bl_label = "Paste Transformations"

    def execute(self, context):
                
        scene = context.scene
        proeprties = scene.nms_properties
        proeprties.paste_transformatinos(paste_location = True, paste_rotation = True, paste_scale = True)
        
        return {"FINISHED"}
    
class PasteLocation(bpy.types.Operator):
    """Paste Copied location"""

    bl_idname = "object.nms_paste_location"
    bl_label = "Paste Location"

    def execute(self, context):
                
        scene = context.scene
        proeprties = scene.nms_properties
        proeprties.paste_transformatinos(paste_location = True, paste_rotation = False, paste_scale = False)
        
        return {"FINISHED"}
    
class PasteRotation(bpy.types.Operator):
    """Paste Copied Rotation"""

    bl_idname = "object.nms_paste_rotation"
    bl_label = "Paste Rotation"

    def execute(self, context):
                
        scene = context.scene
        proeprties = scene.nms_properties
        proeprties.paste_transformatinos(paste_location = False, paste_rotation = True, paste_scale = False)
        
        return {"FINISHED"}
    
class PasteScale(bpy.types.Operator):
    """Paste Copied Scale"""

    bl_idname = "object.nms_paste_scale"
    bl_label = "Paste Scale"

    def execute(self, context):
                
        scene = context.scene
        proeprties = scene.nms_properties
        proeprties.paste_transformatinos(paste_location = False, paste_rotation = False, paste_scale = True)
        
        return {"FINISHED"}
    
    
classes = (
    ResetTransformations,
    CopyTransformations,
    PasteTransformations,
    
    PasteLocation,
    PasteRotation,
    PasteScale
    
)