import customtkinter
from customtkinter import CTkFont
import tkinter.filedialog as fd
import json
import os
import threading
from Prep_and_Tools.patient_tools import load_case_config, clean_patient_analysis_files
from Prep_and_Tools.results_structure import export_patient_list_to_excel
from Prep_and_Tools.prep_workflows import batch_patient_prep, individual_patient_prep
from pipeline.execution_phase import execute_analysis
from classes import Patient
from segmentation import SEGMENTATION_TOOLS
from openpyxl import Workbook

CONFIG_FILE = "gui_config.json"

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Modular Imaging Pipeline")
        self.geometry("1400x1000")

        # UI Mode and Theme
        customtkinter.set_appearance_mode("light")
        customtkinter.set_default_color_theme("green")

        # Set universal fonts
        self.font = CTkFont(family="Segoe UI", size=14)
        self.font_button = CTkFont(family="Segoe UI", size=16, weight="bold")
        self.font_title = CTkFont(family="Segoe UI", size=24, weight="bold")

        # Paths and settings
        self.results_path = None
        self.slicer_path = None
        self.remember_settings = False
        self.load_saved_config()

        # INTERNAL VARIABLES
        self.indiv_raw_path = None
        self.batch_csv_path = None
        self.batch_raw_path = None
        self.n_loaded_patients = None
        self.patients_w_json = []
        self.new_patients = []
        self.selected_new_patients = []
        self.selected_existing_patients = []
        self.new_objects = []
        self.reused_objects = []
        self.patient_objects = []
        self.selected_steps = []
        self.crop_mode = None
        self.excel_path = None
        self.selected_analysis_type = None
        self.case_1 = None
        self.case_2 = None

        ## Frames
        self.initial_frame = customtkinter.CTkFrame(self)
        self.main_frame = customtkinter.CTkFrame(self)
        # phase 1
        self.phase1_frame = customtkinter.CTkFrame(self)
        self.individual_frame = customtkinter.CTkFrame(self)
        self.batch_frame = customtkinter.CTkFrame(self)
        self.indv_automatic_selection_frame = customtkinter.CTkFrame(self)
        self.batch_automatic_selection_frame = customtkinter.CTkFrame(self)
        self.manual_loading_frame = customtkinter.CTkFrame(self)
        #OVERWRITE LOADED PATIENTS POPUP FRAME??

        #phase 2
        self.phase2_frame = customtkinter.CTkFrame(self)
        self.phase2_steps_frame = customtkinter.CTkFrame(self)
        self.phase2_setup_segmentation_frame = customtkinter.CTkFrame(self)
        self.phase2_setup_crop_frame = customtkinter.CTkFrame(self)
        self.phase2_analysis_results_excel_frame = customtkinter.CTkFrame(self)
        self.phase2_setup_general_analysis_frame = customtkinter.CTkFrame(self)

        #phase 3
        self.phase3_overview_frame = customtkinter.CTkFrame(self)
        self.phase3_process_frame = customtkinter.CTkFrame(self)

        # Set initial Frame
        self.initial_frame.pack(pady=20, padx=60, fill="both", expand=True)

        # Title frames
        self.initial_label = customtkinter.CTkLabel(master=self.initial_frame, text="Welcome! Please set initial configuration:", font=self.font_title)
        self.initial_label.pack(pady=12, padx=10)

        self.main_label = customtkinter.CTkLabel(master=self.main_frame, text="Modular Comparative Copilot: Main Menu", font=self.font_title)
        self.main_label.pack(pady=12, padx=10)

        self.phase1_label = customtkinter.CTkLabel(master=self.phase1_frame, text="Phase 1: Patient loading mode", font=self.font_title)
        self.phase1_label.pack(pady=12, padx=10)

        self.individual_loading_label = customtkinter.CTkLabel(master=self.individual_frame, text="Phase 1: Individual Patient Loading", font=self.font_title)
        self.individual_loading_label.pack(pady=12, padx=10)

        self.batch_loading_label = customtkinter.CTkLabel(master=self.batch_frame, text="Phase 1: Batch Patient Loading", font=self.font_title)
        self.batch_loading_label.pack(pady=12, padx=10)

        self.indv_automatic_selection_label = customtkinter.CTkLabel(master=self.indv_automatic_selection_frame, text="Phase 1: Automatic Image Selection", font=self.font_title)
        self.indv_automatic_selection_label.pack(pady=12, padx=10)

        self.batch_automatic_selection_label = customtkinter.CTkLabel(master=self.batch_automatic_selection_frame, text="Phase 1: Batch Automatic Image Selection", font=self.font_title)
        self.batch_automatic_selection_label.pack(pady=12, padx=10)

        self.manual_loading_label = customtkinter.CTkLabel(master=self.manual_loading_frame, text="Phase 1: Manual Image Selection", font=self.font_title)
        self.manual_loading_label.pack(pady=12, padx=10)

        self.phase2_label = customtkinter.CTkLabel(master=self.phase2_frame, text="Phase 2: Analysis setup", font=self.font_title)
        self.phase2_label.pack(pady=12, padx=10)

        self.phase2_label2 = customtkinter.CTkLabel(master=self.phase2_steps_frame, text="Phase 2: Analysis setup", font=self.font_title)
        self.phase2_label.pack(pady=12, padx=10)

        self.phase2_label3 = customtkinter.CTkLabel(master=self.phase2_setup_segmentation_frame, text="Phase 2: Analysis setup", font=self.font_title)
        self.phase2_label.pack(pady=12, padx=10)

        self.phase2_label4 = customtkinter.CTkLabel(master=self.phase2_setup_crop_frame, text="Phase 2: Analysis setup", font=self.font_title)
        self.phase2_label.pack(pady=12, padx=10)

        self.phase2_label5 = customtkinter.CTkLabel(master=self.phase2_analysis_results_excel_frame, text="Phase 2: Analysis setup", font=self.font_title)
        self.phase2_label5.pack(pady=12, padx=10)

        self.phase2_label6 = customtkinter.CTkLabel(master=self.phase2_setup_general_analysis_frame, text="Phase 2: Analysis setup", font=self.font_title)
        self.phase2_label6.pack(pady=12, padx=10)

        self.phase3_overview_title = customtkinter.CTkLabel(master=self.phase3_overview_frame, text="Analysis Overview", font=self.font_title)
        self.phase3_overview_title.pack(pady=10)

        self.phase3_processing_title = customtkinter.CTkLabel(master=self.phase3_process_frame, text= "Executing Analysis...", font=self.font_title)
        self.phase3_processing_title.pack(pady=10)

        ########### Initial Frame
        # Set Results path
        self.button1 = customtkinter.CTkButton(master=self.initial_frame, text="Set Results folder path (Default: Desktop)", command=self.select_main_directory, font=self.font)
        self.button1.pack(pady=6, padx=10)
        self.label_main_path = customtkinter.CTkLabel(master=self.initial_frame, text=f"Current Results Path: {self.results_path}" or "No Results path selected", font=self.font)
        self.label_main_path.pack(pady=4, padx=10)

        # Set Slicer path
        self.button2 = customtkinter.CTkButton(master=self.initial_frame, text="Set Slicer path", command=self.select_slicer_path, font=self.font)
        self.button2.pack(pady=6, padx=10)
        self.label_slicer_path = customtkinter.CTkLabel(master=self.initial_frame, text=f"Current Slicer Path: {self.slicer_path}" or "No Slicer path selected", font=self.font)
        self.label_slicer_path.pack(pady=4, padx=10)

        # Checkbox to remember paths
        self.checkbox = customtkinter.CTkCheckBox(master=self.initial_frame, text="Remember these options", command=self.toggle_remember, font=self.font)
        self.checkbox.pack(pady=12, padx=10)
        self.checkbox.select() if self.remember_settings else self.checkbox.deselect()

        # Launch pipeline
        self.button3 = customtkinter.CTkButton(master=self.initial_frame, text="Start Modular Comparative Copilot App", command=self.start_app, font=self.font_button)
        self.button3.pack(pady=12, padx=10)

        ########### Main Frame buttons
        # Load Patients
        self.button1 = customtkinter.CTkButton(master=self.main_frame, text="Load Patients", command=self.phase_1_load_patients, font=self.font_button)
        self.button1.pack(pady=6, padx=10)

        # Label for patient count
        self.label_patient_count = customtkinter.CTkLabel(master=self.main_frame, text=f"{self.n_loaded_patients} patients loaded" if self.n_loaded_patients else "No patients loaded", font=self.font)
        self.label_patient_count.pack(pady=4, padx=10)

        # Textboxes for patient lists
        self.box_new_patients = customtkinter.CTkTextbox(master=self.main_frame, width=400, height=100, font=self.font)
        self.box_new_patients.pack(pady=4)
        self.box_new_patients.configure(state="disabled")

        self.box_existing_patients = customtkinter.CTkTextbox(master=self.main_frame, width=400, height=100, font=self.font)
        self.box_existing_patients.pack(pady=4)
        self.box_existing_patients.configure(state="disabled")

        # Configure Analysis
        self.button2 = customtkinter.CTkButton(master=self.main_frame, text="Setup Analysis", command=self.phase_2_setup_analysis, font=self.font_button)
        self.button2.pack(pady=6, padx=10)

        ############## Phase 1 Frame buttons #############################################################################
        self.button1 = customtkinter.CTkButton(master=self.phase1_frame, text="Individual Loading", command=self.individual_patient_loading, font=self.font_button)
        self.button1.pack(pady=6, padx=10)

        self.button2 = customtkinter.CTkButton(master=self.phase1_frame, text="Batch Loading", command=self.batch_patient_loading, font=self.font_button)
        self.button2.pack(pady=6, padx=10)

        self.phase1_back_button = customtkinter.CTkButton(master=self.phase1_frame,text="⬅️ Back to Main Menu",font=self.font, command=self.return_to_main_menu)
        self.phase1_back_button.pack(pady=10)

        ########### Phase 1 (Individual Loading) Frame buttons
        entry_patient_id = customtkinter.CTkEntry(master=self.individual_frame, placeholder_text="Patient ID", font=self.font)
        entry_patient_id.pack(pady=6, padx=10)

        entry_case_type = customtkinter.CTkEntry(master=self.individual_frame, placeholder_text="Case Type (e.g., CASE_A)", font=self.font)
        entry_case_type.pack(pady=6, padx=10)

        entry_levels = customtkinter.CTkEntry(master=self.individual_frame, placeholder_text="Vertebral Levels (e.g., L2-L3/L4-L5)", font=self.font)
        entry_levels.pack(pady=6, padx=10)

        entry_visits = customtkinter.CTkEntry(master=self.individual_frame, placeholder_text="Visit Types (e.g., PRE/POST)", font=self.font)
        entry_visits.pack(pady=6, padx=10)

        self.button1 = customtkinter.CTkButton(master=self.individual_frame, text="Select patient raw data folder", command=self.select_individual_raw_folder, font=self.font)
        self.button1.pack(pady=6, padx=10)
        self.label_indiv_raw_path = customtkinter.CTkLabel(master=self.individual_frame, text=f"Current Results patient raw data folder: {self.indiv_raw_path}" or "No Results path selected", font=self.font)
        self.label_indiv_raw_path.pack(pady=4, padx=10)

        # Variable to store the selected option
        self.selection_mode = customtkinter.StringVar(value="Automatic")

        # Radio buttons
        radio1 = customtkinter.CTkRadioButton(master=self.individual_frame, text="Automatic", variable=self.selection_mode, value="Automatic")
        radio2 = customtkinter.CTkRadioButton(master=self.individual_frame, text="Manual", variable=self.selection_mode, value="Manual")
        radio1.pack(pady=5)
        radio2.pack(pady=5)

        self.button_individual_patient_prep = customtkinter.CTkButton(master=self.individual_frame, text="Start Individual Patient Prep", font=self.font_button, command=self.image_selection_mode)
        self.button_individual_patient_prep.pack(pady=10)

        self.individual_back_button = customtkinter.CTkButton(master=self.individual_frame,text="⬅️ Back to Main Menu",font=self.font, command=self.return_to_main_menu)
        self.individual_back_button.pack(pady=10)

        ########### Phase 1 (Batch Loading) Frame buttons

        self.button1 = customtkinter.CTkButton(master=self.batch_frame, text="Select Excel file with patient info", command=self.select_batch_csv, font=self.font)
        self.button1.pack(pady=6, padx=10)
        self.label_batch_csv = customtkinter.CTkLabel(master=self.batch_frame, text=f"Current Excel File: {self.batch_csv_path}" or "No Results path selected", font=self.font)
        self.label_batch_csv.pack(pady=4, padx=10)

        self.button2 = customtkinter.CTkButton(master=self.batch_frame, text="Select raw data folder", command=self.select_batch_raw_folder, font=self.font)
        self.button2.pack(pady=6, padx=10)
        self.label_batch_raw_path = customtkinter.CTkLabel(master=self.batch_frame, text=f"Current Batch patients raw data folder: {self.batch_raw_path}" or "No Results path selected", font=self.font)
        self.label_batch_raw_path.pack(pady=4, padx=10)

        # Variable to store the selected option
        self.selection_mode_batch = customtkinter.StringVar(value="Automatic")

        # Radio buttons
        radio1 = customtkinter.CTkRadioButton(master=self.batch_frame, text="Automatic", variable=self.selection_mode_batch, value="Automatic")
        radio2 = customtkinter.CTkRadioButton(master=self.batch_frame, text="Manual", variable=self.selection_mode_batch, value="Manual")
        radio1.pack(pady=5)
        radio2.pack(pady=5)

        self.button_batch_patient_prep = customtkinter.CTkButton(master=self.batch_frame, text="Start Batch Patient Prep", font=self.font_button, command=self.image_selection_mode_batch)
        self.button_batch_patient_prep.pack(pady=10)

        self.batch_back_button = customtkinter.CTkButton(master=self.batch_frame,text="⬅️ Back to Main Menu",font=self.font, command=self.return_to_main_menu)
        self.batch_back_button.pack(pady=10)

        ########### Indv Automatic Loading Frame buttons
        # Start button
        self.automatic_selection_button = customtkinter.CTkButton(master=self.indv_automatic_selection_frame,text="Start automatic selection",font=self.font_button,
            command=lambda: self.on_start_automatic_selection(
                    entry_patient_id.get().strip(),
                    entry_case_type.get().strip().upper(),
                    entry_levels.get().strip().split('/'), 
                    entry_visits.get().strip().upper().split('/'),
                    self.indiv_raw_path,
                    self.selection_mode.get()
            )
        )
        self.automatic_selection_button.pack(pady=10)

        # Progress bar: PROCESSING...
        self.indiv_progress_label = customtkinter.CTkLabel(master=self.indv_automatic_selection_frame, text="Processing...")
        self.indiv_progress_bar = customtkinter.CTkProgressBar(master=self.indv_automatic_selection_frame, width=300)
        self.indiv_progress_bar.set(0)


        # Back button
        self.automatic_back_button = customtkinter.CTkButton(
            master=self.indv_automatic_selection_frame,
            text="⬅️ Back to Main Menu",
            font=self.font,
            command=self.return_to_main_menu
        )
        self.automatic_back_button.pack(pady=10)

        ########### Batch Automatic Loading Frame buttons
        # Start button
        self.batch_automatic_selection_button = customtkinter.CTkButton(
            master=self.batch_automatic_selection_frame,
            text="Start Batch Automatic Selection",
            font=self.font_button,
            command=lambda: self.on_start_batch_automatic_selection(
                self.batch_csv_path,
                self.batch_raw_path,
                self.selection_mode.get()
            )
        )
        self.batch_automatic_selection_button.pack(pady=10)

        # Progress bar: PROCESSING...
        self.batch_progress_label = customtkinter.CTkLabel(master=self.batch_automatic_selection_frame, text="Processing...")
        self.batch_progress_bar = customtkinter.CTkProgressBar(master=self.batch_automatic_selection_frame, width=300)
        self.batch_progress_bar.set(0)


        # Back button
        self.batch_automatic_back_button = customtkinter.CTkButton(master=self.batch_automatic_selection_frame, text="⬅️ Back to Main Menu",font=self.font,command=self.return_to_main_menu)
        self.batch_automatic_back_button.pack(pady=10)

        ########### Manual Loading Frame buttons
        #  label
        self.label_current_visit = customtkinter.CTkLabel(master=self.manual_loading_frame, text="Manual Image Selection not implemented yet. Please use automatic image selection mode", font=self.font)
        self.label_current_visit.pack(pady=10)

        # Back button
        self.manual_back_button = customtkinter.CTkButton(master=self.manual_loading_frame,text="⬅️ Back to Main Menu",font=self.font,command=self.return_to_main_menu)
        self.manual_back_button.pack(pady=10)


        ############## Phase 2 Frame buttons ########################################################################################
        ########### Select Patients for Analysis
        # Phase 2: Title
        self.select_patients_description = customtkinter.CTkLabel(master=self.phase2_frame, text="Select Patients for Analysis", font=self.font)
        self.select_patients_description.pack(pady=10)

        # Container Frame to hold both sides
        self.selection_container = customtkinter.CTkFrame(master=self.phase2_frame)
        self.selection_container.pack(pady=10, fill="both", expand=True)

        # New Patients Frame (Left)
        self.new_patients_frame = customtkinter.CTkScrollableFrame(master=self.selection_container, width=400, height=400)
        self.new_patients_frame.grid(row=0, column=0, padx=20, pady=10)

        self.new_patients_label = customtkinter.CTkLabel(master=self.new_patients_frame, text="🆕 New Patients", font=self.font_button)
        self.new_patients_label.pack()

        # Existing Patients Frame (Right)
        self.existing_patients_frame = customtkinter.CTkScrollableFrame(master=self.selection_container, width=400, height=400)
        self.existing_patients_frame.grid(row=0, column=1, padx=20, pady=10)

        self.existing_patients_label = customtkinter.CTkLabel( master=self.existing_patients_frame, text="📁 Existing Patients", font=self.font_button)
        self.existing_patients_label.pack()

        # Confirm Button
        self.confirm_patient_selection_btn = customtkinter.CTkButton(master=self.phase2_frame, text="✅ Confirm Selection",font=self.font_button, command=self.confirm_patient_selection)
        self.confirm_patient_selection_btn.pack(pady=10)

        # Back button
        self.phase2_back_button = customtkinter.CTkButton(master=self.phase2_frame, text="⬅️ Back to Main Menu",font=self.font_button, command=self.return_to_main_menu)
        self.phase2_back_button.pack(pady=10)

        ########### Phase 2 Steps Frame buttons
        # Phase 2 Steps: Title
        self.select_patients_description = customtkinter.CTkLabel(master=self.phase2_steps_frame, text="Select Analysis Steps", font=self.font)
        self.select_patients_description.pack(pady=10)

        self.step_vars = {}  # Dict to store step name → BooleanVar

        self.step_options = ["segmentation","meshing","registration","cropping","Patient_volumetric_analysis","general_analysis"]

        # Step Checkboxes
        for step in self.step_options:
            var = customtkinter.BooleanVar()
            self.step_vars[step] = var
            cb = customtkinter.CTkCheckBox(master=self.phase2_steps_frame,text=step.title(),variable=var,font=self.font)
            cb.pack(pady=4, anchor="w", padx=20)

        # Confirm Button
        self.confirm_steps_button = customtkinter.CTkButton(master=self.phase2_steps_frame,text="✅ Confirm Steps",font=self.font_button,command=self.confirm_steps_selection)
        self.confirm_steps_button.pack(pady=10)

        # Back button
        self.phase2_back_button = customtkinter.CTkButton(master=self.phase2_steps_frame, text="⬅️ Back to Main Menu",font=self.font_button, command=self.return_to_main_menu)
        self.phase2_back_button.pack(pady=10)

        ########### Phase 2 Setup Segmentation Frame buttons
        # Phase 2 Setup Segmentation: Title
        # --- Title ---
        self.segmentation_label = customtkinter.CTkLabel(master=self.phase2_setup_segmentation_frame,text="Configure Segmentation",font=self.font)
        self.segmentation_label.pack(pady=10)

        # --- Tool Dropdown ---
        self.tool_label = customtkinter.CTkLabel(master=self.phase2_setup_segmentation_frame,text="Select Segmentation Tool",font=self.font)
        self.tool_label.pack()
        self.tool_var = customtkinter.StringVar()
        self.tool_dropdown = customtkinter.CTkOptionMenu(
            master=self.phase2_setup_segmentation_frame,
            variable=self.tool_var,
            values=list(SEGMENTATION_TOOLS.keys()),
            command=self.update_modality_dropdown,
            font=self.font
        )
        self.tool_dropdown.pack(pady=5)

        # --- Modality Dropdown ---
        self.modality_label = customtkinter.CTkLabel(master=self.phase2_setup_segmentation_frame,text="Select Image Modality",font=self.font)
        self.modality_label.pack()
        self.modality_var = customtkinter.StringVar()
        self.modality_dropdown = customtkinter.CTkOptionMenu(
            master=self.phase2_setup_segmentation_frame,
            variable=self.modality_var,
            values=["ct", "mr"],
            command=self.update_roi_and_other,
            font=self.font
        )
        self.modality_dropdown.pack(pady=5)

        # --- ROI Dropdown (updated based on tool + modality) ---
        self.roi_label = customtkinter.CTkLabel(master=self.phase2_setup_segmentation_frame,text="Select Region of Interest (ROI)",font=self.font)
        self.roi_label.pack()
        self.roi_var = customtkinter.StringVar()
        self.roi_dropdown = customtkinter.CTkOptionMenu(master=self.phase2_setup_segmentation_frame,variable=self.roi_var,values=[],font=self.font)
        self.roi_dropdown.pack(pady=5)

        # --- Other (multi-checkbox) ---
        self.other_label = customtkinter.CTkLabel(master=self.phase2_setup_segmentation_frame,text="Additional Structures to Segment (Optional)",font=self.font)
        self.other_label.pack()
        self.other_vars = {}
        self.other_frame = customtkinter.CTkScrollableFrame(master=self.phase2_setup_segmentation_frame, width=400, height=150)
        self.other_frame.pack(pady=5)

        # --- Fast checkbox ---
        self.fast_var = customtkinter.BooleanVar()
        self.fast_checkbox = customtkinter.CTkCheckBox(master=self.phase2_setup_segmentation_frame,text="⚡ Run in fast mode",variable=self.fast_var,font=self.font)
        self.fast_checkbox.pack(pady=5)

        # --- Confirm button ---
        self.confirm_segmentation_button = customtkinter.CTkButton(
            master=self.phase2_setup_segmentation_frame,
            text="✅ Confirm Segmentation Settings",
            font=self.font_button,
            command=self.confirm_segmentation_settings
        )
        self.confirm_segmentation_button.pack(pady=10)

        # Set initial values
        self.tool_var.set(list(SEGMENTATION_TOOLS.keys())[0])
        self.modality_var.set("ct")
        self.update_roi_and_other()

        # Back button
        self.phase2_setup_segmentation_back_button = customtkinter.CTkButton(master=self.phase2_setup_segmentation_frame, text="⬅️ Back to Main Menu", font=self.font_button, command=self.return_to_main_menu)
        self.phase2_setup_segmentation_back_button.pack(pady=10)

        ########### Phase 2 Setup Crop Frame buttons
        # Phase 2 Setup Crop: Title
        self.setup_crop_description = customtkinter.CTkLabel(master=self.phase2_setup_crop_frame, text="Setup Crop", font=self.font)
        self.setup_crop_description.pack(pady=10)
        
        # Plane Crop Button
        self.Plane_crop_btn = customtkinter.CTkButton(master=self.phase2_setup_crop_frame, text="Plane Crop", font=self.font_button, command=self.plane_crop_setup)
        self.Plane_crop_btn.pack(pady=10)

        # Scissor Crop Button
        self.Scissor_crop_btn = customtkinter.CTkButton(master=self.phase2_setup_crop_frame, text="Scissor Crop", font=self.font_button, command=self.scissor_crop_setup)
        self.Scissor_crop_btn.pack(pady=10)

        # Back button
        self.phase2_setup_crop_back_button = customtkinter.CTkButton(master=self.phase2_setup_crop_frame, text="⬅️ Back to Main Menu", font=self.font_button, command=self.return_to_main_menu)
        self.phase2_setup_crop_back_button.pack(pady=10)

        ########### Phase 2 Create Analysis Excel Frame buttons
        # Title
        self.select_create_excel_description = customtkinter.CTkLabel(master=self.phase2_analysis_results_excel_frame, text="Create Analysis Results Excel file", font=self.font)
        self.select_create_excel_description.pack(pady=10)

        # Entry for filename
        self.excel_entry = customtkinter.CTkEntry(master=self.phase2_analysis_results_excel_frame,placeholder_text="Enter filename (e.g., Analysis_Results.xlsx)",font=self.font)
        self.excel_entry.pack(pady=10)

        # Confirm button
        self.excel_confirm_button = customtkinter.CTkButton(master=self.phase2_analysis_results_excel_frame,text="✅ Confirm",font=self.font_button,command=self.gui_create_excel_file)
        self.excel_confirm_button.pack(pady=10)

        # Message label
        self.excel_status_label = customtkinter.CTkLabel(master=self.phase2_analysis_results_excel_frame,text="",font=self.font)
        self.excel_status_label.pack(pady=5)

        # Back button
        self.phase2_excel_back_button = customtkinter.CTkButton(master=self.phase2_analysis_results_excel_frame, text="⬅️ Back to Main Menu", font=self.font_button, command=self.return_to_main_menu)
        self.phase2_excel_back_button.pack(pady=10)

        ########### Phase 2 Setup General Analysis Frame buttons
        # Phase 2 Setup General Analysis: Title 
        self.setup_general_analysis_description = customtkinter.CTkLabel(master=self.phase2_setup_general_analysis_frame, text="Setup General Analysis", font=self.font)
        self.setup_general_analysis_description.pack(pady=10)

        # --- Dropdown for analysis type ---
        self.analysis_type_var = customtkinter.StringVar(value="Do not perform a general analysis")
        self.analysis_type_dropdown = customtkinter.CTkOptionMenu(
            master=self.phase2_setup_general_analysis_frame,
            variable=self.analysis_type_var,
            values=["Do not perform a general analysis", "Comparative Surgery Spinal Cord", "Psoas Atrophy Analysis"],
            command=self.update_case_selection_visibility,
            font=self.font
        )
        self.analysis_type_dropdown.pack(pady=10)

        # --- Case selection UI (only for comparative surgery) ---
        self.case_selection_label = customtkinter.CTkLabel(master=self.phase2_setup_general_analysis_frame,text="Select two cases for comparison:",font=self.font)

        self.case_1_var = customtkinter.StringVar()
        self.case_2_var = customtkinter.StringVar()

        self.case_1_dropdown = customtkinter.CTkOptionMenu(master=self.phase2_setup_general_analysis_frame,variable=self.case_1_var,values=[],font=self.font)

        self.case_2_dropdown = customtkinter.CTkOptionMenu(master=self.phase2_setup_general_analysis_frame,variable=self.case_2_var,values=[],font=self.font)

        # --- Confirm button ---
        self.confirm_analysis_button = customtkinter.CTkButton(
            master=self.phase2_setup_general_analysis_frame,
            text="✅ Confirm",
            font=self.font_button,
            command=self.confirm_analysis_setup
        )
        self.confirm_analysis_button.pack(pady=10)
        
        # Back button
        self.phase2_general_analysis_back_button = customtkinter.CTkButton(master=self.phase2_setup_general_analysis_frame, text="⬅️ Back to Main Menu", font=self.font_button, command=self.return_to_main_menu)
        self.phase2_general_analysis_back_button.pack(pady=10)

    ############## Phase 3 Frame buttons ########################################################################################
        ########### Phase 3 Overview frame buttons
        # Textbox for displaying overview summary
        self.phase3_overview_textbox = customtkinter.CTkTextbox(
            master=self.phase3_overview_frame,
            width=500,
            height=500,
            font=self.font
        )
        self.phase3_overview_textbox.pack(pady=10)
        self.phase3_overview_textbox.configure(state="disabled")

        # Confirm button to launch Phase 3
        self.phase3_overview_confirm_button = customtkinter.CTkButton(
            master=self.phase3_overview_frame,
            text="✅ Start Analysis",
            font=self.font_button,
            command=self.launch_phase3_execution
        )
        self.phase3_overview_confirm_button.pack(pady=10)

        # Back button
        self.phase3_overview_back_button = customtkinter.CTkButton(
            master=self.phase3_overview_frame,
            text="⬅️ Back to Main Menu",
            font=self.font,
            command=self.return_to_main_menu
        )
        self.phase3_overview_back_button.pack(pady=10)

        ########### Phase 3 Process frame buttons
        # --- Progress Label ---
        self.phase3_progress_label = customtkinter.CTkLabel(
            master=self.phase3_process_frame,
            text="Processing...",
            font=self.font
        )
        self.phase3_progress_label.pack(pady=5)

        # --- Progress Bar ---
        self.phase3_progress_bar = customtkinter.CTkProgressBar(
            master=self.phase3_process_frame,
            width=300
        )
        self.phase3_progress_bar.set(0)
        self.phase3_progress_bar.pack(pady=5)

        # --- Back to Main Menu (initially disabled) ---
        self.phase3_process_back_button = customtkinter.CTkButton(
            master=self.phase3_process_frame,
            text="⬅️ Back to Main Menu",
            font=self.font,
            command=self.return_to_main_menu,
            state="disabled"
        )
        self.phase3_process_back_button.pack(pady=10)

        
    def load_saved_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.results_path = config.get("results_path")
                self.slicer_path = config.get("slicer_path")
                self.remember_settings = config.get("remember", False)

    def save_config(self):
        if not self.remember_settings:
            return
        config = {
            "results_path": self.results_path,
            "slicer_path": self.slicer_path,
            "remember": True
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

    def toggle_remember(self):
        self.remember_settings = self.checkbox.get()

    def show_frame(self, frame_to_show):
        # Hide all frames
        # Frames
        self.initial_frame.pack_forget()
        self.main_frame.pack_forget()
        self.phase1_frame.pack_forget()
        self.individual_frame.pack_forget()
        self.batch_frame.pack_forget()
        self.indv_automatic_selection_frame.pack_forget()
        self.batch_automatic_selection_frame.pack_forget()
        self.manual_loading_frame.pack_forget()
        self.phase2_frame.pack_forget()
        self.phase2_steps_frame.pack_forget()
        self.phase2_setup_segmentation_frame.pack_forget()
        self.phase2_setup_crop_frame.pack_forget()
        self.phase2_analysis_results_excel_frame.pack_forget()
        self.phase2_setup_general_analysis_frame.pack_forget()
        self.phase3_overview_frame.pack_forget()
        self.phase3_process_frame.pack_forget()
        
        # Show only the one we want
        frame_to_show.pack(pady=20, padx=60, fill="both", expand=True)

    def select_main_directory(self):
        path = fd.askdirectory(title="Select Results Output Directory")
        if path:
            self.results_path = path
            self.label_main_path.configure(text=f"📂 {path}")
            self.save_config()

    def select_slicer_path(self):
        path = fd.askopenfilename(title="Select Slicer Executable", filetypes=[("Executable files", "*.exe")])
        if path:
            self.slicer_path = path
            self.label_slicer_path.configure(text=f"🧠 {self.slicer_path}")
            self.save_config()

    def start_app(self):
        if not self.results_path:
            print("❌ Please set the Results folder.")
            return
        if not self.slicer_path:
            print("❌ Please set the Slicer executable path.")
            return

        print("🚀 Starting pipeline...")
        self.save_config()
        self.return_to_main_menu()


    def find_patients(self):
        results_path = os.path.join(self.results_path, "Results")
        if not os.path.exists(results_path):
            self.n_loaded_patients = 0
            self.patients_w_json = []
            self.new_patients = []
            self.label_patient_count.configure(text="No patients loaded")
            return []

        txt_files = []
        patients_w_json = []
        new_patients = []

        for root, _, files in os.walk(results_path):
            for file in files:
                if file.endswith("_config.txt"):
                    txt_files.append(os.path.join(root, file))

        for path in txt_files:
            try:
                config = load_case_config(path)
                patient_number = config.get("patient_number", "❓Unknown")
                output_path = config.get("patient_output_path", "")
                json_path = os.path.join(output_path, f"PATIENT_{patient_number}_state.json")

                if os.path.exists(json_path):
                    patients_w_json.append(path)
                    #patients_w_json.append(f"Patient {patient_number}")
                else:
                    new_patients.append(path)
                    #patients_w_json.append(f"Patient {patient_number}")

            except Exception as e:
                print(f"❌ Could not parse config at {path}: {e}")

        # Save class-level attributes
        self.n_loaded_patients = len(txt_files)
        self.patients_w_json = patients_w_json
        self.new_patients = new_patients

        self.label_patient_count.configure(text=f"{self.n_loaded_patients} patients loaded")

        # Update textboxes
        self.box_new_patients.configure(state="normal")
        self.box_new_patients.delete("1.0", "end")
        if new_patients:
            self.box_new_patients.insert("end", "New Patients:\n")
            for path in new_patients:
                config = load_case_config(path)
                p_number = config.get("patient_number", "❓Unknown")
                p = f"Patient {p_number}"
                self.box_new_patients.insert("end", f"  - {p}\n")
        else:
            self.box_new_patients.insert("end", "No new patients found.")
        self.box_new_patients.configure(state="disabled")

        self.box_existing_patients.configure(state="normal")
        self.box_existing_patients.delete("1.0", "end")
        if patients_w_json:
            self.box_existing_patients.insert("end", "Existing Patients:\n")
            for path in patients_w_json:
                config = load_case_config(path)
                p_number = config.get("patient_number", "❓Unknown")
                p = f"Patient {p_number}"
                self.box_existing_patients.insert("end", f"  - {p}\n")
        else:
            self.box_existing_patients.insert("end", "No pre-analyzed patients found.")
        self.box_existing_patients.configure(state="disabled")

        return txt_files
    
    def update_main_menu(self):
        """Refresh patient list and export the Excel progression sheet."""
        txt_paths = self.find_patients()

        if txt_paths:
            export_patient_list_to_excel(txt_paths, self.results_path)
            print("✅ Patient progression exported to Excel.")

        self.label_patient_count.configure(text=f"{self.n_loaded_patients} patients loaded")

        """Set all analysis setup variables to None."""
        self.indiv_raw_path = None
        self.batch_csv_path = None
        self.batch_raw_path = None
        self.selected_new_patients = []
        self.selected_existing_patients = []
        self.new_objects = []
        self.reused_objects = []
        self.patient_objects = []
        self.selected_steps = []
        self.crop_mode = None
        self.excel_path = None
        self.selected_analysis_type = None
        self.case_1 = None
        self.case_2 = None


    def return_to_main_menu(self):
        self.update_main_menu()
        self.show_frame(self.main_frame)

    ######## PHASE 1 FUNCTIONS ###########################################################

    def phase_1_load_patients(self):
        self.show_frame(self.phase1_frame)
        print("Load Patients button clicked")
    
    def individual_patient_loading(self):
        self.show_frame(self.individual_frame)
        print("Individual Patient Loading button clicked")

    def select_individual_raw_folder(self):
        path = fd.askdirectory(title="Select Individual Patient Raw Data Folder")
        if path:
            self.indiv_raw_path = path
            self.label_indiv_raw_path.configure(text=f"📂 {path}")

    def image_selection_mode(self):
        if self.selection_mode.get() == "Automatic":
            self.show_frame(self.indv_automatic_selection_frame)
            print("Automatic Image Selection mode selected")

        elif self.selection_mode.get() == "Manual":
            self.show_frame(self.manual_loading_frame)
            print("Manual Image Selection mode selected")

    def on_start_automatic_selection(self, patient_id, case_type, level_pairs, visit_types, raw_path, selection_mode):
        self.indiv_progress_label.pack(pady=5)
        self.indiv_progress_bar.pack(pady=5)
        self.indiv_progress_bar.set(0)
        self.indiv_progress_bar.start()
        
        #Disable buttons
        self.automatic_back_button.configure(state="disabled")
        self.automatic_selection_button.configure(state="disabled")

        levels = []
        for pair in level_pairs:
                parts = pair.strip().split('-')
                if len(parts) != 2:
                    raise ValueError(f"Invalid format: '{pair}' — must be like 'L2-L3'")
                levels.extend(parts)

        patient_dict = {"patient_number": patient_id, "case_type": case_type, "levels": levels, "folder_path": raw_path, "visits": {}}
        for vt in visit_types:
            vt_path = os.path.join(raw_path, vt)
            if os.path.exists(vt_path):
                patient_dict["visits"][vt] = vt_path
            else:
                print(f"⚠️ Visit folder not found: {vt_path}")

        def run_and_finish():
            individual_patient_prep(patient_dict, self.results_path, selection_mode)
            self.after(0, lambda: [
                self.indiv_progress_bar.stop(),
                self.indiv_progress_bar.set(1),
                self.automatic_back_button.configure(state="normal"),
                self.automatic_selection_button.configure(state="normal"),
                print("✅ Individual selection complete.")
            ])

        threading.Thread(target=run_and_finish).start()


    def batch_patient_loading(self):
        self.show_frame(self.batch_frame)
        print("Batch Patient Loading button clicked")

    def select_batch_raw_folder(self):
        path = fd.askdirectory(title="Select Batch Raw Data Folder")
        if path:
            self.batch_raw_path = path
            self.label_batch_raw_path.configure(text=f"📂 {path}")
    
    def select_batch_csv(self):
        path = fd.askopenfilename(title="Select Batch CSV/Excel File", filetypes=[("Excel files", "*.xlsx"),("CSV files", "*.csv")])
        if path:
            self.batch_csv_path = path
            self.label_batch_csv.configure(text=f"📂 {path}")

    def image_selection_mode_batch(self):
        if self.selection_mode.get() == "Automatic":
            self.show_frame(self.batch_automatic_selection_frame)
            print("Automatic Image Selection mode selected")

        elif self.selection_mode.get() == "Manual":
            self.show_frame(self.manual_loading_frame)
            print("Manual Image Selection mode selected")

    def on_start_batch_automatic_selection(self, csv_path, raw_path, selection_mode):
        self.batch_progress_label.pack(pady=5)
        self.batch_progress_bar.pack(pady=5)
        self.batch_progress_bar.set(0)
        self.batch_progress_bar.start()
        self.batch_automatic_back_button.configure(state="disabled")
        self.batch_automatic_selection_button.configure(state="disabled")

        def run_and_finish():
            batch_patient_prep(csv_path, raw_path, self.results_path, selection_mode)
            self.after(0, lambda: [
                self.batch_progress_bar.stop(),
                self.batch_progress_bar.set(1),
                self.batch_automatic_back_button.configure(state="normal"),
                self.batch_automatic_selection_button.configure(state="normal"),
                print("✅ Batch selection complete.")
            ])

        threading.Thread(target=run_and_finish).start()


    ######## PHASE 2 FUNCTIONS ###########################################################

    def phase_2_setup_analysis(self):
        print("Setup Analysis button clicked")
        if self.n_loaded_patients == 0:
            print("❌ No patients loaded. Please load patients first.")
            return
        else:
            self.show_frame(self.phase2_frame)
            self.populate_patient_checkboxes()

    def populate_patient_checkboxes(self):
        self.patient_checkbox_vars_new = {}
        self.patient_checkbox_vars_existing = {}

        # Clear both frames
        for f in self.new_patients_frame.winfo_children()[1:]:  # Skip label
            f.destroy()
        for f in self.existing_patients_frame.winfo_children()[1:]:
            f.destroy()

        # Create checkboxes for each group
        for path in self.new_patients:
            config = load_case_config(path)
            pid = str(config.get("patient_number", "❓"))
            var = customtkinter.BooleanVar()
            self.patient_checkbox_vars_new[pid] = (var, path)

            row = customtkinter.CTkFrame(master=self.new_patients_frame)
            row.pack(fill="x", pady=2)
            customtkinter.CTkLabel(row, text=f"Patient {pid}", font=self.font).pack(side="left", padx=5)
            customtkinter.CTkCheckBox(row, variable=var, text="").pack(side="right", padx=5)

        for path in self.patients_w_json:
            config = load_case_config(path)
            pid = str(config.get("patient_number", "❓"))
            var = customtkinter.BooleanVar()
            self.patient_checkbox_vars_existing[pid] = (var, path)

            row = customtkinter.CTkFrame(master=self.existing_patients_frame)
            row.pack(fill="x", pady=2)
            customtkinter.CTkLabel(row, text=f"Patient {pid}", font=self.font).pack(side="left", padx=5)
            customtkinter.CTkCheckBox(row, variable=var, text="").pack(side="right", padx=5)


    def confirm_patient_selection(self):
        self.selected_new_patients = [path for pid, (var, path) in self.patient_checkbox_vars_new.items() if var.get()]
        self.selected_existing_patients = [path for pid, (var, path) in self.patient_checkbox_vars_existing.items() if var.get()]
        print("✅ Selected new patient config paths:")
        for path in self.selected_new_patients:
            print(f"  • {path}")

        print("✅ Selected existing patient config paths:")
        for path in self.selected_existing_patients:
            print(f"  • {path}")

        if self.selected_existing_patients:
            self.ask_overwrite_patient()

        else:
            self._skip_existing_patients()
            self.show_frame(self.phase2_steps_frame)

    def ask_overwrite_patient(self):
        CustomPopupWindow(
            master=self,
            title="Existing Patients Selected",
            message="What would you like to do with them?\n Overwrite will DELETE all existing progress!",
            options={
                "🔄 Reuse": self._reuse_existing_patients,
                "🧨 Overwrite": self._overwrite_existing_patients,
                "⏭️ Skip": self._skip_existing_patients
            }
        )

    def _reuse_existing_patients(self):
        print("♻️ Reusing selected existing patients...")

        for config_path in self.selected_existing_patients:
            config = load_case_config(config_path)
            patient_id = config["patient_number"]
            output_path = config["patient_output_path"]

            existing = Patient.load_from_json(output_path, patient_id)
            self.reused_objects.append(existing)
            continue
        
        if self.selected_new_patients:
            print("✨ Creating new patients from selected new patient configs...")
            self._skip_existing_patients()
        
        self.show_frame(self.phase2_steps_frame)

    def _overwrite_existing_patients(self):
        print("🧨 Overwriting selected existing patients...")

        for config_path in self.selected_existing_patients:
            config = load_case_config(config_path)
            patient_id = config["patient_number"]
            output_path = config["patient_output_path"]
            json_path = os.path.join(output_path, f"PATIENT_{patient_id}_state.json")
            print(f"⚠️ Overwriting Patient {patient_id} analysis files.")
            try:
                existing = Patient.load_from_json(output_path, patient_id)
                clean_patient_analysis_files(existing)
            except Exception as e:
                print(f"⚠️ Failed to clean previous analysis: {e}")
            os.remove(json_path)
            self.selected_new_patients.append(config_path)  # treat it like new patient

        self._skip_existing_patients()
        self.show_frame(self.phase2_steps_frame)

    def _skip_existing_patients(self):
        print("⏭️ Creating NEW patients...")
        for config_path in self.selected_new_patients:
            try:
                config = load_case_config(config_path)
                patient_id = config["patient_number"]
                print(f"✨ Creating Patient object for ID {patient_id}")

                patient = Patient(config)
                if config.get("pre_nifti_path"):
                    patient.pre.log_nifti(config["pre_nifti_path"])
                if config.get("post_nifti_path"):
                    patient.post.log_nifti(config["post_nifti_path"])

                self.new_objects.append(patient)

            except Exception as e:
                print(f"⚠️ Failed to prepare patient from {config_path}: {e}")
                continue

    def confirm_steps_selection(self):
        self.selected_steps = [step for step, var in self.step_vars.items() if var.get()]
        print("🧠 Selected processing steps:")
        for step in self.selected_steps:
            print(f"  • {step}")

        if not self.selected_steps:
            print("⚠️ No steps selected.")
            return

        print("Number of new patients:", len(self.new_objects))
        print("Number of reused patients:", len(self.reused_objects))

        # --- If new patients and segmentation is selected ---
        if "segmentation" in self.selected_steps and len(self.new_objects) > 0:
            self.show_frame(self.phase2_setup_segmentation_frame)
            return  # Let segmentation pipeline handle the rest

        # --- No new patients: assign reused patients now ---
        if len(self.new_objects) == 0:
            print("🔁 Only reused patients — assigning directly to self.patient_objects")
            self.patient_objects = self.reused_objects

        # --- Move to cropping setup ---
        if "cropping" in self.selected_steps:
            self.show_frame(self.phase2_setup_crop_frame)

        elif "Patient_volumetric_analysis" in self.selected_steps:
            self.show_frame(self.phase2_analysis_results_excel_frame)

        elif "general_analysis" in self.selected_steps:
            self.populate_case_dropdowns()
            self.show_frame(self.phase2_setup_general_analysis_frame)

        else:
            self.show_frame(self.phase3_overview_frame)
            self.populate_analysis_overview()


    def update_modality_dropdown(self, selected_tool):
        self.modality_var.set("ct")  # Default to ct when tool changes
        self.update_roi_and_other()

    def update_roi_and_other(self, *args):
        tool = self.tool_var.get()
        modality = self.modality_var.get()

        if tool not in SEGMENTATION_TOOLS or modality not in SEGMENTATION_TOOLS[tool]:
            return

        # Update ROI dropdown
        roi_options = SEGMENTATION_TOOLS[tool][modality]["roi_options"]
        self.roi_dropdown.configure(values=roi_options)
        self.roi_var.set(roi_options[0])

        # Clear and re-add "other" checkboxes
        for widget in self.other_frame.winfo_children():
            widget.destroy()
        self.other_vars = {}

        for label in SEGMENTATION_TOOLS[tool][modality]["other_options"]:
            if label == "none":
                continue
            var = customtkinter.BooleanVar()
            self.other_vars[label] = var
            cb = customtkinter.CTkCheckBox(self.other_frame, text=label, variable=var, font=self.font)
            cb.pack(anchor="w", padx=10, pady=2)

    def confirm_segmentation_settings(self):
        tool = self.tool_var.get()
        modality = self.modality_var.get()
        roi = self.roi_var.get()
        other = [k for k, v in self.other_vars.items() if v.get()]
        fast = self.fast_var.get()

        self.segmentation_config = {
            "tool": tool,
            "modality": modality,
            "roi": roi,
            "other": other,
            "fast": fast
        }

        for p in self.new_objects:
            p.segmentation_tool = self.segmentation_config["tool"]
            p.roi = self.segmentation_config["roi"]
            p.other = self.segmentation_config["other"]
            p.pre.log_modality(self.segmentation_config["modality"])
            p.post.log_modality(self.segmentation_config["modality"])
            p.use_fast = self.segmentation_config.get("fast", False)
            p.save_to_json()

        self.patient_objects = self.new_objects + self.reused_objects 

        # Move to next step
        if "cropping" in self.selected_steps:
            self.show_frame(self.phase2_setup_crop_frame)

        elif "Patient_volumetric_analysis" in self.selected_steps:
            self.show_frame(self.phase2_analysis_results_excel_frame)

        elif "general_analysis" in self.selected_steps:
            self.populate_case_dropdowns()
            self.show_frame(self.phase2_setup_general_analysis_frame)

        else:
            self.show_frame(self.phase3_overview_frame)
            self.populate_analysis_overview()

    def plane_crop_setup(self):
        self.crop_mode = "Plane Crop"
        print("✂️ Crop mode set to: Plane Crop")

        if "Patient_volumetric_analysis" in self.selected_steps:
            self.show_frame(self.phase2_analysis_results_excel_frame)

        elif "general_analysis" in self.selected_steps:
            self.populate_case_dropdowns()
            self.show_frame(self.phase2_setup_general_analysis_frame)

        else:
            self.show_frame(self.phase3_overview_frame)
            self.populate_analysis_overview()

    def scissor_crop_setup(self):
        self.crop_mode = "Scissor Crop"
        print("✂️ Crop mode set to: Scissor Crop")

        if "Patient_volumetric_analysis" in self.selected_steps:
            self.show_frame(self.phase2_analysis_results_excel_frame)

        elif "general_analysis" in self.selected_steps:
            self.populate_case_dropdowns()
            self.show_frame(self.phase2_setup_general_analysis_frame)

        else:
            self.show_frame(self.phase3_overview_frame)
            self.populate_analysis_overview()

    def gui_create_excel_file(self):
        filename = self.excel_entry.get().strip()
        if not filename:
            filename = "Analysis_Results.xlsx"
        if not filename.endswith(".xlsx"):
            filename += ".xlsx"

        excel_path = os.path.join(self.results_path, filename)

        def continue_to_next_step():
            if "general_analysis" in self.selected_steps:
                self.populate_case_dropdowns()
                self.show_frame(self.phase2_setup_general_analysis_frame)
            else:
                self.show_frame(self.phase3_overview_frame)
                self.populate_analysis_overview()

        if os.path.exists(excel_path):
            def handle_decision(choice):
                if choice == "overwrite":
                    self._finalize_excel_creation(excel_path)
                    continue_to_next_step()
                elif choice == "rename":
                    self.excel_status_label.configure(text="✏️ Please enter a new name.")

            self.show_excel_overwrite_popup(excel_path, handle_decision)
        else:
            self._finalize_excel_creation(excel_path)
            continue_to_next_step()

    def _finalize_excel_creation(self, path):
        wb = Workbook()
        ws = wb.active
        ws.title = "Volume Analysis"
        wb.save(path)

        self.excel_path = path
        self.excel_status_label.configure(text=f"✅ Excel created: {os.path.basename(path)}")
        print(f"✅ Created Excel at {path}")

    def show_excel_overwrite_popup(self, path, callback):
        CustomPopupWindow(
            master=self,
            title="File Exists",
            message=f"The file '{os.path.basename(path)}' already exists.\nWould you like to overwrite it or rename?",
            options={
                "Overwrite": lambda: callback("overwrite"),
                "Rename": lambda: callback("rename")
            }
        )

    def update_case_selection_visibility(self, choice):
        if choice == "Comparative Surgery Spinal Cord":
            self.case_selection_label.pack()
            self.case_1_dropdown.pack()
            self.case_2_dropdown.pack()
        else:
            self.case_selection_label.pack_forget()
            self.case_1_dropdown.pack_forget()
            self.case_2_dropdown.pack_forget()

    def populate_case_dropdowns(self):
        case_types = sorted(set(p.case_type for p in self.patient_objects))
        self.case_1_dropdown.configure(values=case_types)
        self.case_2_dropdown.configure(values=case_types)
        if case_types:
            self.case_1_var.set(case_types[0])
            self.case_2_var.set(case_types[1] if len(case_types) > 1 else case_types[0])

    def confirm_analysis_setup(self):
        selected = self.analysis_type_var.get()

        # Replace placeholder "General Analysis" in steps with selected type
        if "general_analysis" in self.selected_steps:
            index = self.selected_steps.index("general_analysis")

            if selected == "Do not perform a general analysis":
                self.selected_analysis_type = None
                self.case_1 = None
                self.case_2 = None
                self.selected_steps.pop(index)  # Remove "General Analysis"
                print("Skipping general analysis")

            else:
                self.selected_analysis_type = selected
                self.selected_steps[index] = selected  # Replace with actual analysis

                if selected == "Comparative Surgery Spinal Cord":
                    case_1 = self.case_1_var.get()
                    case_2 = self.case_2_var.get()
                    if case_1 == case_2:
                        print("Please select two different case types.")
                        return
                    self.case_1, self.case_2 = case_1, case_2
                    print(f"Comparative analysis: {case_1} vs {case_2}")
                else:
                    self.case_1, self.case_2 = None, None
                    print("Psoas Atrophy Analysis selected")

        # Done → move to Phase 3
        self.show_frame(self.phase3_overview_frame)
        self.populate_analysis_overview()

    ######## PHASE 3 FUNCTIONS ##########################################################
    def populate_analysis_overview(self):
        summary = "Analysis Overview\n\n"

        summary += f"Patients selected: {len(self.patient_objects)}\n"
        for p in self.patient_objects:
            summary += f"  - Patient {p.patient_number}\n"

        summary += "\nSelected steps:\n"
        for step in self.selected_steps:
            summary += f"  - {step}\n"

        if "Segmentation" in self.selected_steps and self.new_objects:
            example = self.new_objects[0]
            summary += "\nSegmentation configuration:\n"
            summary += f"  - Tool: {example.segmentation_tool}\n"
            summary += f"  - Modality: {example.pre.modality}\n"
            summary += f"  - ROI: {example.roi}\n"
            if example.other:
                summary += f"  - Additional: {', '.join(example.other)}\n"
            summary += f"  - Fast mode: {'Yes' if example.use_fast else 'No'}\n"

        if "Crop" in self.selected_steps:
            summary += f"\nCrop mode: {self.crop_mode}\n"

        if "Patient Analysis" in self.selected_steps:
            summary += f"\nExcel file: {os.path.basename(self.excel_path)}\n"

        if self.selected_analysis_type:
            summary += f"\nGeneral analysis: {self.selected_analysis_type}\n"
            if self.selected_analysis_type == "Comparative Surgery Spinal Cord":
                summary += f"  - Case 1: {self.case_1}\n"
                summary += f"  - Case 2: {self.case_2}\n"
        else:
            summary += "\nGeneral analysis: Not performed\n"

        # Display in textbox
        self.phase3_overview_textbox.configure(state="normal")
        self.phase3_overview_textbox.delete("1.0", "end")
        self.phase3_overview_textbox.insert("1.0", summary)
        self.phase3_overview_textbox.configure(state="disabled")

    def launch_phase3_execution(self):
        self.show_frame(self.phase3_process_frame)
        self.phase3_progress_bar.set(0)
        self.phase3_progress_bar.start()
        self.phase3_process_back_button.configure(state="disabled")
        print("🚀 Starting analysis...")
        def run_execution():
            try:
                execute_analysis(self.patient_objects, self.selected_steps, self.crop_mode, self.slicer_path, self.excel_path, self.results_path, self.case_1, self.case_2)
            except Exception as e:
                print(f"❌ Execution failed: {e}")
            finally:
                        self.after(0, lambda: [
                            self.phase3_progress_bar.stop(),
                            self.phase3_progress_bar.set(1),
                            self.phase3_process_back_button.configure(state="normal"),
                            print("✅ Analysis complete.")
                        ])

        threading.Thread(target=run_execution).start()


class CustomPopupWindow(customtkinter.CTkToplevel):
    def __init__(self, master, title, message, options: dict):
        super().__init__(master)
        self.title(title)
        self.geometry("420x180")
        self.resizable(False, False)
        self.grab_set()  # Modal behavior

        label = customtkinter.CTkLabel(self, text=message, font=customtkinter.CTkFont(size=14))
        label.pack(pady=20, padx=20)

        btn_frame = customtkinter.CTkFrame(self)
        btn_frame.pack(pady=10)

        for text, callback in options.items():
            customtkinter.CTkButton(
                btn_frame, text=text, width=100,
                command=lambda cb=callback: self._handle_click(cb)
            ).pack(side="left", padx=10)

    def _handle_click(self, callback):
        callback()
        self.destroy()


# Run app
app = App()
app.mainloop()