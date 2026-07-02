
import bpy
import sys
import os

if len(sys.argv) < 5:
    print("Usage: blender -b -P blender_script.py -- <import_path> <import_ext> <export_path> <export_ext>")
    sys.exit(1)

import_path = sys.argv[5]
import_ext = sys.argv[6]
export_path = sys.argv[7]
export_ext = sys.argv[8]

if import_ext == '.stl':
    bpy.ops.wm.stl_import(filepath=import_path)
elif import_ext == '.obj':
    bpy.ops.wm.obj_import(filepath=import_path)
else:
    print("Unsupported import format")
    sys.exit(1)

# Check if any objects were imported
if bpy.context.selected_objects:
    # Select all objects for export
    bpy.ops.object.select_all(action='SELECT')

    if export_ext == '.ac':
        bpy.ops.export_scene.export_ac3d(filepath=export_path)
        print("AC3D exported")
    else:
        print("Unsupported export format")
        sys.exit(1)

# Remove all objects from the scene
while bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects[0], do_unlink=True)
    