import os
import shutil
import dicom2nifti
import nibabel as nib
import pydicom
import numpy as np


def convert_dicom_to_nifti(series_dir, output_path, output_name, overwrite=True):
    os.makedirs(output_path, exist_ok=True)
    out_path = os.path.join(output_path, f"{output_name}.nii.gz")
    if os.path.exists(out_path) and not overwrite:
        return out_path
    try:
        dicom2nifti.dicom_series_to_nifti(series_dir, out_path, reorient_nifti=True)
        return out_path
    except Exception as e:
        print(f"❌ Conversion failed for {series_dir}: {e}")
        return None


def list_nifti_series(folder_path):
    """
    Lists all NIfTI files inside a folder and loads them with nibabel.
    Returns a list of (path, nib_image) tuples.
    """
    import os
    import nibabel as nib

    nifti_series = []
    for file in os.listdir(folder_path):
        if file.endswith(".nii") or file.endswith(".nii.gz"):
            path = os.path.join(folder_path, file)
            try:
                img = nib.load(path)
                nifti_series.append((path, img))
            except Exception as e:
                print(f"❌ Failed to load NIfTI: {file} — {e}")
    return nifti_series


def is_dicom_folder(path):
    """
    Quick check to see if a folder contains DICOM files.
    """
    return any(f.lower().endswith('.dcm') for f in os.listdir(path))


def list_all_series(sorted_folder):
    """
    Lists all NIfTI and DICOM series in a folder with metadata.
    Returns a list of (path, type) where type is 'nifti' or 'dicom'.
    """
    import pydicom
    series_list = []

    for item in os.listdir(sorted_folder):
        full_path = os.path.join(sorted_folder, item)

        if full_path.endswith((".nii", ".nii.gz")):
            try:
                img = nib.load(full_path)
                shape = img.shape
                voxel = tuple(round(v, 3) for v in img.header.get_zooms())
                print(f"{len(series_list)+1}. {os.path.basename(full_path)} — NIFTI — Shape: {shape} — Voxel size: {voxel}")
                series_list.append((full_path, "nifti"))
            except Exception as e:
                print(f"⚠️ Could not read NIfTI: {full_path} — {e}")

        elif os.path.isdir(full_path) and is_dicom_folder(full_path):
            try:
                dcm_files = sorted([
                    os.path.join(full_path, f)
                    for f in os.listdir(full_path)
                    if f.lower().endswith(".dcm")
                ])
                if not dcm_files:
                    continue
                sample = pydicom.dcmread(dcm_files[0])
                shape = sample.pixel_array.shape
                pixel_spacing = getattr(sample, "PixelSpacing", [1.0, 1.0])
                slice_thickness = getattr(sample, "SliceThickness", 1.0)
                voxel = tuple(round(float(v), 3) for v in list(pixel_spacing) + [slice_thickness])
                num_slices = len(dcm_files)
                print(f"{len(series_list)+1}. {os.path.basename(full_path)} — DICOM — Shape: {shape} — Voxel size: {voxel} — Num slices: {num_slices}")
                series_list.append((full_path, "dicom"))
            except Exception as e:
                print(f"⚠️ Could not read DICOM folder: {full_path} — {e}")

    return series_list

def automatic_image_selection(series_list):
    import nibabel as nib
    import pydicom
    import os

    candidates = []

    for path, kind in series_list:
        try:
            if kind == "nifti":
                img = nib.load(path)
                shape = img.shape
                zooms = img.header.get_zooms()

                if len(shape) < 3 or len(zooms) < 3:
                    continue

                if shape[0]/zooms[0] < 50 or shape[1]/zooms[1] < 50 or shape[2]/zooms[2] < 50:
                    print(f"⚠️ Skipping {os.path.basename(path)} — too few voxels: {shape}")
                    continue

                print(f"📐 {os.path.basename(path)} — size x/y/z: {shape}, spacing x/y/z: {zooms}")
                score = shape[0] + shape[1] + shape[2]
                voxel_volume = zooms[0] * zooms[1] * zooms[2]

            elif kind == "dicom":
                files = [f for f in os.listdir(path) if f.lower().endswith(".dcm")]
                if not files:
                    continue

                num_slices = len(files)
                if num_slices < 50:
                    print(f"⚠️ Skipping {os.path.basename(path)} — too few slices: {num_slices}")
                    continue

                sample = pydicom.dcmread(os.path.join(path, files[0]), stop_before_pixels=True)
                spacing = getattr(sample, "PixelSpacing", [1.0, 1.0])
                spacing_x, spacing_y = float(spacing[0]), float(spacing[1])
                thickness = float(getattr(sample, "SliceThickness", 1.0))
                rows = int(getattr(sample, "Rows", 0))
                cols = int(getattr(sample, "Columns", 0))

                print(f"📐 {os.path.basename(path)} — slices: {num_slices}, rows: {rows}, cols: {cols}, spacing: {spacing_x}/{spacing_y}, thickness: {thickness}")
                score = num_slices + cols + rows
                voxel_volume = spacing_x * spacing_y * thickness

            else:
                continue

            candidates.append((path, kind, score, voxel_volume))

        except Exception as e:
            print(f"⚠️ Skipping {path}: {e}")
            continue

    if not candidates:
        print("❌ No valid series found for automatic selection.")
        return None, None

    # Stage 1: Get max anatomical score
    max_score = max(c[2] for c in candidates)
    threshold = 0.8 * max_score

    # Stage 2: Filter top 10% and select lowest voxel volume
    top_candidates = [c for c in candidates if c[2] >= threshold]
    top_candidates.sort(key=lambda c: c[3])  # sort by voxel volume ascending

    selected = top_candidates[0]
    print(f"✅ Automatically selected: {os.path.basename(selected[0])} ({selected[1]}) — Score: {selected[2]:.2f}, Voxel volume: {selected[3]:.4f}")
    return selected[0], selected[1]
