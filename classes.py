import os
import shutil
import json

class VisitData:
    def __init__(self, visit_type, base_output_path, modality=None):
        self.visit_type = visit_type
        self.visit_output_path = os.path.join(base_output_path, visit_type)
        self.nifti_path = None
        self.segmentation_paths = []
        self.other_segmentations_path = None
        self.mesh_paths = []
        self.modality = modality

    def log_modality(self, modality):
        self.modality = modality

    def log_nifti(self, path):
        self.nifti_path = path

    def log_segmentation(self, path_or_list):
        self.segmentation_paths = path_or_list if isinstance(path_or_list, list) else [path_or_list]

    def log_other_segmentations(self, folder_path):
        self.other_segmentations_path = folder_path

    def log_mesh(self, path_or_list):
        self.mesh_paths = path_or_list if isinstance(path_or_list, list) else [path_or_list]

    def to_dict(self):
        return {
            "modality": self.modality,
            "visit_type": self.visit_type,
            "visit_output_path": self.visit_output_path,
            "nifti_path": self.nifti_path,
            "segmentation_paths": self.segmentation_paths,
            "other_segmentations_path": self.other_segmentations_path,
            "mesh_paths": self.mesh_paths,
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(data["visit_type"], os.path.dirname(data["visit_output_path"]), data.get("modality"))
        obj.nifti_path = data.get("nifti_path")
        obj.segmentation_paths = data.get("segmentation_paths", [])
        obj.other_segmentations_path = data.get("other_segmentations_path")
        obj.mesh_paths = data.get("mesh_paths", [])
        return obj


class Patient:
    def __init__(self, config):
        self.patient_number = config["patient_number"]
        self.case_type = config["case_type"]
        self.levels = config.get("level_intervened", [])
        self.output_path = config["patient_output_path"]

        # Visit Data
        self.pre = VisitData("PRE", self.output_path)
        self.post = VisitData("POST", self.output_path)

        # Other Patient Data
        self.segmentation_tool = config.get("segmentation_tool", "N/A")
        self.roi = config.get("roi", "N/A")
        self.other = config.get("other", [])
        self.use_fast = config.get("use_fast", False)
        
        # Patient-Level Analysis Attributes
        self.registration_paths = []  # Stores paths to registered meshes
        self.crop_paths = []          # Stores paths to cropped meshes
        self.analysis_paths = []  # Stores paths to analysis results

    def log_registration(self, path_or_list):
        """Logs registration paths at the patient level."""
        self.registration_paths = path_or_list if isinstance(path_or_list, list) else [path_or_list]

    def log_crop(self, path_or_list):
        """Logs crop paths at the patient level."""
        self.crop_paths = path_or_list if isinstance(path_or_list, list) else [path_or_list]

    def log_analysis(self, path_or_list):
        """Logs analysis paths at the patient level."""
        self.analysis_paths = path_or_list if isinstance(path_or_list, list) else [path_or_list]

    def summary(self):
        print(f"🧬 Patient #{self.patient_number} | Type: {self.case_type}")
        
        print("  PRE visit:")
        for k, v in vars(self.pre).items():
            if v:
                print(f"    - {k}: {v}")
        
        print("  POST visit:")
        for k, v in vars(self.post).items():
            if v:
                print(f"    - {k}: {v}")
        
        print("  Patient-Level Paths:")
        print(f"    - Registration paths: {self.registration_paths}")
        print(f"    - Crop paths: {self.crop_paths}")
        print(f"    - Analysis paths: {self.analysis_paths}")

    def to_dict(self):
        return {
            "patient_number": self.patient_number,
            "case_type": self.case_type,
            "levels": self.levels,
            "roi": self.roi,
            "other": self.other,
            "segmentation_tool": self.segmentation_tool,
            "use_fast": self.use_fast,
            "output_path": self.output_path,
            "pre": self.pre.to_dict(),
            "post": self.post.to_dict(),
            "registration_paths": self.registration_paths,
            "crop_paths": self.crop_paths,
            "analysis_paths": self.analysis_paths,
        }

    @classmethod
    def from_dict(cls, data):
        config = {
            "patient_number": data["patient_number"],
            "case_type": data["case_type"],
            "level_intervened": data.get("levels", []),
            "roi": data.get("roi", "N/A"),
            "other": data.get("other", []),
            "segmentation_tool": data.get("segmentation_tool", "N/A"),
            "patient_output_path": data["output_path"],
            "use_fast": data.get("use_fast", False),
        }
        patient = cls(config)
        patient.pre = VisitData.from_dict(data["pre"])
        patient.post = VisitData.from_dict(data["post"])
        patient.registration_paths = data.get("registration_paths", [])
        patient.crop_paths = data.get("crop_paths", [])
        patient.analysis_paths = data.get("analysis_paths", {})
        return patient

    def save_to_json(self):
        json_path = os.path.join(self.output_path, f"PATIENT_{self.patient_number}_state.json")
        with open(json_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"🧾 Saved patient state to: {json_path}")

    @staticmethod
    def load_from_json(output_path, patient_number):
        json_path = os.path.join(output_path, f"PATIENT_{patient_number}_state.json")
        if not os.path.exists(json_path):
            return None
        with open(json_path, 'r') as f:
            data = json.load(f)
        print(f"📂 Loaded patient state from: {json_path}")
        return Patient.from_dict(data)
