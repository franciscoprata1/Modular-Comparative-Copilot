import os
import shutil
import tempfile
from nibabel import load
from Prep_and_Tools.io_tools import load_csv, copy_csv
from Prep_and_Tools.patient_tools import extract_patient_info, organize_patient_files
from Prep_and_Tools.results_structure import create_results_structure
from Prep_and_Tools.ui_tools import select_series, get_user_selection
from Prep_and_Tools.visualization_tools import visualize_nifti_series, visualize_dicom_series
from Prep_and_Tools.imaging_tools import convert_dicom_to_nifti, list_all_series, automatic_image_selection


def batch_patient_prep(csv_path, raw_data_path, output_path, keep_temp=False):
    print(f"🔍 Loading patient metadata from: {csv_path}")
    df = load_csv(csv_path)
    patients_info = extract_patient_info(df, raw_data_path)

    # Ask once how to select images (auto/manual)
    use_auto = get_user_selection(
        ["Automatic", "Manual"],
        prompt="Batch Mode: How would you like to select the NIfTI/DICOM series?",
        multi=False
    ) == "Automatic"

    temp_input_dir = tempfile.mkdtemp(prefix="InputStructure_")
    results_path = os.path.join(output_path, "Results")
    os.makedirs(results_path, exist_ok=True)
    copy_csv(csv_path, results_path)

    config_paths = []

    for patient in patients_info:
        if not patient["visits"]:
            print(f"🚫 Skipping Patient {patient['patient_number']} — no valid visit folders found.")
            continue

        patient_id = patient["patient_number"]
        case_type = patient["case_type"]
        levels = patient["levels"]

        patient_folder, skip_patient = create_results_structure(output_path, patient, case_type)
        if skip_patient:
            config_path = os.path.join(patient_folder, f"PATIENT_{patient_id}_config.txt")
            if os.path.exists(config_path):
                print(f"📎 Reusing existing config for PATIENT_{patient_id}")
                config_paths.append(config_path)
            else:
                print(f"⚠️ Skipping PATIENT_{patient_id} — config file not found!")
            continue

        organize_patient_files(patient, input_structure_path=temp_input_dir)
        input_base = os.path.join(temp_input_dir, f"PATIENT_{patient_id}")
        selected_niftis = {}

        for visit_type in patient["visits"]:
            sorted_path = os.path.join(input_base, visit_type, "SORTED")
            print(f"\n🧠 Selecting series for Patient {patient_id} — {visit_type}")

            sorted_items = list_all_series(sorted_path)
            if not sorted_items:
                print(f"⚠️ No valid series in {sorted_path}")
                continue

            if use_auto:
                selected_path, selected_type = automatic_image_selection(sorted_items)
                if not selected_path:
                    print(f"⚠️ Could not automatically select a valid series for Patient {patient_id} — {visit_type}")
                    continue
            else:
                for idx, (path, kind) in enumerate(sorted_items, 1):
                    if kind == "nifti":
                        try:
                            img = load(path)
                            print(f"\n🔍 Previewing {idx}: {os.path.basename(path)} (NIFTI)")
                            visualize_nifti_series([(path, img)], title_prefix=f"{visit_type}")
                        except Exception as e:
                            print(f"⚠️ Could not preview NIfTI: {e}")
                    elif kind == "dicom":
                        print(f"\n🔍 Previewing {idx}: {os.path.basename(path)} (DICOM)")
                        visualize_dicom_series(path)
                selected_path, selected_type = select_series(sorted_items)

            output_dir = os.path.join(output_path, "Results", case_type.upper(), f"PATIENT_{patient_id}", visit_type)
            final_name = f"PATIENT_{patient_id}_{visit_type}.nii.gz"
            final_path = os.path.join(output_dir, final_name)

            if selected_type == "nifti":
                shutil.copyfile(selected_path, final_path)
            else:
                converted = convert_dicom_to_nifti(selected_path, output_dir, f"PATIENT_{patient_id}_{visit_type}")
                if not converted:
                    continue

            selected_niftis[visit_type] = final_path

        config_path = os.path.join(patient_folder, f"PATIENT_{patient_id}_config.txt")
        config_lines = [
            f"patient_number = {patient_id}",
            f"case_type = {case_type}",
            f"level_intervened = [{', '.join(levels)}]",
            f"patient_output_path = {patient_folder}",
            f"pre_nifti_path = {selected_niftis.get('PRE', '')}",
            f"post_nifti_path = {selected_niftis.get('POST', '')}"
        ]

        with open(config_path, "w") as f:
            f.write("\n".join(config_lines))

        print(f"📝 Created config file: {config_path}")
        config_paths.append(config_path)

    if keep_temp:
        print(f"⚠️ Temp folder preserved: {temp_input_dir}")
    else:
        shutil.rmtree(temp_input_dir)
        print(f"🧹 Deleted temp input folder: {temp_input_dir}")

    return config_paths


def individual_patient_prep(patient_dict, output_path, keep_temp=False):

    patient_id = patient_dict["patient_number"]
    case_type = patient_dict["case_type"]
    levels = patient_dict["levels"]

    temp_input_dir = tempfile.mkdtemp(prefix="InputStructure_")
    patient_folder, skip_patient = create_results_structure(output_path, patient_dict, case_type)

    if skip_patient:
        config_path = os.path.join(patient_folder, f"PATIENT_{patient_id}_config.txt")
        if os.path.exists(config_path):
            print(f"📎 Reusing existing config for PATIENT_{patient_id}")
            return [config_path]
        else:
            print(f"⚠️ Skipping PATIENT_{patient_id} — config file not found!")
            return []

    organize_patient_files(patient_dict, input_structure_path=temp_input_dir)
    input_base = os.path.join(temp_input_dir, f"PATIENT_{patient_id}")
    selected_niftis = {}

    # Ask once how to select images (auto/manual)
    use_auto = get_user_selection(
        ["Automatic", "Manual"],
        prompt="How would you like to select the NIfTI/DICOM series?",
        multi=False
    ) == "Automatic"

    for visit_type in patient_dict["visits"]:
        sorted_path = os.path.join(input_base, visit_type, "SORTED")
        print(f"\n🧠 Selecting series for Patient {patient_id} — {visit_type}")

        sorted_items = list_all_series(sorted_path)
        if not sorted_items:
            print(f"⚠️ No valid series in {sorted_path}")
            continue

        if use_auto:
            selected_path, selected_type = automatic_image_selection(sorted_items)
        else:
            for idx, (path, kind) in enumerate(sorted_items, 1):
                if kind == "nifti":
                    try:
                        img = load(path)
                        print(f"\n🔍 Previewing {idx}: {os.path.basename(path)} (NIFTI)")
                        visualize_nifti_series([(path, img)], title_prefix=f"{visit_type}")
                    except Exception as e:
                        print(f"⚠️ Could not preview NIfTI: {e}")
                elif kind == "dicom":
                    print(f"\n🔍 Previewing {idx}: {os.path.basename(path)} (DICOM)")
                    visualize_dicom_series(path)
            selected_path, selected_type = select_series(sorted_items)

        output_dir = os.path.join(output_path, "Results", case_type.upper(), f"PATIENT_{patient_id}", visit_type)
        final_name = f"PATIENT_{patient_id}_{visit_type}.nii.gz"
        final_path = os.path.join(output_dir, final_name)

        if selected_type == "nifti":
            shutil.copyfile(selected_path, final_path)
        else:
            converted = convert_dicom_to_nifti(selected_path, output_dir, f"PATIENT_{patient_id}_{visit_type}")
            if not converted:
                continue

        selected_niftis[visit_type] = final_path

    config_path = os.path.join(patient_folder, f"PATIENT_{patient_id}_config.txt")
    config_lines = [
        f"patient_number = {patient_id}",
        f"case_type = {case_type}",
        f"level_intervened = [{', '.join(levels)}]",
        f"patient_output_path = {patient_folder}",
        f"pre_nifti_path = {selected_niftis.get('PRE', '')}",
        f"post_nifti_path = {selected_niftis.get('POST', '')}"
    ]

    with open(config_path, "w") as f:
        f.write("\n".join(config_lines))

    print(f"📝 Created config file: {config_path}")

    if keep_temp:
        print(f"⚠️ Temp folder preserved: {temp_input_dir}")
    else:
        shutil.rmtree(temp_input_dir)
        print(f"🧹 Deleted temp input folder: {temp_input_dir}")

    return [config_path]