import os
import shutil
import open3d as o3d
import numpy as np
import vtk
import trimesh

def extract_mesh_info(patient):
    """
    Extracts paths to relevant meshes based on patient levels and ROI for both PRE and POST visits.
    Handles multi-level patients with multiple mesh paths.

    Args:
        patient (Patient): Patient object containing levels, ROI, and mesh paths information.

    Returns:
        dict: Structured dictionary with paths to relevant meshes for each level pair.
    """
    roi = patient.roi

    mesh_info = {}

    # Iterate over PRE and POST
    for visit_type in ["PRE", "POST"]:
        visit = getattr(patient, visit_type.lower())
        mesh_paths = visit.mesh_paths

        if not mesh_paths:
            print(f"❌ No mesh paths available for {visit_type}.")
            continue

        # Iterate over each mesh folder (e.g., Mesh_L3_L4, Mesh_L4_L5)
        for mesh_folder in mesh_paths:
            if not os.path.exists(mesh_folder):
                print(f"⚠️ Mesh folder not found: {mesh_folder}")
                continue

            # Extract levels from the folder name (e.g., Mesh_L3_L4)
            folder_name = os.path.basename(mesh_folder)
            level_pair = folder_name.replace("Mesh_", "")

            # Ensure valid level pair
            levels_split = level_pair.split("_")
            if len(levels_split) != 2:
                print(f"⚠️ Invalid level pair format in {folder_name}. Skipping.")
                continue

            sup_level, inf_level = levels_split

            # Initialize nested structure if not present
            if level_pair not in mesh_info:
                mesh_info[level_pair] = {
                    "PRE": {"roi": {}, "vertebrae": {}},
                    "POST": {"roi": {}, "vertebrae": {}}
                }

            # Iterate through mesh files in the mesh folder
            for file in os.listdir(mesh_folder):
                file_path = os.path.join(mesh_folder, file)
                if file.endswith(".obj"):
                    # Identify ROI mesh
                    if roi == "spinal_cord" and file.startswith("SpinalCord"):
                        mesh_info[level_pair][visit_type]["roi"][level_pair] = file_path

                    elif roi == "iliopsoas":
                        for key in ["Iliopsoas_Left", "Iliopsoas_Right"]:
                            if file.startswith(key):
                                if level_pair not in mesh_info:
                                    mesh_info[level_pair] = {
                                        "PRE": {"roi": {}, "vertebrae": {}},
                                        "POST": {"roi": {}, "vertebrae": {}}
                                    }
                                mesh_info[level_pair][visit_type]["roi"][key] = file_path

                    # Identify vertebra meshes
                    if file.startswith("Vertebra_Superior"):
                        mesh_info[level_pair][visit_type]["vertebrae"][sup_level] = file_path
                    elif file.startswith("Vertebra_Inferior"):
                        mesh_info[level_pair][visit_type]["vertebrae"][inf_level] = file_path

            # Check for missing essential meshes
            for level in [sup_level, inf_level]:
                if level not in mesh_info[level_pair][visit_type]["vertebrae"]:
                    print(f"❌ Vertebra mesh 'vertebrae_{level}' not found in {mesh_folder} for {visit_type}")

    return mesh_info


def combine_vertebrae(mesh_info, level_pair, visit_type, output_path):
    """
    Combines the superior and inferior vertebrae meshes into a single mesh for a specific level pair.

    Args:
        mesh_info (dict): Dictionary containing mesh paths for each level pair.
        level_pair (str): The level pair identifier (e.g., "L3_L4").
        visit_type (str): "PRE" or "POST".
        output_path (str): Path to save the combined mesh.

    Returns:
        str: Path to the saved combined mesh.
    """
    vertebrae_info = mesh_info.get(level_pair, {}).get(visit_type, {}).get("vertebrae", {})
    
    # Extract paths to superior and inferior vertebrae
    sup_path = vertebrae_info.get(level_pair.split("_")[0])
    inf_path = vertebrae_info.get(level_pair.split("_")[1])

    if not sup_path or not inf_path:
        print(f"❌ Missing vertebrae meshes for {level_pair} - {visit_type}")
        return None

    try:
        # Load meshes
        sup_mesh = trimesh.load_mesh(sup_path)
        inf_mesh = trimesh.load_mesh(inf_path)

        # Combine meshes
        combined_mesh = trimesh.util.concatenate([sup_mesh, inf_mesh])

        # Save combined mesh
        combined_mesh.export(output_path)
        print(f"✅ Combined vertebrae mesh saved at {output_path}")

        return output_path

    except Exception as e:
        print(f"❌ Error combining vertebrae meshes for {level_pair} - {visit_type}: {e}")
        return None


def spinal_cord_registration(prep, level_pair, registration_dir):
    """
    Performs ICP registration for spinal cord using combined vertebrae models.
    PRE is registered to POST and saved in the registration folder.

    Args:
        prep (dict): Contains pre/post vertices, triangles, and vertebrae .obj paths.
        level_pair (str): e.g., "L3_L4".
        registration_dir (str): Where to save the registered mesh.

    Returns:
        None
    """
    print(f"🔁 Registering {level_pair} using ICP")

    # Load combined vertebrae models
    pre_model_reader = vtk.vtkOBJReader()
    pre_model_reader.SetFileName(prep["PRE"]["vertebrae_model"])
    pre_model_reader.Update()

    post_model_reader = vtk.vtkOBJReader()
    post_model_reader.SetFileName(prep["POST"]["vertebrae_model"])
    post_model_reader.Update()

    # Setup ICP transform
    icp = vtk.vtkIterativeClosestPointTransform()
    icp.SetSource(pre_model_reader.GetOutput())
    icp.SetTarget(post_model_reader.GetOutput())
    icp.GetLandmarkTransform().SetModeToRigidBody()
    icp.SetMeanDistanceModeToRMS()
    icp.SetMaximumNumberOfIterations(2000)
    icp.SetMaximumNumberOfLandmarks(300)
    icp.Update()

    # Build transformation matrix
    matrix = icp.GetMatrix()
    transform = np.array([[matrix.GetElement(i, j) for j in range(4)] for i in range(4)])

    # Apply transformation to PRE ROI mesh
    pre_vertices = prep["PRE"]["vertices"]
    pre_triangles = prep["PRE"]["triangles"]

    transformed_vertices = np.dot(
        np.hstack((pre_vertices, np.ones((pre_vertices.shape[0], 1)))),
        transform.T
    )[:, :3]

    pre_registered = o3d.geometry.TriangleMesh()
    pre_registered.vertices = o3d.utility.Vector3dVector(transformed_vertices)
    pre_registered.triangles = o3d.utility.Vector3iVector(pre_triangles)

    pre_save_path = os.path.join(registration_dir, f"{level_pair}_PRE_registered.obj")
    o3d.io.write_triangle_mesh(pre_save_path, pre_registered)

    # Copy vertebrae model for visualization
    shutil.copy2(prep["POST"]["vertebrae_model"], registration_dir)

    # Clean up temp files
    os.remove(prep["PRE"]["vertebrae_model"])
    os.remove(prep["POST"]["vertebrae_model"])

    print(f"✅ Registration complete for {level_pair}")

def iliopsoas_registration(prep, level_pair, registration_dir):
    """
    Applies ICP transform from vertebrae alignment to both iliopsoas sides.
    Saves output in Left_Iliopsoas and Right_Iliopsoas subfolders.

    Args:
        prep (dict): Contains pre/post iliopsoas vertices and vertebrae models
        level_pair (str): e.g., "L3_L4"
        registration_dir (str): base folder for saving registered output
    """
    print(f"🔁 Registering iliopsoas for {level_pair} using vertebrae-based ICP")

    # Load vertebrae models
    pre_model_reader = vtk.vtkOBJReader()
    pre_model_reader.SetFileName(prep["PRE"]["vertebrae_model"])
    pre_model_reader.Update()

    post_model_reader = vtk.vtkOBJReader()
    post_model_reader.SetFileName(prep["POST"]["vertebrae_model"])
    post_model_reader.Update()

    # Compute ICP
    icp = vtk.vtkIterativeClosestPointTransform()
    icp.SetSource(pre_model_reader.GetOutput())
    icp.SetTarget(post_model_reader.GetOutput())
    icp.GetLandmarkTransform().SetModeToRigidBody()
    icp.SetMeanDistanceModeToRMS()
    icp.SetMaximumNumberOfIterations(2000)
    icp.SetMaximumNumberOfLandmarks(300)
    icp.Update()

    matrix = icp.GetMatrix()
    transform = np.array([[matrix.GetElement(i, j) for j in range(4)] for i in range(4)])

    for side in ["left", "right"]:
        key = f"iliopsoas_{side}"
        folder_name = f"{side.capitalize()}_Iliopsoas"
        side_output_dir = os.path.join(registration_dir, folder_name)
        os.makedirs(side_output_dir, exist_ok=True)

        # 1. Transform and save PRE
        if key in prep["PRE"]:
            pre_data = prep["PRE"][key]
            pre_vertices = pre_data["vertices"]
            pre_triangles = pre_data["triangles"]

            transformed = np.dot(
                np.hstack((pre_vertices, np.ones((pre_vertices.shape[0], 1)))),
                transform.T
            )[:, :3]

            mesh = o3d.geometry.TriangleMesh()
            mesh.vertices = o3d.utility.Vector3dVector(transformed)
            mesh.triangles = o3d.utility.Vector3iVector(pre_triangles)

            out_path = os.path.join(side_output_dir, f"{level_pair}_PRE_registered.obj")
            o3d.io.write_triangle_mesh(out_path, mesh)

        else:
            print(f"⚠️ Missing PRE mesh for {key} — skipping")

        # 2. Save original POST mesh for visual comparison
        if key in prep["POST"]:
            post_data = prep["POST"][key]
            post_vertices = post_data["vertices"]
            post_triangles = post_data["triangles"]

            mesh = o3d.geometry.TriangleMesh()
            mesh.vertices = o3d.utility.Vector3dVector(post_vertices)
            mesh.triangles = o3d.utility.Vector3iVector(post_triangles)

            out_path = os.path.join(side_output_dir, f"{level_pair}_POST_registered.obj")
            o3d.io.write_triangle_mesh(out_path, mesh)

        else:
            print(f"⚠️ Missing POST mesh for {key} — skipping")

        # 3. Copy vertebrae model for context
        shutil.copy2(prep["POST"]["vertebrae_model"], os.path.join(side_output_dir, f"{level_pair}_Vertebrae.obj"))

    # Final cleanup
    os.remove(prep["PRE"]["vertebrae_model"])
    os.remove(prep["POST"]["vertebrae_model"])

    print(f"✅ Iliopsoas registration done for {level_pair} — split into Left and Right folders")


def registration_process(patient):
    """
    Modular registration entry point — prepares data and calls appropriate registration function
    depending on ROI type (e.g., spinal_cord, iliopsoas).
    """
    if not patient.pre.mesh_paths or not patient.post.mesh_paths:
        print(f"⏭️ Skipping registration for Patient {patient.patient_number} — Missing PRE or POST mesh.")
        return

    mesh_info = extract_mesh_info(patient)
    if not mesh_info:
        print(f"⏭️ Skipping registration for Patient {patient.patient_number} — No mesh info extracted.")
        return
    
    reg_paths = []
    
    for level_pair in mesh_info:
        print(f"\n🧠 Running registration for level pair: {level_pair}")

        registration_dir = os.path.join(patient.output_path, f"Registration_{level_pair}")
        os.makedirs(registration_dir, exist_ok=True)

        prep = {
            "PRE": {},
            "POST": {}
        }

        for visit_type in ["PRE", "POST"]:
            visit = getattr(patient, visit_type.lower())
            visit_output = visit.visit_output_path

            # Step 1: Combine vertebrae
            combined_path = os.path.join(visit_output, f"{level_pair}_Vertebrae.obj")
            combined_model = combine_vertebrae(mesh_info, level_pair, visit_type, combined_path)
            prep[visit_type]["vertebrae_model"] = combined_model

            # Step 2: Parse ROI-specific meshes
            if patient.roi == "spinal_cord":
                roi_path = mesh_info[level_pair][visit_type]["roi"].get(level_pair)
                reader = vtk.vtkOBJReader()
                reader.SetFileName(roi_path)
                reader.Update()
                vtk_mesh = reader.GetOutput()

                vertices = np.array(vtk_mesh.GetPoints().GetData())
                triangles = np.array(vtk_mesh.GetPolys().GetData()).reshape(-1, 4)[:, 1:]

                prep[visit_type]["roi_path"] = roi_path
                prep[visit_type]["vertices"] = vertices
                prep[visit_type]["triangles"] = triangles

                if visit_type == "POST":
                    mesh = o3d.geometry.TriangleMesh()
                    mesh.vertices = o3d.utility.Vector3dVector(vertices)
                    mesh.triangles = o3d.utility.Vector3iVector(triangles)
                    save_path = os.path.join(registration_dir, f"{level_pair}_POST_registered.obj")
                    o3d.io.write_triangle_mesh(save_path, mesh)

            elif patient.roi == "iliopsoas":
                for side, name in [("left", "Iliopsoas_Left"), ("right", "Iliopsoas_Right")]:
                    mesh_dir = os.path.join(visit_output, f"Mesh_{level_pair}")
                    files = [f for f in os.listdir(mesh_dir) if f.startswith(name)]

                    if not files:
                        print(f"❌ No {name} mesh found for {visit_type} in {level_pair}")
                        continue

                    roi_path = os.path.join(mesh_dir, files[0])
                    reader = vtk.vtkOBJReader()
                    reader.SetFileName(roi_path)
                    reader.Update()
                    vtk_mesh = reader.GetOutput()

                    vertices = np.array(vtk_mesh.GetPoints().GetData())
                    triangles = np.array(vtk_mesh.GetPolys().GetData()).reshape(-1, 4)[:, 1:]

                    prep[visit_type][f"iliopsoas_{side}"] = {
                        "roi_path": roi_path,
                        "vertices": vertices,
                        "triangles": triangles
                    }

        # Step 3: Run the registration method
        if patient.roi == "spinal_cord":
            spinal_cord_registration(prep, level_pair, registration_dir)
        elif patient.roi == "iliopsoas":
            iliopsoas_registration(prep, level_pair, registration_dir)
        else:
            print(f"⚠️ No registration function implemented for ROI: {patient.roi}")
        
        # Step 4: Log
        if os.path.exists(registration_dir):
            reg_paths.append(registration_dir)

    patient.log_registration(reg_paths)
