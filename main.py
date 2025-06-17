import os
import json

from Prep_and_Tools.ui_tools import select_main_directory, select_slicer_path, get_user_selection
from Prep_and_Tools.patient_tools import find_patients, show_patients
from Prep_and_Tools.results_structure import export_patient_list_to_excel
from pipeline.input_phase import phase1_load_patients
from pipeline.setup_phase import phase2_setup
from pipeline.execution_phase import execute_analysis

def main():
    print("\n🔬 Welcome to the Modular Imaging Pipeline")
    main_output_path = select_main_directory()

    slicer_path = select_slicer_path()

    while True:
        print("\n🌐 Main Menu")
        print(f"✅ Current directory: {main_output_path}")

        # 🔍 Load patient state files (not full objects)
        found_patients = find_patients(main_output_path)
        show_patients(found_patients)
        export_patient_list_to_excel(found_patients, main_output_path)

        choice = get_user_selection(
            ["Load new patients", "Setup analysis", "Run analysis", "Exit"],
            prompt="What would you like to do?",
            multi=False
        )

        if choice == "Load new patients":
            # 🏗️ Run Phase 1 — patient loading (adds txt files)
            phase1_load_patients(main_output_path)

        elif choice == "Setup analysis":
            # ⚙️ Phase 2 — Use patient_txt_paths to go through setup Analysis
            selection = phase2_setup(found_patients,main_output_path)
            if selection:
                selected_patients, selected_steps, crop_mode, excel_path, case_1, case_2 = selection
                execute_analysis(selected_patients, selected_steps, crop_mode, slicer_path, excel_path, main_output_path, case_1, case_2)

        elif choice == "Run analysis":
            print("\n👉 You must first setup analysis (select patients and steps).")

        elif choice == "Exit":
            print("👋 Exiting. See you soon!")
            break


if __name__ == "__main__":
    main()
