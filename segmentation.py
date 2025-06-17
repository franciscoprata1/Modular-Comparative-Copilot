import os
import numpy as np
import nibabel as nib
from scipy.ndimage import gaussian_filter
import tempfile
import subprocess
import gc
import shutil


SEGMENTATION_TOOLS = {
    "total_segmentator": {
        "ct": {
            "roi_options": [
                "spinal_cord",
                "iliopsoas"
            ],
            "other_options": [
                "none",
                *[f"vertebrae_T{i}" for i in range(1, 13)],
                *[f"vertebrae_L{i}" for i in range(1, 6)],
                "vertebrae_S1",
                "sacrum",
                "autochthon_left",
                "autochthon_right"
            ]
        },
        "mr": {
            "roi_options": [
                "spinal_cord",
                "iliopsoas_left",
                "iliopsoas_right"
            ],
            "other_options": [
                "none",
                "vertebrae",
                "sacrum",
                "intervertebral_discs",
                "autochthon_left",
                "autochthon_right"
            ]
        }
    }
}


def run_totalsegmentator(input_path, output_path, roi_subset, modality="ct", use_fast=False):
    task = "total_mr" if modality == "mr" else "total"
    command = [
        "TotalSegmentator",
        "-i", input_path,
        "-o", output_path,
        "--task", task,
        "--roi_subset"
    ] + roi_subset + ["--output_type", "nifti"]

    if use_fast:
        command.append("--fast")

    subprocess.run(command, check=True)
    print(f"✅ TotalSegmentator finished — ROI subset: {roi_subset}, modality: {modality}, fast: {use_fast}")
    gc.collect()


def smooth_segmentation(seg_img):
    data = seg_img.get_fdata()
    smoothed = np.zeros_like(data)
    voxel_spacing = seg_img.header.get_zooms()
    sigma = 0.8 / np.sqrt(np.prod(voxel_spacing))

    for label in np.unique(data):
        if label == 0:
            continue
        mask = data == label
        smoothed_mask = gaussian_filter(mask.astype(float), sigma)
        smoothed[smoothed_mask > 0.5] = label

    del data  # Explicit memory release
    gc.collect()

    return nib.Nifti1Image(smoothed, seg_img.affine)


def save_segmentation(seg_img, output_path):
    nib.save(seg_img, output_path)
    print(f"💾 Saved: {output_path}")
    del seg_img  # Explicit memory release
    gc.collect()


def combine_segmentations_spinal_cord(input_path, temp_dir, levels, output_path):
    """
    Combines spinal cord and vertebra pairs into single masks without saving unused segmentations.
    """
    base_img = nib.load(input_path)
    affine = base_img.affine
    outputs = []

    def get_label_filename(anatomical_label):
        return next((fname for fname in os.listdir(temp_dir)
                     if fname.startswith(anatomical_label) and fname.endswith(".nii.gz")), None)

    spinal_file = get_label_filename("spinal_cord")
    if not spinal_file:
        raise FileNotFoundError("Spinal cord mask not found!")

    spinal_data = nib.load(os.path.join(temp_dir, spinal_file)).get_fdata()

    for i in range(0, len(levels), 2):
        vertebra_sup = levels[i]
        vertebra_inf = levels[i + 1]

        fname_sup = get_label_filename(f"vertebrae_{vertebra_sup}")
        fname_inf = get_label_filename(f"vertebrae_{vertebra_inf}")

        if not fname_sup or not fname_inf:
            print(f"⚠️ Skipping pair {vertebra_sup}-{vertebra_inf}, missing segmentation.")
            continue

        sup_data = nib.load(os.path.join(temp_dir, fname_sup)).get_fdata()
        inf_data = nib.load(os.path.join(temp_dir, fname_inf)).get_fdata()

        # Create combined mask
        combined = np.zeros(base_img.shape, dtype=np.uint8)
        combined[spinal_data > 0] = 1
        combined[sup_data > 0] = 2
        combined[inf_data > 0] = 3

        # Save combined mask
        name = f"{vertebra_sup}_{vertebra_inf}"
        output_path_combined = os.path.join(output_path, f"Segmentation_{name}.nii.gz")
        save_segmentation(nib.Nifti1Image(combined, affine), output_path_combined)

        # Append tuple (path, name)
        outputs.append((output_path_combined, name))

        # Memory release
        del sup_data, inf_data, combined
        gc.collect()

    del spinal_data
    gc.collect()

    return outputs


def combine_segmentations_iliopsoas(input_path, temp_dir, levels, output_path):
    """
    Combines iliopsoas (left and right) and vertebra pairs into single masks without saving unused segmentations.
    """
    base_img = nib.load(input_path)
    affine = base_img.affine
    outputs = []

    def get_label_filename(anatomical_label):
        return next((fname for fname in os.listdir(temp_dir)
                     if fname.startswith(anatomical_label) and fname.endswith(".nii.gz")), None)

    psoas_left_file = get_label_filename("iliopsoas_left")
    psoas_right_file = get_label_filename("iliopsoas_right")

    if not psoas_left_file or not psoas_right_file:
        print("⚠️ Iliopsoas masks not found!")
        return []

    psoas_left_data = nib.load(os.path.join(temp_dir, psoas_left_file)).get_fdata()
    psoas_right_data = nib.load(os.path.join(temp_dir, psoas_right_file)).get_fdata()

    for i in range(0, len(levels), 2):
        vertebra_sup = levels[i]
        vertebra_inf = levels[i + 1]

        fname_sup = get_label_filename(f"vertebrae_{vertebra_sup}")
        fname_inf = get_label_filename(f"vertebrae_{vertebra_inf}")

        if not fname_sup or not fname_inf:
            print(f"⚠️ Skipping pair {vertebra_sup}-{vertebra_inf}, missing segmentation.")
            continue

        sup_data = nib.load(os.path.join(temp_dir, fname_sup)).get_fdata()
        inf_data = nib.load(os.path.join(temp_dir, fname_inf)).get_fdata()

        # Create combined mask
        combined = np.zeros(base_img.shape, dtype=np.uint8)
        combined[psoas_left_data > 0] = 1
        combined[psoas_right_data > 0] = 2
        combined[sup_data > 0] = 3
        combined[inf_data > 0] = 4

        # Save combined mask
        name = f"{vertebra_sup}_{vertebra_inf}"
        output_path_combined = os.path.join(output_path, f"Segmentation_{name}.nii.gz")
        save_segmentation(nib.Nifti1Image(combined, affine), output_path_combined)

        # Append tuple (path, name)
        outputs.append((output_path_combined, name))

        # Memory release
        del sup_data, inf_data, combined
        gc.collect()

    del psoas_left_data, psoas_right_data
    gc.collect()

    return outputs


def segmentation_process(patient, visit_type):
    try:
        print(f"\n🔍 SEGMENTING — Patient {patient.patient_number} | Visit: {visit_type}")
        visit = patient.pre if visit_type == "PRE" else patient.post
        nifti_path = visit.nifti_path
        output_path = visit.visit_output_path
        modality = visit.modality or "ct"
        use_fast = patient.use_fast 

        if not nifti_path or not os.path.exists(nifti_path):
            print(f"⚠️ Missing NIfTI file for {visit_type}")
            return

        vertebrae = patient.levels
        if len(vertebrae) < 2 or len(vertebrae) % 2 != 0:
            raise ValueError("Levels must be provided in pairs (e.g., L4-L5, L2-L3)")

        # ✅ Determine ROI subset
        roi_subset = []
        if patient.roi == "spinal_cord":
            roi_subset = [patient.roi] + patient.other + [f"vertebrae_{v}" for v in vertebrae]
        elif patient.roi == "iliopsoas":
            roi_subset = ["iliopsoas_left", "iliopsoas_right"] + patient.other + [f"vertebrae_{v}" for v in vertebrae]
        else:
            raise NotImplementedError(f"ROI '{patient.roi}' not implemented for segmentation.")

        print(f"ROI Subset: {roi_subset}")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Run TotalSegmentator with the determined ROI subset
            run_totalsegmentator(
                input_path=nifti_path,
                output_path=temp_dir,
                roi_subset=roi_subset,
                modality=modality,
                use_fast=use_fast
            )

            # Combine segmentations based on ROI
            if patient.roi == "spinal_cord":
                combined_imgs = combine_segmentations_spinal_cord(nifti_path, temp_dir, vertebrae, output_path)
            elif patient.roi == "iliopsoas":
                combined_imgs = combine_segmentations_iliopsoas(nifti_path, temp_dir, vertebrae, output_path)

            # Debugging: Print the structure of combined_imgs
            print(f"combined_imgs structure: {combined_imgs}")

            seg_paths = []
            for img_path, name in combined_imgs:
                # Load the NIfTI file before processing
                img = nib.load(img_path)
                smoothed = smooth_segmentation(img)
                out_path = os.path.join(output_path, f"Segmentation_{name}.nii.gz")
                save_segmentation(smoothed, out_path)
                seg_paths.append(out_path)

        visit.log_segmentation(seg_paths)

    except Exception as e:
        print(f"❌ Segmentation failed for Patient {patient.patient_number} | Visit: {visit_type}")
        print(f"   ↳ Error: {e}")
        gc.collect()

