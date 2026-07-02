
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
    