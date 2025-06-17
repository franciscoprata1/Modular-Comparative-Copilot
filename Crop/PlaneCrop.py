import os
import vtk
import numpy as np
import slicer
import vtkSegmentationCorePython as vtkSeg
from qt import QDialog, QVBoxLayout, QLabel, QPushButton
import json
import sys

sac_seg_node = None
line_up_node = None
line_down_node = None
base_path = None

def load_data_and_prepare_editor(local_base_path, local_output_dir, patient_dir, patient_id, base_name):
    global sac_seg_node, line_up_node, line_down_node, base_path, output_dir
    base_path = local_base_path
    output_dir = local_output_dir

    # Files
    volume_path = os.path.join(patient_dir, "POST", f"PATIENT_{patient_id}_POST.nii.gz")
    roi_pre_path = os.path.join(base_path, f"{base_name}_PRE_registered.obj")
    roi_post_path = os.path.join(base_path, f"{base_name}_POST_registered.obj")
    vertebrae_path = os.path.join(base_path, f"{base_name}_Vertebrae.obj")

    # Load volume
    volumeNode = slicer.util.loadVolume(volume_path)
    if not volumeNode:
        print("❌ Failed to load volume")
        return

    # Create segmentation nodes
    sac_seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentation_DuralSac")
    sac_seg_node.SetReferenceImageGeometryParameterFromVolumeNode(volumeNode)

    vertebrae_seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentation_Vertebrae")
    vertebrae_seg_node.SetReferenceImageGeometryParameterFromVolumeNode(volumeNode)

    # Import PRE model as segment
    pre_model = slicer.util.loadModel(roi_pre_path)
    pre_model.SetName("PRE")
    slicer.modules.segmentations.logic().ImportModelToSegmentationNode(pre_model, sac_seg_node)
    sac_seg_node.GetSegmentation().GetNthSegment(0).SetName("PRE")

    # Import POST model as segment
    post_model = slicer.util.loadModel(roi_post_path)
    post_model.SetName("POST")
    slicer.modules.segmentations.logic().ImportModelToSegmentationNode(post_model, sac_seg_node)
    sac_seg_node.GetSegmentation().GetNthSegment(1).SetName("POST")

    # ✅ Set segment colors (correct method)
    sac_seg_node.GetSegmentation().GetSegment("PRE").SetColor(0.0, 1.0, 0.0)   # Green
    sac_seg_node.GetSegmentation().GetSegment("POST").SetColor(1.0, 0.0, 0.0)  # Red

    # Import Vertebrae model as segment
    vertebrae_model = slicer.util.loadModel(vertebrae_path)
    vertebrae_model.SetName("Vertebrae")
    slicer.modules.segmentations.logic().ImportModelToSegmentationNode(vertebrae_model, vertebrae_seg_node)
    vertebrae_seg_node.GetSegmentation().GetNthSegment(0).SetName("Vertebrae")

    for i in range(sac_seg_node.GetSegmentation().GetNumberOfSegments()):
        segment_id = sac_seg_node.GetSegmentation().GetNthSegmentID(i)
        print(f"Segment {i}: {segment_id}")

    # Validation
    if not sac_seg_node.GetSegmentation().GetSegment("PRE"):
        print("❌ Error: PRE segment not created.")
        return
    if not sac_seg_node.GetSegmentation().GetSegment("POST"):
        print("❌ Error: POST segment not created.")
        return

    print("✅ Nodes loaded successfully.")
    print("✅ Segmentations loaded and colored correctly.")

    # Switch to markups module
    slicer.util.selectModule("Markups")
    slicer.modules.markups.logic().StartPlaceMode(0)

    # Start cropping lines
    line_up_node = create_and_configure_line("Crop_Line_Up")



def create_and_configure_line(line_name):
    # Create Markups Line node
    line_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", line_name)

    # Configure line properties
    line_display_node = line_node.GetDisplayNode()
    line_display_node.SetVisibility(1)
    line_display_node.SetOpacity(50)
    line_display_node.SetGlyphScale(3)
    line_display_node.SetTextScale(0)

    print(f"✅ Configuration done for {line_name}.")

    # Show popup
    show_popup_window(line_node, line_name)

    return line_node


def show_popup_window(line_node, line_name):
    dialog = QDialog()
    dialog.setWindowTitle("Line created")
    dialog_layout = QVBoxLayout(dialog)

    label = QLabel(f"The line '{line_node.GetName()}' has been created. Add at least two points to enable saving.")
    dialog_layout.addWidget(label)

    ok_button = QPushButton("OK")
    ok_button.setEnabled(False)
    dialog_layout.addWidget(ok_button)

    def on_line_modified(caller, event):
        if line_node.GetNumberOfControlPoints() >= 2:
            ok_button.setEnabled(True)

    line_node.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, on_line_modified)

    ok_button.clicked.connect(lambda: save_line(line_node, dialog, line_name))

    dialog.show()


def save_line(line_node, dialog, line_name):
    global sac_seg_node, line_up_node, line_down_node, output_dir

    print(f"✅ Line saved: {line_node.GetName()}")
    dialog.close()

    if line_name == "Crop_Line_Up":
        line_up_node = line_node
        second_line_node = create_and_configure_line("Crop_Line_Down")
        activate_line_tool(second_line_node)
    elif line_name == "Crop_Line_Down":
        line_down_node = line_node

        if line_up_node.GetNumberOfControlPoints() < 2:
            print("❌ Error: Line_Markups_Up has insufficient points.")
            return
        if line_down_node.GetNumberOfControlPoints() < 2:
            print("❌ Error: Line_Markups_Down has insufficient points.")
            return

        plane_up, plane_down = generate_planes_from_lines(line_up_node, line_down_node)
        crop_segments_between_planes(sac_seg_node, plane_up, plane_down)
        save_cropped_segments_as_nrrd(sac_seg_node, output_dir)
        print("✅ Process complete.")

        slicer.util.exit()


def activate_line_tool(line_node):
    interaction_node = slicer.app.applicationLogic().GetInteractionNode()
    interaction_node.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place)
    slicer.modules.markups.logic().SetActiveListID(line_node)


def generate_planes_from_lines(line_up_node, line_down_node):
    def generate_plane_from_line(lineNode):
        p0 = np.array([0.0, 0.0, 0.0])
        p1 = np.array([0.0, 0.0, 0.0])
        lineNode.GetNthControlPointPosition(0, p0)
        lineNode.GetNthControlPointPosition(1, p1)

        v1 = p1 - p0
        if np.linalg.norm(v1) < 1e-3:
            raise ValueError("Line has zero length.")
        v1 = v1 / np.linalg.norm(v1)

        reference = np.array([1, 0, 0]) if abs(v1[2]) > 0.9 else np.array([0, 0, 1])
        v2 = np.cross(v1, reference)
        if np.linalg.norm(v2) < 1e-3:
            reference = np.array([0, 1, 0])
            v2 = np.cross(v1, reference)
        v2 = v2 / np.linalg.norm(v2)

        normal = np.cross(v1, v2)
        normal = normal / np.linalg.norm(normal)
        center = (p0 + p1) / 2

        plane = vtk.vtkPlane()
        plane.SetOrigin(center.tolist())
        plane.SetNormal(normal.tolist())
        return plane

    def visualize_plane_3d(vtk_plane, name="VisualPlane", scale=100):
        plane_source = vtk.vtkPlaneSource()
        normal = np.array(vtk_plane.GetNormal())
        origin = np.array(vtk_plane.GetOrigin())
        reference = np.array([0, 0, 1]) if abs(normal[2]) < 0.9 else np.array([1, 0, 0])
        v1 = np.cross(normal, reference)
        v1 = v1 / np.linalg.norm(v1)
        v2 = np.cross(normal, v1)
        p1 = origin + v1 * scale
        p2 = origin + v2 * scale
        p3 = origin - v1 * scale
        p4 = origin - v2 * scale
        plane_source.SetOrigin(p3.tolist())
        plane_source.SetPoint1(p1.tolist())
        plane_source.SetPoint2(p2.tolist())
        plane_source.Update()
        model_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", name)
        model_node.SetAndObservePolyData(plane_source.GetOutput())
        display_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode")
        slicer.mrmlScene.AddNode(display_node)
        display_node.SetColor(1.0, 0.0, 0.0)
        display_node.SetOpacity(0.5)
        model_node.SetAndObserveDisplayNodeID(display_node.GetID())
        return model_node

    plane_up = generate_plane_from_line(line_up_node)
    plane_down = generate_plane_from_line(line_down_node)
    print("✅ Planes created.")
    visualize_plane_3d(plane_up, "Plane_Up")
    visualize_plane_3d(plane_down, "Plane_Down")
    print("✅ Planes ready for visualization.")
    return plane_up, plane_down


def crop_segments_between_planes(segmentation_node, plane_up, plane_down):
    logic = slicer.modules.segmentations.logic()
    original_ids = ["PRE", "POST"]

    for segment_id in original_ids:
        if not segmentation_node.GetSegmentation().GetSegment(segment_id):
            print(f"⚠️ Segment '{segment_id}' not found.")
            continue

        polyData = vtk.vtkPolyData()
        success = logic.GetSegmentRepresentation(
            segmentation_node,
            segment_id,
            vtkSeg.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName(),
            polyData
        )

        if not success or polyData.GetNumberOfPoints() == 0:
            print(f"❌ Could not obtain geometry of '{segment_id}'.")
            continue

        clipper_up = vtk.vtkClipPolyData()
        clipper_up.SetInputData(polyData)
        clipper_up.SetClipFunction(plane_up)
        clipper_up.InsideOutOff()
        clipper_up.Update()
        polyData_clipped_up = clipper_up.GetOutput()

        clipper_down = vtk.vtkClipPolyData()
        clipper_down.SetInputData(polyData_clipped_up)
        clipper_down.SetClipFunction(plane_down)
        clipper_down.InsideOutOn()
        clipper_down.Update()
        polyData_final = clipper_down.GetOutput()

        new_segment = vtkSeg.vtkSegment()
        new_segment.SetName(f"{segment_id}_Cropped")
        new_segment.AddRepresentation(
            vtkSeg.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName(),
            polyData_final
        )

        segmentation_node.GetSegmentation().AddSegment(new_segment)
        print(f"✅ Segment '{segment_id}_Cropped' created and added.")


def save_cropped_segments_as_nrrd(seg_node, output_dir):
    if not os.path.exists(output_dir):
        raise ValueError(f"❌ Directory does not exist: '{output_dir}'")

    segments_to_export = ["PRE_Cropped", "POST_Cropped"]

    for segmentID in segments_to_export:
        if not seg_node.GetSegmentation().GetSegment(segmentID):
            print(f"⚠️ Segment '{segmentID}' not found. Skipping.")
            continue

        tempSegNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", f"Temp_{segmentID}")
        tempSegNode.GetSegmentation().AddSegment(seg_node.GetSegmentation().GetSegment(segmentID))

        labelmapNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", f"{segmentID}_labelmap")
        slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(tempSegNode, labelmapNode)

        file_path = os.path.join(output_dir, f"{segmentID}.nrrd")
        slicer.util.saveNode(labelmapNode, file_path)
        print(f"✅ Segment '{segmentID}' saved to: {output_dir}")

        slicer.mrmlScene.RemoveNode(labelmapNode)
        slicer.mrmlScene.RemoveNode(tempSegNode)


def main():
    print("Reading input JSON...")
    json_path = sys.argv[1]
    print(f"📄 Reading input from file: {json_path}")

    try:
        with open(json_path, 'r') as f:
            crop_input = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return

    registration_path = crop_input["registration_path"]
    output_dir = crop_input["output_dir"]
    roi = crop_input["roi"]
    patient_id = crop_input["patient_id"]
    base_name = crop_input["base_name"]
    patient_dir = crop_input["patient_dir"]

    load_data_and_prepare_editor(registration_path, output_dir, patient_dir, patient_id, base_name)


if __name__ == "__main__":
    main()
