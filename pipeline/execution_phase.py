from segmentation import segmentation_process
from Mesh.execute_mesh import mesh_process
from registration import registration_process
from Patient_Analysis.execute_analysis import analysis_process
from StatAnalysis import global_spinal_cord_process, global_psoas_atrophy_process
import os

def _check_paths_exist(path_or_paths):
    """
    Handles both single path (str) and list of paths.
    Returns True only if the path(s) exist and list is not empty.
    """
    if isinstance(path_or_paths, list):
        if not path_or_paths:
            return False  # empty list means not done
        return all(os.path.exists(p) for p in path_or_paths)

    elif isinstance(path_or_paths, str):
        return os.path.exists(path_or_paths)

    return False


def is_step_done(patient, step_name, visit_type=None):
    if step_name == "segmentation":
        visit = patient.pre if visit_type == "PRE" else patient.post
        return _check_paths_exist(visit.segmentation_paths)

    elif step_name == "meshing":
        visit = patient.pre if visit_type == "PRE" else patient.post
        return _check_paths_exist(visit.mesh_paths)

    elif step_name == "registration":
        return _check_paths_exist(patient.registration_paths)

    elif step_name == "cropping":
        return _check_paths_exist(patient.crop_paths)

    elif step_name == "analysis":
        return _check_paths_exist(patient.analysis_paths)


def execute_analysis(patients, steps, crop_mode, slicer_path, excel_path, main_output_path, case1, case2):
    print("\n🚀 Phase 3 — Running Analysis")

    print("\n✅ Starting automated execution...")

    for step in steps:
        print(f"\n🔁 Processing Step: {step.upper()}")

        for patient in patients:
            print(f"\n➡️  Patient {patient.patient_number} — {step}")

            if step == "segmentation":
                for visit in ["PRE", "POST"]:
                    if is_step_done(patient, "segmentation", visit_type=visit):
                        print(f"⏩ {visit} segmentation already done. Skipping.")
                        continue
                    print(f"🔧 Run segmentation for {visit}")
                    segmentation_process(patient, visit)
                    patient.save_to_json()

            elif step == "meshing":
                for visit in ["PRE", "POST"]:
                    if is_step_done(patient, "meshing", visit_type=visit):
                        print(f"⏩ {visit} meshing already done. Skipping.")
                        continue
                    print(f"🔧 Run meshing for {visit}")
                    mesh_process(patient, visit, slicer_path)
                    patient.save_to_json()

            elif step == "registration":
                if is_step_done(patient, "registration"):
                    print("⏩ Registration already done. Skipping.")
                    continue
                print("🔧 Run registration")
                registration_process(patient)
                patient.save_to_json()

            elif step == "cropping":
                if is_step_done(patient, "cropping"):
                    print("⏩ Cropping already done. Skipping.")
                    continue
                print("🔧 Run Cropping")

                if crop_mode == "Plane Crop":
                    from Crop.execute_crop import plane_crop_process
                    plane_crop_process(patient, slicer_path)
                    patient.save_to_json()

                if crop_mode == "Scissor Crop":
                    from Crop.execute_crop import scissor_crop_process
                    scissor_crop_process(patient, slicer_path)
                    patient.save_to_json()

                if crop_mode == "Auto Crop":
                    print("Auto Crop not implemented yet. Please use Plane Crop or Scissor Crop.")
                    #from Crop.execute_crop import auto_crop_process
                    #auto_crop_process(patient, slicer_path)
                    #patient.save_to_json()

            elif step == "Patient_volumetric_analysis":
                if is_step_done(patient, "analysis"):
                    print("⏩ Analysis already done. Skipping.")
                    continue
                print("🔧 Run Patient analysis")
                analysis_process(patient, excel_path)
                patient.save_to_json()

        if step == "Comparative Surgery Spinal Cord":
            if case1 and case2:
                print("🔧 Run Comparative Surgery Spinal Cord")
                global_spinal_cord_process(patients, main_output_path, case1, case2, excel_path)

        elif step == "Psoas Atrophy Analysis":
            print("🔧 Run Psoas Atrophy analysis")
            global_psoas_atrophy_process(patients, main_output_path, excel_path)