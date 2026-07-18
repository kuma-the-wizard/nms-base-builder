
import bpy


# Workspace Cleanup
def cleanup_workspace(context) -> None:
    
    new_workspace_name = "No Man's Sky Base & Corvette Builder"
    
    layout_ws = bpy.data.workspaces.get("Layout")
    if layout_ws is None:
        return

    # Snapshot list before iterating because collection changes during deletion
    other_workspaces = [ws for ws in bpy.data.workspaces if ws != layout_ws]
    for ws in other_workspaces:
        with bpy.context.temp_override(workspace=ws):
            bpy.ops.workspace.delete()

    # switch to Layout and rename it
    win = context.window
    win.workspace = layout_ws
    layout_ws.name = new_workspace_name
    
    # active screen after the workspace switch
    screen = win.screen
    
    # take a snapshot of the areas we want to close in one pass
    areas_to_close = [
        area for area in screen.areas 
        if area.type == "PROPERTIES" or 
        (area.type == "DOPESHEET_EDITOR" and area.spaces.active.mode == "TIMELINE")
    ]
    
    # close areas
    for area in areas_to_close:
        with bpy.context.temp_override(window=win, screen=screen, area=area):
            bpy.ops.screen.area_close()
            
    # Hide status bar
    for s in bpy.data.screens:
        s.show_statusbar = False
        
