import slicer
import os
import json
import sys

def crop_roi(volume_path, roi_pre_path, roi_post_path, vertebra_path, output_dir):
    """
    Performs scissors-based ROI cropping in 3D Slicer.
    Combines pre and post .obj files into a segmentation and crops it using scissors.
    """
    patient_id = os.path.splitext(os.path.splitext(os.path.basename(volume_path))[0])[0]
    segment_names = [
        os.path.splitext(os.path.basename(roi_post_path))[0],
        os.path.splitext(os.path.basename(roi_pre_path))[0],
        os.path.splitext(os.path.basename(vertebra_path))[0]
    ]

    os.makedirs(output_dir, exist_ok=True)
    volume_node = slicer.util.loadVolume(volume_path)

    def import_model_as_segmentation(model_path, segment_name):
        slicer.util.loadModel(model_path)
        model_node = slicer.util.getNode(segment_name)
        segmentation_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segmentation_node.SetName(segment_name)
        slicer.modules.segmentations.logic().ImportModelToSegmentationNode(model_node, segmentation_node)
        slicer.mrmlScene.RemoveNode(model_node)

    import_model_as_segmentation(roi_post_path, segment_names[0])
    import_model_as_segmentation(roi_pre_path,  segment_names[1])
    import_model_as_segmentation(vertebra_path,  segment_names[2])

    colors = [[1, 0, 0], [1, 1, 0], [0.5, 0.25, 0]]
    segmentations = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')

    for i, seg in enumerate(segmentations):
        if i < len(colors):
            segment = seg.GetSegmentation().GetSegment(seg.GetSegmentation().GetNthSegmentID(0))
            segment.SetColor(colors[i])

    seg_post = slicer.util.getNode(segment_names[0])
    seg_pre = slicer.util.getNode(segment_names[1])
    seg_pre_id = seg_pre.GetSegmentation().GetNthSegmentID(0)
    seg_post.GetSegmentation().CopySegmentFromSegmentation(seg_pre.GetSegmentation(), seg_pre_id)
    seg_post.SetName("ROI_segmented")
    slicer.mrmlScene.RemoveNode(seg_pre)

    # Setup Segment Editor for cropping
    slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpYellowSliceView)
    slicer.app.processEvents()
    slicer.util.selectModule('SegmentEditor')

    editor = slicer.modules.SegmentEditorWidget.editor
    editor.setSegmentationNode(seg_post)
    editor.setSourceVolumeNode(volume_node)

    if editor:
        effect = editor.effectByName("Scissors")
        editor.setActiveEffect(effect)
        if effect:
            effect.setParameter("Operation", "EraseOutside")
            effect.setParameter("ApplyToAllVisibleSegments", "1")
            effect.setParameter("Shape", "FreeForm")
            effect.setParameter("SliceCutMode", "Unlimited")

    # Save final result
    output_segmentation_path = os.path.join(output_dir, "ROI_segmented.nrrd")
    slicer.util.saveNode(seg_post, output_segmentation_path)
    print(f"✅ Saved cropped segmentation to: {output_segmentation_path}")

    # Save optional outputs
    scene_path = os.path.join(output_dir, "Scene_Case.mrml")
    slicer.util.saveScene(scene_path)

    outputs = {
        "segmentation_path": output_segmentation_path,
        "scene_path": scene_path
    }
    with open(os.path.join(output_dir, "crop_outputs.json"), "w") as f:
        json.dump(outputs, f)

def find_file_by_keywords(folder, keywords):
    for f in os.listdir(folder):
        name = f.lower()
        if f.lower().endswith(".obj") and all(k in name for k in keywords):
            return os.path.join(folder, f)
    return None

def main():
    json_path = sys.argv[1]
    with open(json_path, 'r') as f:
        data = json.load(f)

    reg_path = data["registration_path"]
    output_dir = data["output_dir"]
    patient_dir = data["patient_dir"]

    volume_path = next(
        (os.path.join(patient_dir, f) for f in os.listdir(patient_dir)
         if f.lower().endswith(".nii.gz") and "post" in f.lower()),
        None
    )
    if not volume_path:
        raise FileNotFoundError("❌ POST volume (.nii.gz) not found in patient directory.")

    roi_post_path = find_file_by_keywords(reg_path, ["post"])
    roi_pre_path = find_file_by_keywords(reg_path, ["pre"])
    vertebra_path = find_file_by_keywords(reg_path, ["vertebra"])

    if not all([roi_post_path, roi_pre_path, vertebra_path]):
        raise FileNotFoundError("❌ One or more .obj files missing in registration folder.")

    crop_roi(volume_path, roi_pre_path, roi_post_path, vertebra_path, output_dir)
    slicer.util.exit()

if __name__ == "__main__":
    main()
