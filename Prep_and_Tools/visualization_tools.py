import os
import numpy as np
import matplotlib.pyplot as plt
from skimage import exposure
import pydicom


def visualize_nifti_series(series_list, title_prefix="NIfTI Preview"):
    """
    Visualizes each NIfTI file's mid-slice in axial, sagittal, and coronal planes.
    Skips corrupted or incompatible volumes without crashing.
    """
    for i, (path, img) in enumerate(series_list):
        try:
            data = img.get_fdata()
            shape = data.shape
            voxel_sizes = img.header.get_zooms()

            mids = [s // 2 for s in shape]

            views = {
                "sagittal": (data[mids[0], :, :], voxel_sizes[2] / voxel_sizes[1]),
                "coronal":  (data[:, mids[1], :], voxel_sizes[2] / voxel_sizes[0]),
                "axial":    (data[:, :, mids[2]], voxel_sizes[1] / voxel_sizes[0])
            }

            fig, axes = plt.subplots(1, 3, figsize=(12, 4))
            fig.suptitle(f"{title_prefix} {i + 1}: {os.path.basename(path)}", fontsize=14)

            for ax, (plane, (sl, aspect)) in zip(axes, views.items()):
                sl = np.rot90(sl)
                sl = sl.astype(np.float32)
                sl = (sl - np.min(sl)) / (np.max(sl) - np.min(sl) + 1e-5)
                sl = exposure.equalize_adapthist(sl)

                ax.imshow(sl, cmap='gray', aspect=aspect)
                ax.set_title(plane)
                ax.axis('off')

            plt.title(f"NifTi preview: {os.path.basename(path)}")
            plt.tight_layout()
            plt.show()

        except Exception as e:
            print(f"❌ Failed to preview NIfTI: {path} — {e}")
            continue


def visualize_dicom_series(dicom_folder):
    """
    Loads and displays a representative mid-slice from a DICOM series.
    Robust against corrupted slices or inconsistent shape issues.
    """
    try:
        files = sorted([f for f in os.listdir(dicom_folder) if f.lower().endswith(".dcm")])
        slices = []

        for f in files:
            try:
                path = os.path.join(dicom_folder, f)
                dicom = pydicom.dcmread(path)
                slices.append(dicom.pixel_array)
            except Exception as e:
                print(f"⚠️ Skipping unreadable DICOM file: {f} — {e}")
                continue

        if not slices:
            print(f"❌ No valid DICOM slices found in {dicom_folder}")
            return

        try:
            volume = np.stack(slices, axis=0)
        except Exception as e:
            print(f"❌ Could not stack DICOM slices from {dicom_folder}: {e}")
            return

        mid_slice = volume[len(volume)//2]

        plt.figure(figsize=(5, 5))
        plt.imshow(mid_slice, cmap="gray")
        plt.title(f"DICOM preview: {os.path.basename(dicom_folder)}")
        plt.axis("off")
        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"❌ Failed to preview DICOM series at {dicom_folder} — {e}")