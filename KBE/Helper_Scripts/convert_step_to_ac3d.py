"Script imported from Aerolympic Internal files. This script was used for a glider KBE application and was adapted for our airship"
import subprocess
import sys
import os
import env_Arnesh as env

_HERE = os.path.dirname(os.path.abspath(__file__))


def run_freecad_conversion(input_file, intermediate_file):
    """Convert STEP to STL/OBJ using FreeCAD."""
    freecad_script = """
import sys
import FreeCAD
import Part
import Mesh
import MeshPart

import os

def convert_stp_to_mesh(input_file):
    try:
        print(f"Loading STEP file: {input_file}")
        doc = FreeCAD.newDocument()
        shape = Part.Shape()
        shape.read(input_file)
        print("STEP file read successfully.")

        print("Creating part object...")
        part = doc.addObject("Part::Feature", "Part")
        part.Shape = shape
        print("Part object created.")

        if not part.Shape.isValid():
            raise ValueError("The shape loaded from the STEP file is invalid.")

        print("Meshing the part...")
        mesh = MeshPart.meshFromShape(Shape=part.Shape, LinearDeflection=0.05, AngularDeflection=0.15523599)

        if mesh is None or len(mesh.Facets) == 0:
            raise ValueError("The mesh could not be created or is empty.")
        print("Part meshed successfully.")

        return mesh

    except Exception as e:
        print(f"An error occurred: {e}")
        try:
            FreeCAD.closeDocument(doc.Name)
        except:
            pass
        return None

def export_mesh(mesh, output_file):
    try:
        if output_file.lower().endswith('.stl'):
            print(f"Exporting mesh to STL file: {output_file}")
            mesh.write(output_file, "STL")
        elif output_file.lower().endswith('.obj'):
            print(f"Exporting mesh to OBJ file: {output_file}")
            mesh.write(output_file, "OBJ")
        else:
            raise ValueError("Unsupported file extension. Please use .stl or .obj.")
        print("Mesh exported successfully.")

    except Exception as e:
        print(f"An error occurred during export: {e}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python convert_step_to_mesh.py <input_file.stp> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist.")
        sys.exit(1)

    mesh = convert_stp_to_mesh(input_file)

    if mesh:
        export_mesh(mesh, output_file)

    try:
        FreeCAD.closeDocument(FreeCAD.ActiveDocument.Name)
    except:
        pass

if __name__ == "__main__":
    main()
    """

    mesh_script_path = os.path.join(_HERE, 'convert_step_to_mesh.py')
    with open(mesh_script_path, 'w') as f:
        f.write(freecad_script)

    # Run FreeCAD conversion
    subprocess.run(
        [env.dir_FREECAD + "/bin/python.exe", mesh_script_path, input_file, intermediate_file],
        check=True
    )


def run_blender_conversion(intermediate_file, export_file):
    """Convert STL/OBJ to AC3D using Blender."""
    blender_script = """
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
    """

    ac_script_path = os.path.join(_HERE, 'convert_to_ac3d.py')
    with open(ac_script_path, 'w') as f:
        f.write(blender_script)

    # Run Blender conversion
    subprocess.run([
        env.dir_BLENDER, "--background", "--python", ac_script_path,
        "--", intermediate_file, os.path.splitext(intermediate_file)[1], export_file, ".ac"
    ], check=True)


def main():
    if len(sys.argv) != 4:
        print("Usage: python convert_step_to_ac3d.py <input_file.stp> <intermediate_file> <output_file.ac>")
        sys.exit(1)

    input_file = sys.argv[1]
    intermediate_file = sys.argv[2]
    export_file = sys.argv[3]

    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist.")
        sys.exit(1)

    run_freecad_conversion(input_file, intermediate_file)
    run_blender_conversion(intermediate_file, export_file)


if __name__ == "__main__":
    main()