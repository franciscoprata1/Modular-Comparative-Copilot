import os
import shutil
import glob
import pydicom
import pandas as pd
from pydicom.errors import InvalidDicomError


def extract_patient_info(df, raw_data_root):
    required_columns = {'NHC', 'PatientID', 'VisitType', 'CaseType', 'Levels'}
    if not required_columns.issubset(df.columns):
        raise ValueError(f"Missing required columns: {required_columns}")

    patients_map = {}
    for _, row in df.iterrows():
        try:
            nhc = str(row['NHC']).strip()
            patient_id = str(row['PatientID']).strip()
            case_type = str(row['CaseType']).strip().upper()
            level_pairs = str(row['Levels']).strip().split('/')
            levels = []
            for pair in level_pairs:
                parts = pair.strip().split('-')
                if len(parts) != 2:
                    raise ValueError(f"Invalid format: '{pair}' — must be like 'L2-L3'")
                levels.extend(parts)
            visit_types = str(row['VisitType']).strip().upper().split('/')

            if patient_id not in patients_map:
                patients_map[patient_id] = {
                    "nhc": nhc,
                    "patient_number": patient_id,
                    "case_type": case_type,
                    "levels": levels,
                    "folder_path": os.path.join(raw_data_root, nhc),
                    "visits": {}
                }

            for visit_type in visit_types:
                visit_path = os.path.join(raw_data_root, nhc, visit_type)
                if os.path.exists(visit_path):
                    patients_map[patient_id]["visits"][visit_type] = visit_path
                    print(f"✅ Found: Patient {patient_id} — {visit_type}")
                else:
                    print(f"⚠️ Missing folder for Patient {patient_id} — {visit_type}")
        except Exception as e:
            print(f"❌ Error parsing row: {e}")

    return list(patients_map.values())

def organize_patient_files(patient, input_structure_path, overwrite=True):
    patient_id = patient['patient_number']
    print(f"\n🧬 Organizing files for Patient {patient_id}")

    for visit_type, raw_path in patient["visits"].items():
        visit_dir = os.path.join(input_structure_path, f"PATIENT_{patient_id}", visit_type)
        sorted_output = os.path.join(visit_dir, "SORTED")

        if os.path.exists(sorted_output):
            if overwrite:
                print(f"🔁 Overwriting existing: {sorted_output}")
                shutil.rmtree(sorted_output)
            else:
                print(f"↪️ Skipping: SORTED folder already exists and overwrite=False: {sorted_output}")
                continue

        os.makedirs(sorted_output, exist_ok=True)

        for root, _, files in os.walk(raw_path):
            for file in files:
                src = os.path.join(root, file)
                if file.lower().endswith(".dcm"):
                    try:
                        dcm = pydicom.dcmread(src, stop_before_pixels=True)
                        name = getattr(dcm, "SeriesDescription", str(dcm.SeriesNumber))
                        safe_name = "".join(x for x in name if x.isalnum() or x in " ._-")
                        dst_dir = os.path.join(sorted_output, safe_name)
                        os.makedirs(dst_dir, exist_ok=True)
                        shutil.copy(src, os.path.join(dst_dir, file))
                    except InvalidDicomError:
                        continue
                elif file.lower().endswith((".nii", ".nii.gz")):
                    dst = os.path.join(sorted_output, os.path.basename(file))
                    if os.path.abspath(src) != os.path.abspath(dst):
                        shutil.copy(src, dst)

def find_patients(main_dir):
    results_path = os.path.join(main_dir, "Results")
    if not os.path.exists(results_path):
        return []

    txt_files = []
    for root, _, files in os.walk(results_path):
        for file in files:
            if file.endswith("_config.txt"):
                txt_files.append(os.path.join(root, file))
    return txt_files


def show_patients(txt_paths):
    """
    Prints a list of patients from config .txt files.
    Adds a ⚠️ if a corresponding JSON state file exists (i.e., patient has started processing),
    or 🆕 if not. Also shows a brief description of the status.
    """
    print(f"\n📋 Found {len(txt_paths)} patient(s):")
    for path in txt_paths:
        try:
            config = load_case_config(path)
            patient_number = config.get("patient_number", "❓Unknown")
            output_path = config.get("patient_output_path", "")
            json_path = os.path.join(output_path, f"PATIENT_{patient_number}_state.json")

            if os.path.exists(json_path):
                status_icon = "⚠️"
                status_text = "Patient has existing progress"
            else:
                status_icon = "🆕"
                status_text = "New patient"

            print(f"  {status_icon} Patient {patient_number} — {os.path.basename(path)}  ({status_text})")

        except Exception as e:
            print(f"  ❌ Could not parse config at {path}: {e}")

def load_case_config(path):
    config = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, value = line.split('=')
            key = key.strip()
            value = value.strip()

            if value.startswith('[') and value.endswith(']'):
                items = value[1:-1].split(',')
                value = [item.strip() for item in items if item.strip()]
            elif key == "patient_number":
                value = int(value)
            elif key == "modality":
                value = value.lower()

            config[key] = value

    return config


def clean_patient_analysis_files(patient):
    """
    Deletes all analysis-related files associated with a patient.
    Called when a user chooses to overwrite an existing patient.
    """
    for visit in [patient.pre, patient.post]:
        visit_path = visit.visit_output_path

        # SEGMENTATION CLEANUP
        seg_pattern = os.path.join(visit_path, "Segmentation_*.nii.gz")
        print(f"🔍 Looking for segmentation files using pattern: {seg_pattern}")
        for path in glob.glob(seg_pattern):
            os.remove(path)
            print(f"🗑️ Deleted segmentation file: {path}")

        # OTHER SEGMENTATIONS
        other_seg_dir = os.path.join(visit_path, "OtherSegmentations")
        if os.path.isdir(other_seg_dir):
            shutil.rmtree(other_seg_dir)
            print(f"🗑️ Deleted OtherSegmentations folder: {other_seg_dir}")

        # MESHING CLEANUP
        mesh_pattern = os.path.join(visit_path, "Mesh*")
        print(f"🔍 Looking for mesh files/folders using pattern: {mesh_pattern}")
        for path in glob.glob(mesh_pattern):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            print(f"🗑️ Deleted mesh file/folder: {path}")

    patient_folder = patient.output_path

    # REGISTRATION CLEANUP
    reg_pattern = os.path.join(patient_folder, "Registration*")
    print(f"🔍 Looking for registration files using pattern: {reg_pattern}")
    for path in glob.glob(reg_pattern):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        print(f"🗑️ Deleted registration file/folder: {path}")

    # CROPPING CLEANUP
    crop_pattern = os.path.join(patient_folder, "Crop*")
    print(f"🔍 Looking for crop files using pattern: {crop_pattern}")
    for path in glob.glob(crop_pattern):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        print(f"🗑️ Deleted crop file/folder: {path}")

    # SHAPE ANALYSIS CLEANUP
    analysis_pattern = os.path.join(patient_folder, "Stat Analysis*")
    print(f"🔍 Looking for analysis files using pattern: {analysis_pattern}")
    for path in glob.glob(analysis_pattern):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        print(f"🗑️ Deleted analysis file/folder: {path}")