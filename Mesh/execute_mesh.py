import os
import json
import subprocess
import tempfile


def mesh_process(patient, visit_type, slicer_path):
    """
    Executes the mesh generation process for a given patient visit using the MeshGeneration.py script.
    """
    print(f"\n🔧 MESHING — Patient {patient.patient_number} | Visit: {visit_type}")

    # Extract data
    patient_number = patient.patient_number
    visit = patient.pre if visit_type == "PRE" else patient.post
    seg_paths = visit.segmentation_paths
    output_dir = visit.visit_output_path
    if not seg_paths or not all(os.path.exists(p) for p in seg_paths):
        print(f"⚠️ No segmentation files found for {visit_type}")
        return
    roi = patient.roi

    # Path to MeshGeneration.py in the Tools/Mesh folder
    mesh_folder = os.path.abspath("Mesh")
    mesh_script_path = os.path.join(mesh_folder, "MeshGeneration.py")

    mesh_paths=[]

    for seg_path in seg_paths:
                base_name = os.path.basename(seg_path).replace("Segmentation_", "").replace(".nii.gz", "")

                # Create mesh subfolder
                mesh_output_dir = os.path.join(output_dir, f"Mesh_{base_name}")
                os.makedirs(mesh_output_dir, exist_ok=True)

                # Construct the input data
                mesh_input = {
                    "patient_id": patient_number,
                    "visit_type": visit_type,
                    "segmentation_path": seg_path,
                    "output_dir": mesh_output_dir,
                    "roi": roi  
                    }


                # Save the input to a temporary JSON file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as temp_file:
                    json.dump(mesh_input, temp_file)
                    temp_json_path = temp_file.name

                try:
                    # Run slicer with the temp JSON path as an argument
                    subprocess.run([slicer_path, "--python-script", mesh_script_path, temp_json_path], check=True)
                    print(f"✅ Mesh generation completed for Patient {patient.patient_number} — {visit_type}")
                    
                    # Clean up the temporary JSON file
                    os.remove(temp_json_path)

                    # ✅ Log mesh output
                    if os.path.exists(mesh_output_dir):
                        out_path = os.path.join(mesh_output_dir)
                        mesh_paths.append(out_path)

                except subprocess.CalledProcessError as e:
                    print(f"❌ Mesh generation failed for Patient {patient.patient_number} — {visit_type}: {e}")

    visit.log_mesh(mesh_paths)
