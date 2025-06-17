import os
from segmentation import SEGMENTATION_TOOLS

def select_main_directory(default=None):
    default = default or os.path.expanduser("~/Desktop")
    print(f"\n📂 Default main directory: {default}")
    custom = input("Would you like to use a different directory? (y/n): ").strip().lower()
    if custom == 'y':
        new_path = input("Enter full path: ").strip()
        return new_path if os.path.exists(new_path) else default
    return default

def select_slicer_path(default_path=r"C:\Users\Usuario\AppData\Local\slicer.org\Slicer 5.6.0\Slicer.exe"):
    """
    Prompts user to enter the path to the Slicer executable.
    If no input is provided, the default path is used.
    Returns the validated path.
    """
    print("\n🧪 Slicer Executable Setup")
    print(f"Default path: {default_path}")
    path = input("Enter full path to Slicer executable [press Enter to use default]: ").strip()
    
    if not path:
        path = default_path

    if not os.path.exists(path):
        print(f"❌ Provided path does not exist: {path}")
        return select_slicer_path(default_path)  # retry

    print(f"✅ Using Slicer path: {path}")
    return path



def get_user_selection(options, prompt="Choose:", multi=True):
    print(prompt)
    for idx, opt in enumerate(options, 1):
        print(f"  {idx}. {opt}")

    while True:
        choice = input("Enter number(s): ").strip()
        try:
            indices = [int(i.strip()) for i in choice.split(',')]
            selected = [options[i-1] for i in indices]
            if not multi:
                return selected[0]
            return selected
        except (ValueError, IndexError):
            print("❌ Invalid input. Try again.")

def select_series(series_list):
    while True:
        try:
            choice = int(input("Enter number of series to use: "))
            if 1 <= choice <= len(series_list):
                return series_list[choice - 1]
        except ValueError:
            pass
        print("Invalid selection. Try again.")

def get_segmentation_config(patient_id):
    """
    Retrieves segmentation configuration for a patient.
    If a previous configuration exists, it offers the option to reuse it.
    Otherwise, prompts the user to select segmentation options.
    Returns the configuration as a dictionary.
    """

    print(f"\n🛠️  Segmentation setup for Patient {patient_id}")
    tool = get_user_selection(list(SEGMENTATION_TOOLS.keys()), "Choose segmentation tool:")[0]
    modality = get_user_selection(["ct", "mr"], "Select imaging modality:")[0]
    roi = get_user_selection(SEGMENTATION_TOOLS[tool][modality]["roi_options"], "Select ROI:")[0]
    other_raw = get_user_selection(SEGMENTATION_TOOLS[tool][modality]["other_options"], "Select additional regions (other):")
    other = [] if "none" in other_raw else other_raw
    fast = input("⚡ Run segmentation in fast mode? [y/N]: ").strip().lower() == 'y'

    segmentation_config = {
        "tool": tool,
        "roi": roi,
        "other": other,
        "modality": modality,
        "fast": fast   # 👈 store this choice
    }
    return segmentation_config