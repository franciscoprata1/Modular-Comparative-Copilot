import os
import shutil
import pandas as pd

def load_csv(path):
    """
    Loads a CSV or Excel file and returns a pandas DataFrame.
    """
    print(f"🔍 Loading file: {path}")
    return pd.read_csv(path) if path.endswith('.csv') else pd.read_excel(path)


def copy_csv(csv_path, output_folder):
    """
    General-purpose function to copy a CSV or Excel file to a target folder.

    Args:
        csv_path (str): Path to the source .csv or .xlsx file.
        output_folder (str): Destination folder where the file will be copied.

    Returns:
        str: Full path to the copied file.
    """
    os.makedirs(output_folder, exist_ok=True)
    filename = "COPY of " + os.path.basename(csv_path)
    destination = os.path.join(output_folder, filename)
    shutil.copy(csv_path, destination)
    print(f"📄 Copied file to: {destination}")
    return destination


def list_folder_contents(label, folder):
    print(f"  📂 {label} folder contents:")
    if os.path.exists(folder):
        contents = os.listdir(folder)
        if contents:
            for item in contents:
                print(f"    - {item}")
        else:
            print("    (empty)")
    else:
        print("    (folder missing)")