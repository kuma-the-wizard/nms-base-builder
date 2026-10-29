"""Explicit Apply/Cancel editor for advanced build ownership metadata."""
import copy
from .build_metadata import OWNER_FIELDS, encode, edited_owner, field_text, approve_save_owner, clear_save_approvals
import bpy
from bpy.app.handlers import persistent


@persistent
def reset_save_approval(_=None):
    # PropertyGroup SKIP_SAVE is not a reliable .blend boundary. Approval is
    # deliberately cleared on file load and add-on enable, in every scene.
    clear_save_approvals()
    scenes = getattr(bpy.data, 'scenes', None)
    if scenes is None:
        return 0.1  # Add-on enable can run under Blender's restricted data context.
    for scene in scenes:
        props = getattr(scene, 'nms_base_tool', None)
        if props is not None:
            props.metadata_owner_to_save = False
            props.metadata_owner_reviewed = ''


def register_handlers():
    if reset_save_approval not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(reset_save_approval)
    if reset_save_approval() is not None and not bpy.app.timers.is_registered(reset_save_approval):
        bpy.app.timers.register(reset_save_approval, first_interval=0.0)


def unregister_handlers():
    if reset_save_approval in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(reset_save_approval)
    if bpy.app.timers.is_registered(reset_save_approval):
        bpy.app.timers.unregister(reset_save_approval)
    reset_save_approval()


class BBE_OT_build_metadata(bpy.types.Operator):
    bl_idname = 'bbe.build_metadata'
    bl_label = 'Advanced Build Metadata'
    bl_description = 'Edit this build\'s Owner record and metadata; changes apply to this Blender project first'
    bl_options = {'UNDO'}
    owner_usn: bpy.props.StringProperty(name='Owner name (USN)')
    owner_uid: bpy.props.StringProperty(name='User ID (UID)')
    owner_lid: bpy.props.StringProperty(name='LID')
    owner_ptk: bpy.props.StringProperty(name='PTK')
    owner_ts: bpy.props.StringProperty(name='Owner timestamp (TS)')
    last_editor_id: bpy.props.StringProperty(name='Last editor ID')
    last_editor_name: bpy.props.StringProperty(name='Last editor name')
    owner_to_save: bpy.props.BoolProperty(name='Include this Owner when exporting to a game save', default=False,
        description='Explicitly update the chosen destination build Owner on your next confirmed export; importing a build never enables this')

    def invoke(self, context, event):
        props = context.scene.nms_base_tool
        self._scene = context.scene
        self._original = props.serialise()
        self._signature = encode(self._original)
        owner = self._original.get('Owner', {})
        if not isinstance(owner, dict):
            self.report({'ERROR'}, 'This build has an unsupported Owner record; no metadata changed.')
            return {'CANCELLED'}
        for key in OWNER_FIELDS:
            setattr(self, 'owner_' + key.lower(), field_text(owner.get(key)))
        self.last_editor_id = field_text(self._original.get('LastEditedById'))
        self.last_editor_name = field_text(self._original.get('LastEditedByUsername'))
        self.owner_to_save = props.metadata_owner_to_save
        return context.window_manager.invoke_props_dialog(self, width=570, confirm_text='Apply to Build')

    def draw(self, context):
        layout = self.layout
        layout.label(text='Edit this build\'s Owner record. Ship slot links stay unchanged.', icon='INFO')
        layout.label(text='Full build files and clipboard exports retain these fields.')
        column = layout.column(align=True)
        for key in OWNER_FIELDS:
            column.prop(self, 'owner_' + key.lower())
        layout.separator()
        layout.prop(self, 'last_editor_name')
        layout.prop(self, 'last_editor_id')
        layout.separator()
        layout.prop(self, 'owner_to_save')
        layout.label(text='Unchecked: game-save exports keep the destination Owner.')
        layout.label(text='Apply changes this project. Export confirmation writes the save.')
        layout.label(text='Other imported metadata and extra Owner fields are preserved.')

    def execute(self, context):
        try:
            props = context.scene.nms_base_tool
            if (not hasattr(self, '_original') or context.scene != self._scene
                    or encode(props.serialise()) != self._signature):
                raise ValueError('The build changed. Reopen Advanced Build Metadata and review it again.')
            owner = edited_owner(self._original.get('Owner', {}),
                {key: getattr(self, 'owner_' + key.lower()) for key in OWNER_FIELDS})
            updated = copy.deepcopy(self._original)
            updated['Owner'] = owner
            for key, text in (('LastEditedById', self.last_editor_id),
                              ('LastEditedByUsername', self.last_editor_name)):
                if text != field_text(self._original.get(key)):
                    updated[key] = text
            props.deserialise_from_data(updated)
            approve_save_owner(props, self.owner_to_save)
        except (ValueError, TypeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Build metadata updated in this project.')
        return {'FINISHED'}


classes = (BBE_OT_build_metadata,)
