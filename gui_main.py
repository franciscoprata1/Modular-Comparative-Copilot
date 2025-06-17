import customtkinter
from customtkinter import CTkFont
import tkinter.filedialog as fd
import json
import os
from Prep_and_Tools.patient_tools import load_case_config

CONFIG_FILE = "gui_config.json"

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Modular Imaging Pipeline")
        self.geometry("1000x600")

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
        self.n_loaded_patients = None
        self.patients_w_json = []
        self.new_patients = []
        self.load_saved_config()

        # Frames
        self.initial_frame = customtkinter.CTkFrame(self)
        self.main_frame = customtkinter.CTkFrame(self)

        # Set initial Frame
        self.initial_frame.pack(pady=20, padx=60, fill="both", expand=True)

        # Title frames
        self.initial_label = customtkinter.CTkLabel(master=self.initial_frame, text="Welcome! Please set initial configuration:", font=self.font_title)
        self.initial_label.pack(pady=12, padx=10)

        self.main_label = customtkinter.CTkLabel(master=self.main_frame, text="Modular Comparative Copilot: Main Menu", font=self.font_title)
        self.main_label.pack(pady=12, padx=10)

        ## Buttons and Labels for initial Frame
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

        ## Main Frame buttons
        # Load Patients
        self.button1 = customtkinter.CTkButton(master=self.main_frame, text="Load Patients", command=self.phase_1_load_patients, font=self.font_button)
        self.button1.pack(pady=6, padx=10)

        # Label for patient count
        self.label_patient_count = customtkinter.CTkLabel(master=self.main_frame, text=f"{self.n_loaded_patients} patients loaded" if self.n_loaded_patients else "No patients loaded", font=self.font)
        self.label_patient_count.pack(pady=4, padx=10)

        # Textboxes for patient lists
        self.box_new_patients = customtkinter.CTkTextbox(master=self.main_frame, width=400, height=70, font=self.font)
        self.box_new_patients.pack(pady=4)
        self.box_new_patients.configure(state="disabled")

        self.box_existing_patients = customtkinter.CTkTextbox(master=self.main_frame, width=400, height=70, font=self.font)
        self.box_existing_patients.pack(pady=4)
        self.box_existing_patients.configure(state="disabled")

        # Configure Analysis
        self.button2 = customtkinter.CTkButton(master=self.main_frame, text="Setup Analysis", command=self.phase_2_setup_analysis, font=self.font_button)
        self.button2.pack(pady=6, padx=10)

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
        self.initial_frame.pack_forget()
        self.main_frame.pack_forget()
        
        # Show only the one we want
        frame_to_show.pack(fill="both", expand=True)

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
        self.show_frame(self.main_frame)
        self.main_frame.pack(pady=20, padx=60, fill="both", expand=True)
        self.find_patients()
        self.label_patient_count.configure(text=f"{self.n_loaded_patients} patients loaded")


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
                    patients_w_json.append(f"Patient {patient_number}")
                else:
                    new_patients.append(f"Patient {patient_number}")

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
            for p in new_patients:
                self.box_new_patients.insert("end", f"  - {p}\n")
        else:
            self.box_new_patients.insert("end", "No new patients found.")
        self.box_new_patients.configure(state="disabled")

        self.box_existing_patients.configure(state="normal")
        self.box_existing_patients.delete("1.0", "end")
        if patients_w_json:
            self.box_existing_patients.insert("end", "Existing Patients:\n")
            for p in patients_w_json:
                self.box_existing_patients.insert("end", f"  - {p}\n")
        else:
            self.box_existing_patients.insert("end", "No pre-analyzed patients found.")
        self.box_existing_patients.configure(state="disabled")

        return None

    def phase_1_load_patients(self):
        print("Load Patients button clicked")
        # Here you would implement the logic to load patients
        self.find_patients()
        self.label_patient_count.configure(text=f"{self.n_loaded_patients} patients loaded")


    def phase_2_setup_analysis(self):
        print("Setup Analysis button clicked")
        # Here you would implement the logic to setup analysis


# Run app
app = App()
app.mainloop()
