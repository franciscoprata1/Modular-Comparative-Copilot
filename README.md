# 🧠 Modular Comparative Imaging Pipeline

A modular, automated pipeline for the analysis of pre-operative and post-operative spinal medical images using segmentation, mesh extraction, and shape analysis. Designed for clinical research and surgical planning applications.

---

## 📌 What This Project Does

The tool currently includes the following core functionalities:
- Patient loading and configuration
- Pre/Post Image selection
- Segmentation of anatomical structures
- Mesh generation
- Image registration
- Region cropping
- Morphological and Shape analysis
- Batch processing and statistical analysis of multiple patients


---

## 🎯 Why This Project Is Useful

Spinal surgery planning requires detailed morphological comparisons. This pipeline:
- Saves clinicians and researchers time by automating repetitive steps
- Ensures consistent segmentation and mesh generation across multiple patients#
- Allows batch analysis of interventional effects (e.g., decompression volume change)
- Enables statistical comparisons between surgical techniques or cases
- Is designed to allow new modules and functionalities

---

## 🚀 Getting Started

To keep dependencies isolated, it is recommended to create a virtual environment for this tool:

### 🔧 Step 1: Create and Activate Environment

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
```

### 📦 Step 2: Install Dependencies
```bash
pip install TotalSegmentator
pip install -r requirements.txt
```

### 🖥️ Step 3: Setup Interface with PyInstaller
```bash
pip install pyinstaller
pyinstaller --onefile gui_main.py
dist/gui_main.exe
```

### 📄 Full Code Explanation
For a complete explanation of the code structure, logic, and design decisions, please refer to the thesis document included in this repository:
See: TFG_Francisco_Prata.pdf

---

## 📬 Contact
Maintainer: Francisco Prata
email: franciscoprata2002@gmail.com
