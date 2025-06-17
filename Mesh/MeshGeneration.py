import os
import sys
import json
import slicer
import vtk
import vtkSegmentationCorePython as vtkSeg

# Label-to-Anatomy Mapping
SPINAL_CORD_LABELS = {
    1: "SpinalCord",
    2: "Vertebra_Superior",
    3: "Vertebra_Inferior"
}

PSOAS_LABELS = {
    1: "Iliopsoas_Left",
    2: "Iliopsoas_Right",
    3: "Vertebra_Superior",
    4: "Vertebra_Inferior"
}

def rename_segments(segmentation_node, label_map):
    """
    Renames segments in the segmentation node based on the label map.
    """
    print(f"Renaming segments using label map: {label_map}")
    segmentation = segmentation_node.GetSegmentation()
    for i in range(segmentation.GetNumberOfSegments()):
        segment_id = segmentation.GetNthSegmentID(i)
        segment = segmentation.GetSegment(segment_id)
        original_name = segment.GetName()

        # Match based on label index (e.g., Segment_1, Segment_2, etc.)
        for label_idx, label_name in label_map.items():
            if original_name == f"Segment_{label_idx}":
                segment.SetName(label_name)
                print(f"Renamed segment '{original_name}' to '{label_name}'")
                break

def export_meshes(segmentation_node, output_dir):
    """
    Exports all segments in the segmentation node as individual .obj files.
    """
    print(f"Exporting meshes to: {output_dir}")
    
    # Access the Subject Hierarchy node
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    exportFolderItemId = shNode.CreateFolderItem(shNode.GetSceneItemID(), "Segments")

    # Export all segments to models
    slicer.modules.segmentations.logic().ExportAllSegmentsToModels(segmentation_node, exportFolderItemId)

    # Get all model nodes created
    modelNodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLModelNode")
    modelNodes.UnRegister(slicer.mrmlScene)  # Avoid memory leaks

    # Save each model node as a separate .obj file
    for modelNode in modelNodes:
        modelName = modelNode.GetName()
        file_path = os.path.join(output_dir, f"{modelName}.obj")
        slicer.util.saveNode(modelNode, file_path)
        print(f"✅ Saved mesh: {file_path}")

def clean_output_folder(output_dir, keep_labels):
    """
    Keeps only the .obj files corresponding to the given labels.
    Deletes all .mtl files and any .obj files not matching keep_labels.
    """
    keep_obj_filenames = {f"{label}.obj" for label in keep_labels}

    for fname in os.listdir(output_dir):
        full_path = os.path.join(output_dir, fname)

        # Always delete .mtl files
        if fname.endswith(".mtl"):
            os.remove(full_path)
            print(f"🗑️ Deleted material file: {full_path}")

        # Delete unwanted .obj files
        elif fname.endswith(".obj") and fname not in keep_obj_filenames:
            os.remove(full_path)
            print(f"🗑️ Deleted mesh file: {full_path}")


def main():
    # Read the input JSON string
    print("Reading input JSON...")
    json_path = sys.argv[1]
    print(f"📄 Reading input from file: {json_path}")

    try:
        with open(json_path, 'r') as f:
            mesh_input = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return

    segmentation_path = mesh_input["segmentation_path"]
    output_dir = mesh_input["output_dir"]

    print(f"Segmentation Path: {segmentation_path}")
    print(f"Output Directory: {output_dir}")

    if not os.path.exists(segmentation_path):
        print(f"❌ Segmentation file not found: {segmentation_path}")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Load the segmentation
    print("Loading segmentation...")
    segmentation_node = slicer.util.loadSegmentation(segmentation_path)
    if not segmentation_node:
        print(f"❌ Failed to load segmentation: {segmentation_path}")
        return

    # Determine anatomical context using roi attribute
    roi = mesh_input.get("roi", "").lower()

    if roi == "spinal_cord":
        label_map = SPINAL_CORD_LABELS
    elif roi == "iliopsoas":
        label_map = PSOAS_LABELS
    else:
        print(f"❌ Unsupported ROI '{roi}' in mesh input.")
        return

    # Rename segments based on label map
    rename_segments(segmentation_node, label_map)

    # Export meshes
    export_meshes(segmentation_node, output_dir)

    # Clean up extraneous files
    keep_labels = list(label_map.values())
    clean_output_folder(output_dir, keep_labels)

    print(f"✅ Mesh generation completed for: {os.path.basename(segmentation_path)}")
    
    # ✅ Automatically close Slicer
    slicer.util.exit()

if __name__ == "__main__":
    main()
