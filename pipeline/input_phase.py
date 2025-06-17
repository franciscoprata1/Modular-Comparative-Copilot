import os

from Prep_and_Tools.prep_workflows import batch_patient_prep, individual_patient_prep
from Prep_and_Tools.ui_tools import get_user_selection

def phase1_load_patients(main_output_path):
    """
    Guide function to run Phase 1 — Patient Loading (Batch or Individual).
    """
    while True:
        print("\n👤 Phase 1 — Patient Loading")
        mode = get_user_selection(
            ["Batch", "Individual", "Back to main"],
            prompt="Add patients in batch or individually?",
            multi=False
        )

        if mode == "Batch":
            csv_path = input("Enter full path to CSV/Excel file: ").strip().strip('"')
            raw_path = input("Enter full path to raw data folder: ").strip().strip('"')
            batch_patient_prep(csv_path, raw_path, main_output_path)

        elif mode == "Individual":
            raw_path = input("Enter full path to raw data folder: ").strip().strip('"')
            patient_id = input("Enter Patient ID: ").strip()
            case_type = input("Enter Case Type (e.g., CASE_A): ").strip().upper()
            visit_types = input("Enter visit types (e.g., PRE/POST): ").strip().upper().split("/")
            level_pairs = input("Enter vertebral levels (e.g., L4-L5): ").strip().split('/')
            levels=[]
            for pair in level_pairs:
                parts = pair.strip().split('-')
                if len(parts) != 2:
                    raise ValueError(f"Invalid format: '{pair}' — must be like 'L2-L3'")
                levels.extend(parts)

            patient_dict = {
                "patient_number": patient_id,
                "case_type": case_type,
                "levels": levels,
                "folder_path": raw_path,  
                "visits": {}
            }

            for vt in visit_types:
                vt_path = os.path.join(raw_path, vt)
                if os.path.exists(vt_path):
                    patient_dict["visits"][vt] = vt_path
                else:
                    print(f"⚠️ Visit folder not found: {vt_path}")

            individual_patient_prep(patient_dict, main_output_path)

        elif mode == "Back to main":
            break