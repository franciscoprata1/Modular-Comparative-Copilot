import os
import re

from Prep_and_Tools.ui_tools import get_user_selection, get_segmentation_config
from Prep_and_Tools.patient_tools import load_case_config, clean_patient_analysis_files
from Prep_and_Tools.results_structure import create_analysis_results_excel
from classes import Patient


def phase2_setup(txt_paths, main_output_path):
    print("\n⚙️ Phase 2 — Analysis Setup")

    if not txt_paths:
        print("❌ No patient configs found. Run Phase 1 first.")
        return None

    # ✅ Robust patient ID extraction
    id_to_path = {}
    for path in txt_paths:
        filename = os.path.basename(path)
        match = re.match(r"PATIENT_(\d+)_config\.txt", filename)
        if match:
            patient_id = match.group(1)
            label = f"PATIENT_{patient_id}"
            id_to_path[label] = path
        else:
            print(f"⚠️ Skipping unrecognized config file: {filename}")

    if not id_to_path:
        print("❌ No valid patient configs matched expected pattern.")
        return None

    found_patients = list(id_to_path.keys())
    found_patients.append("All")
    selection = get_user_selection(found_patients, prompt="Select patients:", multi=True)

    selected_paths = list(id_to_path.values()) if "All" in selection else [
        id_to_path[sel] for sel in selection if sel in id_to_path
    ]

    if not selected_paths:
        print("⚠️ No valid patients selected.")
        return None

    step_options = ["segmentation", "meshing", "registration", "cropping", "Patient_volumetric_analysis", "Stat_analysis", "All"]
    selected_steps = get_user_selection(step_options, prompt="Select analysis steps:", multi=True)

    if "All" in selected_steps:
        selected_steps = ["segmentation", "meshing", "registration", "cropping", "Patient_volumetric_analysis", "Stat_analysis"]

    existing_json_paths = []
    non_existing_paths = []

    for config_path in selected_paths:
        try:
            config = load_case_config(config_path)
            patient_id = config["patient_number"]
            output_path = config["patient_output_path"]
            json_path = os.path.join(output_path, f"PATIENT_{patient_id}_state.json")

            if os.path.exists(json_path):
                print(f"⚠️ Patient_{patient_id} already exists.")
                existing_json_paths.append((json_path, config_path))
            else:
                non_existing_paths.append(config_path)

        except Exception as e:
            print(f"⚠️ Failed to parse config at {config_path}: {e}")

    action = None
    if existing_json_paths:
        print(f"\n⚠️ {len(existing_json_paths)} patients already have existing analysis JSONs.")
        print("⚠️ WARNING: Choosing [O]verwrite will permanently delete all previous analysis results for these patients!")
        print("🚨 This includes segmentations, meshes, registrations, crop files, and shape analysis outputs.")
        action = input("❓ Proceed with [U]se existing, [O]verwrite, or [S]kip them all? ").strip().lower()


    reused_patients = [] # Store reused patients

    for json_path, config_path in existing_json_paths:
        config = load_case_config(config_path)
        patient_id = config["patient_number"]
        output_path = config["patient_output_path"]

        if action == "s":
            print(f"⏭️ Skipping Patient {patient_id}")
            continue

        elif action == "u":
            existing = Patient.load_from_json(output_path, patient_id)
            reused_patients.append(existing)
            continue

        elif action == "o":
            print(f"⚠️ Overwriting Patient {patient_id} analysis files.")
            try:
                existing = Patient.load_from_json(output_path, patient_id)
                clean_patient_analysis_files(existing)
            except Exception as e:
                print(f"⚠️ Failed to clean previous analysis: {e}")
            os.remove(json_path)
            non_existing_paths.append(config_path)  # treat it like new patient

        else:
            print(f"⚠️ Invalid action. Skipping Patient {patient_id}")

    new_patients= []

    # ✅ Create Patient objects for new/overwritten
    for config_path in non_existing_paths:
        try:
            config = load_case_config(config_path)
            patient_id = config["patient_number"]
            print(f"✨ Creating Patient object for ID {patient_id}")

            patient = Patient(config)
            if config.get("pre_nifti_path"):
                patient.pre.log_nifti(config["pre_nifti_path"])
            if config.get("post_nifti_path"):
                patient.post.log_nifti(config["post_nifti_path"])

            new_patients.append(patient)

        except Exception as e:
            print(f"⚠️ Failed to prepare patient from {config_path}: {e}")


    # ✅ Configure segmentation for new/overwritten patients only
    if "segmentation" in selected_steps and new_patients:
        print("\n🧠 Configure segmentation settings for all NEW or OVERWRITTEN patients:")
        seg_config = get_segmentation_config("ALL")

        for p in new_patients:
            p.segmentation_tool = seg_config["tool"]
            p.roi = seg_config["roi"]
            p.other = seg_config["other"]
            p.pre.log_modality(seg_config["modality"])
            p.post.log_modality(seg_config["modality"])
            p.use_fast = seg_config.get("fast", False)
            p.save_to_json()


    selected_patients = new_patients + reused_patients

    # ✅ Crop Modality setup
    if "cropping" in selected_steps:
        print("\n🧠 Configure crop mode for analysis")
        crop_mode = "Plane Crop"
    else:
        crop_mode = None
    
    # ✅ Analysis Excel setup
    if "Patient_volumetric_analysis" in selected_steps:
        excel_path = create_analysis_results_excel(main_output_path)
    else:
        excel_path = None

    # ✅ Comparative analysis setup
    if "Stat_analysis" in selected_steps:
        print("\n🔍 Statistical Analysis Setup")

        stat_analysis_type = get_user_selection(["Comparative Surgery Spinal Cord", "Psoas Atrophy Analysis"],prompt="Select type of Statistical Analysis:",multi=False)

        # Replace "Stat_analysis" with the specific type selected
        index = selected_steps.index("Stat_analysis")

        if stat_analysis_type == "Comparative Surgery Spinal Cord":
            found_cases = sorted(set(p.case_type for p in selected_patients))
            found_cases.append("No Comparative Analysis")

            case_selection = get_user_selection(found_cases,prompt="Select two cases for comparison (or choose 'No Comparative Analysis'):",multi=True)

            if "No Comparative Analysis" in case_selection or len(case_selection) != 2:
                case_1, case_2 = None, None
                print("❌ No valid comparative analysis selected.")
            else:
                case_1, case_2 = case_selection
                print(f"📊 Comparative analysis will be performed between: {case_1} vs {case_2}")

            selected_steps[index] = "Comparative Surgery Spinal Cord"

        elif stat_analysis_type == "Psoas Atrophy Analysis":
            case_1, case_2 = None, None
            selected_steps[index] = "Psoas Atrophy Analysis"
            print("📊 Psoas Atrophy analysis selected")
    else:
        case_1, case_2 = None, None

    return selected_patients, selected_steps, crop_mode, excel_path, case_1, case_2
