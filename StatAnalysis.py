import os
import numpy as np
import json
import matplotlib.pyplot as plt
from scipy import stats
from Prep_and_Tools.results_structure import save_spinal_cord_global_excel, save_comparison_figures, save_psoas_global_excel, save_psoas_figures, create_analysis_results_excel

def global_spinal_cord_process(patients, main_output_path, case1, case2, excel_path):

    areas_data, perims_data, area_fig, perim_fig = general_spinal_cord_morphology_analysis(patients, main_output_path, case1, case2)

    # Preview results in console
    if areas_data and perims_data:
        print(f"\n📊 {case1} vs {case2} — AREA increase:")
        print(f"  {case1}: {areas_data[case1]['global_mean']:.2f} ± {areas_data[case1]['global_std']:.2f}")
        print(f"  {case2}: {areas_data[case2]['global_mean']:.2f} ± {areas_data[case2]['global_std']:.2f}")
        print(f"\n📊 {case1} vs {case2} — PERIMETER increase:")
        print(f"  {case1}: {perims_data[case1]['global_mean']:.2f} ± {perims_data[case1]['global_std']:.2f}")
        print(f"  {case2}: {perims_data[case2]['global_mean']:.2f} ± {perims_data[case2]['global_std']:.2f}")
        # Save to Excel
        if excel_path is None:
            excel_path = create_analysis_results_excel(main_output_path)

        save_spinal_cord_global_excel( areas_data, perims_data, excel_path, case1, case2 )

        # Save figures
        save_comparison_figures(area_fig, perim_fig, main_output_path, case1, case2)

def global_psoas_atrophy_process(patients, main_output_path, excel_path):
    stats_dict, figures_dict = general_psoas_atrophy_analysis(patients, main_output_path)

    intervened_data = stats_dict.get("intervened", {})
    control_data = stats_dict.get("control", {})
    diff_data = stats_dict.get("diff", {})
    cliffs_delta = stats_dict.get("cliffs_delta", np.nan)

    # Preview results in console
    print("\n📊 Psoas Atrophy Analysis Results:")
    print(f"  Intervened Group: {intervened_data.get('median', np.nan):.2f} ± {intervened_data.get('iqr', np.nan):.2f} (IQR)")
    print(f"  Control Group:    {control_data.get('median', np.nan):.2f} ± {control_data.get('iqr', np.nan):.2f} (IQR)")
    print(f"  Mean Difference (I - C): {diff_data.get('global_mean', np.nan):.2f} ± {diff_data.get('global_std', np.nan):.2f}")
    print(f"  Cliff’s Delta: {cliffs_delta:.3f}")

    # Save to Excel
    if excel_path is None:
        excel_path = create_analysis_results_excel(main_output_path)

    save_psoas_global_excel(stats_dict, excel_path)

    # Save figures
    save_psoas_figures(figures_dict, main_output_path)

def general_spinal_cord_morphology_analysis(patients, output_path, case1, case2, interp_length=350):
    """
    Executes a global morphology comparison (area and perimeter increases)
    between two case types (e.g., XLIF vs ALIF), using per-level patient data.

    Parameters
    ----------
    patients : list of Patient
        Patients that have completed shape analysis and have analysis_paths.
    interp_length : int
        Number of interpolated points per shape profile (e.g., 350).
    output_path : str
        Directory where comparison plots will be saved.
    case1 : str
        First surgical case type to compare (e.g., "XLIF").
    case2 : str
        Second surgical case type to compare (e.g., "ALIF").
    """

    def get_analysis_paths_by_case(patients, case_type):
        """
        Returns list of (patient_id, stat_folder) for each level of each patient.
        """
        entries = []
        for p in patients:
            if p.case_type == case_type:
                for folder in getattr(p, "analysis_paths", []):
                    entries.append((p.patient_number, folder))
        return entries

    def collect_arrays(stats_list, keyword, interp_length):
        """
        Loads .npy arrays (e.g., Areas_increase) from folders in stats_list.
        """
        arrays = []
        for pid, folder in stats_list:
            npy_path = os.path.join(folder, f"Patient_{pid}_{keyword}.npy")
            if os.path.exists(npy_path):
                arr = np.load(npy_path)
                if arr.shape[0] == interp_length:
                    arrays.append(arr)
        return np.array(arrays)

    # ⬇️ Build groups
    case1_stats = get_analysis_paths_by_case(patients, case1)
    case2_stats = get_analysis_paths_by_case(patients, case2)

    if len(case1_stats) < 2 or len(case2_stats) < 2:
        print(f"⚠️ Not enough data: {case1} has {len(case1_stats)} cases, {case2} has {len(case2_stats)} cases.")
        return None, None, None, None

    # ⬇️ Load shape metrics for both groups
    case1_areas = collect_arrays(case1_stats, "Areas_increase", interp_length)
    case2_areas = collect_arrays(case2_stats, "Areas_increase", interp_length)
    case1_perims = collect_arrays(case1_stats, "Perimeters_increase", interp_length)
    case2_perims = collect_arrays(case2_stats, "Perimeters_increase", interp_length)

    # ⬇️ Run statistical and visual comparison
    areas_data, area_plot_path = global_shape_statistics(
        case1_areas, case2_areas, interp_length, output_path,
        label="Areas", case1=case1, case2=case2
    )

    perims_data, perim_plot_path = global_shape_statistics(
        case1_perims, case2_perims, interp_length, output_path,
        label="Perimeters", case1=case1, case2=case2
    )

    return areas_data, perims_data, area_plot_path, perim_plot_path

def global_shape_statistics(group1_arrays, group2_arrays, stats_length, output_path, label, case1, case2):
    """
    Performs group-wise statistical shape comparison (mean ± std) between two case types.

    Parameters
    ----------
    group1_arrays : np.ndarray of shape [N, stats_length]
        All `*_increase.npy` arrays for group 1 (e.g., XLIF)
    group2_arrays : np.ndarray of shape [M, stats_length]
        All `*_increase.npy` arrays for group 2 (e.g., ALIF)
    stats_length : int
        Number of interpolated points along the spine (e.g., 350)
    output_path : str
        Directory where the plot will be saved
    label : str
        Metric name ("Areas" or "Perimeters")
    case1 : str
        Label for group 1 (e.g., "XLIF")
    case2 : str
        Label for group 2 (e.g., "ALIF")

    Returns
    -------
    dict
        Dictionary with mean and std arrays for both groups
    str
        Path to the saved comparison plot
    """
    import os
    import numpy as np
    import matplotlib.pyplot as plt

    def calc_mean_std(arrays):
        mean = np.mean(arrays, axis=0)
        std = np.std(arrays, axis=0)
        return mean, std

    # Compute stats
    mean1, std1 = calc_mean_std(group1_arrays)
    mean2, std2 = calc_mean_std(group2_arrays)

    # Global averages
    global_mean1 = np.mean(mean1)
    global_std1 = np.std(mean1)
    global_mean2 = np.mean(mean2)
    global_std2 = np.std(mean2)

    # Create plot
    x = np.linspace(0, 100, stats_length)
    plt.figure(figsize=(10, 6))

    plt.plot(x, mean1, label=f'{case1} Mean', color='green')
    plt.fill_between(x, mean1 - std1, mean1 + std1, color='lightgreen', alpha=0.4)

    plt.plot(x, mean2, label=f'{case2} Mean', color='orange')
    plt.fill_between(x, mean2 - std2, mean2 + std2, color='moccasin', alpha=0.4)

    plt.xlabel("Spinal cord height from top (0%) to bottom (100%) [%]")
    plt.ylabel(f"{label} Increase [%]")
    plt.title(
        f"{case1} vs {case2} — {label} Increase\n"
        f"{case1}: {global_mean1:.2f} ± {global_std1:.2f}  |  "
        f"{case2}: {global_mean2:.2f} ± {global_std2:.2f}"
    )
    plt.legend()
    plt.tight_layout()

    # Save figure
    filename = f"{case1}_vs_{case2}_{label}_comparison.png"
    plot_path = os.path.join(output_path, filename)
    os.makedirs(output_path, exist_ok=True)
    plt.savefig(plot_path)
    plt.close()

    # Return results
    stats_dict = {
        case1: {"mean": mean1, "std": std1, "global_mean": global_mean1, "global_std": global_std1},
        case2: {"mean": mean2, "std": std2, "global_mean": global_mean2, "global_std": global_std2},
    }

    return stats_dict, plot_path

def general_psoas_atrophy_analysis(patients, main_output_path):
    intervened_increments = []
    control_increments = []
    diff_values = []

    for patient in patients:
        analysis_folder = os.path.join(patient.output_path, "Stat Analysis Psoas")
        if not os.path.exists(analysis_folder):
            print(f"⚠️ Skipping Patient {patient.patient_number} — analysis folder missing.")
            continue

        patient_intervened = {}
        patient_control = {}

        for file in os.listdir(analysis_folder):
            if not file.endswith(".json"):
                continue

            try:
                path = os.path.join(analysis_folder, file)
                with open(path, 'r') as f:
                    data = json.load(f)

                increment = data.get("INCREMENT", None)
                if increment is None or isinstance(increment, str) or not np.isfinite(increment):
                    print(f"⚠️ Skipping file with invalid INCREMENT: {file}")
                    continue

                level = data.get("LEVEL")
                if "Intervened" in file:
                    intervened_increments.append(increment)
                    patient_intervened[level] = increment
                elif "Control" in file:
                    control_increments.append(increment)
                    patient_control[level] = increment

            except Exception as e:
                print(f"❌ Error reading {file}: {e}")

        # Pairwise difference calculation (per level)
        for level in patient_intervened:
            if level in patient_control:
                diff = patient_intervened[level] - patient_control[level]
                if np.isfinite(diff):
                    diff_values.append(diff)

    # ==== Statistics ====
    intervened_stats = compute_stats(intervened_increments)
    control_stats = compute_stats(control_increments)
    diff_stats = compute_stats(diff_values)

    # ==== Cliff's Delta ====
    cliffs_delta_val = cliffs_delta(intervened_increments, control_increments)

    # ==== Plots ====
    fig1 = plot_histogram(intervened_increments, "Intervened Psoas Increment", "blue")
    fig2 = plot_histogram(control_increments, "Control Psoas Increment", "green")
    fig3 = plot_histogram(diff_values, "Difference (Intervened - Control)", "red")
    fig_box = plot_boxplot(intervened_increments, control_increments)

    # ==== Return ====
    stats_dict = {
        "intervened": intervened_stats,
        "control": control_stats,
        "diff": {**diff_stats, "type": "I - C"},
        "cliffs_delta": cliffs_delta_val
    }

    figures_dict = {
        "hist_intervened": fig1,
        "hist_control": fig2,
        "hist_diff": fig3,
        "boxplot": fig_box
    }

    return stats_dict, figures_dict


def compute_stats(values):
    values = np.array(values)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return {
            "global_mean": np.nan,
            "global_std": np.nan,
            "median": np.nan,
            "iqr": np.nan,
            "n": 0
        }
    return {
        "global_mean": np.mean(values),
        "global_std": np.std(values),
        "median": np.median(values),
        "iqr": stats.iqr(values),
        "n": len(values)
    }


def cliffs_delta(a, b):
    a, b = np.array(a), np.array(b)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if len(a) == 0 or len(b) == 0:
        return np.nan
    total = len(a) * len(b)
    more = sum(ai > bj for ai in a for bj in b)
    less = sum(ai < bj for ai in a for bj in b)
    return (more - less) / total


def plot_histogram(data, title, color):
    data = np.array(data)
    data = data[np.isfinite(data)]

    fig, ax = plt.subplots(figsize=(6, 4))

    # Define bins every 5%
    bin_width = 5
    min_edge = np.floor(min(data) / bin_width) * bin_width
    max_edge = np.ceil(max(data) / bin_width) * bin_width
    bins = np.arange(min_edge, max_edge + bin_width, bin_width)

    ax.hist(data, bins=bins, color=color, alpha=0.8, edgecolor='black')

    ax.set_title(title)
    ax.set_xlabel("Volume Change (%)")
    ax.set_ylabel("Frequency")

    # Display n
    ax.text(0.98, 0.95, f"n = {len(data)}", ha='right', va='top',
            transform=ax.transAxes, fontsize=10,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.6))

    fig.tight_layout()
    return fig


def plot_boxplot(intervened, control):
    fig, ax = plt.subplots()
    ax.boxplot([intervened, control], labels=["Intervened", "Control"])
    ax.set_title("Psoas Increment — Intervened vs Control")
    ax.set_ylabel("Volume Change (%)")
    return fig
