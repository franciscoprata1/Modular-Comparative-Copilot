import os
import json
import subprocess
import tempfile


def plane_crop_process(patient, slicer_path):
    """
    Executes the plane crop process for a given patient using the PlaneCrop.py script.
    Adapts to ROI-specific registration folders (e.g., spinal_cord = 1 folder, iliopsoas = 2 folders).
    """
    print(f"\n🔧 CROP — Patient {patient.patient_number}")

    patient_number = patient.patient_number
    reg_paths = patient.registration_paths
    output_dir = patient.output_path
    roi = patient.roi

    if not reg_paths or not all(os.path.exists(p) for p in reg_paths):
        print(f"⚠️ No registration files found for Patient {patient_number}")
        return

    crop_folder = os.path.abspath("Crop")
    crop_script_path = os.path.join(crop_folder, "PlaneCrop.py")

    crop_paths = []

    for reg_path in reg_paths:
        base_name = os.path.basename(reg_path).replace("Registration_", "")
        
        if roi == "spinal_cord":
            crop_output_dir = os.path.join(output_dir, f"Crop_{base_name}")
            os.makedirs(crop_output_dir, exist_ok=True)

            crop_input = {
                "patient_id": patient_number,
                "registration_path": reg_path,
                "output_dir": crop_output_dir,
                "base_name": base_name,
                "roi": roi,
                "patient_dir": output_dir
            }

            with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as temp_file:
                json.dump(crop_input, temp_file)
                temp_json_path = temp_file.name

            try:
                subprocess.run([slicer_path, "--python-script", crop_script_path, temp_json_path], check=True)
                print(f"✅ Crop completed for {base_name}")
                os.remove(temp_json_path)
                crop_paths.append(crop_output_dir)

            except subprocess.CalledProcessError as e:
                print(f"❌ Error cropping spinal cord: {e}")

        elif roi == "iliopsoas":
            for side in ["Left_Iliopsoas", "Right_Iliopsoas"]:
                subfolder = os.path.join(reg_path, side)
                if not os.path.exists(subfolder):
                    print(f"⚠️ Missing expected folder: {subfolder}")
                    continue

                crop_output_dir = os.path.join(output_dir, f"Crop_{base_name}", side)
                os.makedirs(crop_output_dir, exist_ok=True)

                crop_input = {
                    "patient_id": patient_number,
                    "registration_path": subfolder,
                    "output_dir": crop_output_dir,
                    "base_name": base_name,
                    "roi": roi,
                    "patient_dir": output_dir
                }

                with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as temp_file:
                    json.dump(crop_input, temp_file)
                    temp_json_path = temp_file.name

                try:
                    subprocess.run([slicer_path, "--python-script", crop_script_path, temp_json_path], check=True)
                    print(f"✅ Crop completed for {side} — {base_name}")
                    os.remove(temp_json_path)
                    crop_paths.append(crop_output_dir)

                except subprocess.CalledProcessError as e:
                    print(f"❌ Error cropping {side}: {e}")

        else:
            print(f"⚠️ ROI '{roi}' not supported in cropping")

    patient.log_crop(crop_paths)


def scissor_crop_process(patient, slicer_path):
    """
    Executes the scissor crop process for a given patient using the ScissorCrop.py script.
    Adapts to ROI-specific registration folders (e.g., spinal_cord = 1 folder, iliopsoas = 2 folders).
    """
    print(f"\n🔧 CROP — Patient {patient.patient_number}")

    patient_number = patient.patient_number
    reg_paths = patient.registration_paths
    output_dir = patient.output_path
    roi = patient.roi

    if not reg_paths or not all(os.path.exists(p) for p in reg_paths):
        print(f"⚠️ No registration files found for Patient {patient_number}")
        return

    crop_folder = os.path.abspath("Crop")
    crop_script_path = os.path.join(crop_folder, "ScissorCrop.py")

    crop_paths = []

    for reg_path in reg_paths:
        base_name = os.path.basename(reg_path).replace("Registration_", "")

        if roi == "spinal_cord":
            crop_output_dir = os.path.join(output_dir, f"Crop_{base_name}")
            os.makedirs(crop_output_dir, exist_ok=True)

            crop_input = {
                "patient_id": patient_number,
                "registration_path": reg_path,
                "output_dir": crop_output_dir,
                "base_name": base_name,
                "roi": roi,
                "patient_dir": output_dir
            }

            with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as temp_file:
                json.dump(crop_input, temp_file)
                temp_json_path = temp_file.name

            try:
                subprocess.run([slicer_path, "--python-script", crop_script_path, temp_json_path], check=True)
                print(f"✅ Scissor crop completed for {base_name}")
                os.remove(temp_json_path)
                crop_paths.append(crop_output_dir)

            except subprocess.CalledProcessError as e:
                print(f"❌ Error scissor cropping spinal cord: {e}")

        elif roi == "iliopsoas":
            for side in ["Left_Iliopsoas", "Right_Iliopsoas"]:
                subfolder = os.path.join(reg_path, side)
                if not os.path.exists(subfolder):
                    print(f"⚠️ Missing expected folder: {subfolder}")
                    continue

                crop_output_dir = os.path.join(output_dir, f"Crop_{base_name}", side)
                os.makedirs(crop_output_dir, exist_ok=True)

                crop_input = {
                    "patient_id": patient_number,
                    "registration_path": subfolder,
                    "output_dir": crop_output_dir,
                    "base_name": base_name,
                    "roi": roi,
                    "patient_dir": output_dir
                }

                with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as temp_file:
                    json.dump(crop_input, temp_file)
                    temp_json_path = temp_file.name

                try:
                    subprocess.run([slicer_path, "--python-script", crop_script_path, temp_json_path], check=True)
                    print(f"✅ Scissor crop completed for {side} — {base_name}")
                    os.remove(temp_json_path)
                    crop_paths.append(crop_output_dir)

                except subprocess.CalledProcessError as e:
                    print(f"❌ Error scissor cropping {side}: {e}")

        else:
            print(f"⚠️ ROI '{roi}' not supported in cropping")

    patient.log_crop(crop_paths)
