import bpy
import webbrowser



class VisitDiscord(bpy.types.Operator):
    """Launch the community discord URL."""

    bl_idname = "object.nms_visit_community"
    bl_label = "Discord."

    def execute(self, context):
        # Load web page.
        webbrowser.open_new("https://discord.gg/kpGVRKPn5W")
        return {"FINISHED"}


class VisitGuides(bpy.types.Operator):
    """Launch the community discord URL."""

    bl_idname = "object.nms_visit_guides"
    bl_label = "Online Guides."

    def execute(self, context):
        # Load web page.
        webbrowser.open_new(
            "https://djmonkey.uk/no-mans-sky-base-builder-blender/guides/"
        )
        return {"FINISHED"}


class VisitPrefabDiscord(bpy.types.Operator):
    """Launch the community discord URL."""

    bl_idname = "object.nms_visit_prefab_community"
    bl_label = "from the Community Discord..."

    def execute(self, context):
        # Load web page.
        webbrowser.open_new("https://discord.gg/EqCXaFcd7Y")
        return {"FINISHED"}


class VisitGitHubRepo(bpy.types.Operator):
    """Launch the GitHub Repo URL."""

    bl_idname = "object.nms_visit_github"
    bl_label = "from the GitHub Repository..."

    def execute(self, context):
        # Load web page.
        webbrowser.open_new("https://djmonkeyuk.github.io/nms-base-builder-presets/")
        return {"FINISHED"}


classes = (
    VisitDiscord,
    VisitGuides,
    VisitPrefabDiscord,
    VisitGitHubRepo
)