import matplotlib.pyplot as plt
import numpy as np

from research_simulation import (
    OUTPUT_DIR,
    ResearchConfig,
    paired_sweep,
    sweep,
    write_csv,
)


DEFAULT_TRIALS = 50


def _ensure_output_dir():
    OUTPUT_DIR.mkdir(exist_ok=True)


def _split_rows(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row["experiment"], []).append(row)
    return groups


def _nice_upper_limit(value):
    if value <= 1:
        return 1
    if value <= 5:
        step = 1
    elif value <= 20:
        step = 5
    elif value <= 60:
        step = 10
    else:
        step = 20
    return np.ceil(value / step) * step


def _plot_metric(
    rows,
    x_label,
    y_label,
    title,
    filename,
    metric,
    scale=1.0,
    threshold=None,
    error_bounds=None,
    y_limits=None,
):
    _ensure_output_dir()
    fig, ax = plt.subplots(figsize=(7.0, 4.8), dpi=160)
    visible_values = []

    for label, group in _split_rows(rows).items():
        group = sorted(group, key=lambda item: item["value"])
        x = [row["value"] for row in group]
        y = [row[f"{metric}_mean"] * scale for row in group]
        err = [row[f"{metric}_std"] * scale for row in group]

        if error_bounds is None:
            yerr = err
            visible_values.extend([value + error for value, error in zip(y, err)])
            visible_values.extend([value - error for value, error in zip(y, err)])
        else:
            lower_bound, upper_bound = error_bounds
            lower_err = [min(error, max(0.0, value - lower_bound)) for value, error in zip(y, err)]
            upper_err = [min(error, max(0.0, upper_bound - value)) for value, error in zip(y, err)]
            yerr = [lower_err, upper_err]
            visible_values.extend([value + error for value, error in zip(y, upper_err)])
            visible_values.extend([value - error for value, error in zip(y, lower_err)])

        ax.errorbar(x, y, yerr=yerr, marker="o", linewidth=1.6, capsize=3, label=label)

    if threshold is not None:
        ax.axhline(threshold, color="black", linestyle="--", linewidth=1.1, label="11% threshold")
        visible_values.append(threshold)

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, linestyle=":", alpha=0.45)
    ax.legend(fontsize=8)

    if y_limits is not None:
        ax.set_ylim(y_limits)
    elif visible_values:
        data_min = min(visible_values)
        data_max = max(visible_values)
        if error_bounds is not None and error_bounds[0] == 0 and data_min >= 0:
            lower_limit = -0.05 * max(1, data_max)
        else:
            lower_limit = data_min - abs(data_min) * 0.08
        upper_limit = _nice_upper_limit(data_max * 1.08)
        if error_bounds is not None:
            lower_limit = max(error_bounds[0] - 0.05 * (error_bounds[1] - error_bounds[0]), lower_limit)
            if data_max >= error_bounds[1] * 0.92:
                upper_limit = error_bounds[1] + 0.05 * (error_bounds[1] - error_bounds[0])
        ax.set_ylim(lower_limit, upper_limit)

    fig.tight_layout()
    path = OUTPUT_DIR / filename
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_detection_decomposition(rows, filename):
    _ensure_output_dir()
    fig, ax = plt.subplots(figsize=(7.0, 4.8), dpi=160)

    for label, group in _split_rows(rows).items():
        group = sorted(group, key=lambda item: item["value"])
        x = [row["value"] for row in group]
        timing = [row["timing_capture_rate_mean"] * 100 for row in group]
        detected = [row["detection_rate_mean"] * 100 for row in group]
        ax.plot(x, timing, marker="o", linewidth=1.7, label=f"{label}: timing capture")
        ax.plot(x, detected, marker="s", linewidth=1.4, linestyle="--", label=f"{label}: after loss")

    ax.set_xlabel("Detector window size (ns)")
    ax.set_ylabel("Rate (%)")
    ax.set_title("Timing capture versus end-to-end detection")
    ax.grid(True, linestyle=":", alpha=0.45)
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = OUTPUT_DIR / filename
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_noise_vs_qber(num_qubits=2048, trials=DEFAULT_TRIALS):
    base = ResearchConfig(num_qubits=num_qubits, eve_rate=0.0, use_qcs=True)
    no_eve = sweep("noise_rate", np.linspace(0.0, 0.20, 9), base, trials, "No Eve")
    eve_base = ResearchConfig(num_qubits=num_qubits, eve_rate=0.2, use_qcs=True)
    with_eve = sweep("noise_rate", np.linspace(0.0, 0.20, 9), eve_base, trials, "20% Eve")
    rows = no_eve + with_eve
    write_csv(rows, "noise_vs_qber.csv")
    return _plot_metric(
        rows,
        "Channel noise probability",
        "QBER (%)",
        "Noise sensitivity of BB84-QCS under partial interception",
        "noise_vs_qber.png",
        "qber",
        scale=100,
        threshold=11,
        error_bounds=(0, 100),
    )


def plot_attack_vs_qber(num_qubits=2048, trials=DEFAULT_TRIALS):
    ideal = ResearchConfig(num_qubits=num_qubits, noise_rate=0.0, use_qcs=True)
    noisy = ResearchConfig(num_qubits=num_qubits, noise_rate=0.03, use_qcs=True)
    values = np.linspace(0.0, 1.0, 11)
    rows = sweep("eve_rate", values, ideal, trials, "Ideal channel")
    rows += sweep("eve_rate", values, noisy, trials, "3% noisy channel")
    write_csv(rows, "attack_vs_qber.csv")
    return _plot_metric(
        rows,
        "Eve interception probability",
        "QBER (%)",
        "Intercept-resend attack strength versus QBER",
        "attack_vs_qber.png",
        "qber",
        scale=100,
        threshold=11,
        error_bounds=(0, 100),
    )


def plot_detection_window_comparison(num_qubits=2048, trials=DEFAULT_TRIALS):
    base = ResearchConfig(num_qubits=num_qubits)
    rows = paired_sweep("detector_window_ns", [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0], base, trials)
    write_csv(rows, "detector_window_vs_timing_capture.csv")
    return _plot_metric(
        rows,
        "Detector window size (ns)",
        "Timing-window capture rate (%)",
        "QCS aligns photon arrivals with narrow detector gates",
        "detector_window_vs_timing_capture.png",
        "timing_capture_rate",
        scale=100,
        error_bounds=(0, 100),
    )


def plot_detection_decomposition(num_qubits=2048, trials=DEFAULT_TRIALS):
    base = ResearchConfig(num_qubits=num_qubits)
    rows = paired_sweep("detector_window_ns", [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0], base, trials)
    write_csv(rows, "detector_window_timing_vs_end_to_end.csv")
    return _plot_detection_decomposition(rows, "detector_window_timing_vs_end_to_end.png")


def plot_clock_offset_vs_detection(num_qubits=2048, trials=DEFAULT_TRIALS):
    base = ResearchConfig(num_qubits=num_qubits, detector_window_ns=2.0)
    rows = paired_sweep("clock_offset_ns", np.linspace(0.0, 8.0, 9), base, trials)
    write_csv(rows, "clock_offset_vs_timing_capture.csv")
    return _plot_metric(
        rows,
        "Clock offset (ns)",
        "Timing-window capture rate (%)",
        "QCS maintains detector-gate alignment under clock offset",
        "clock_offset_vs_timing_capture.png",
        "timing_capture_rate",
        scale=100,
        error_bounds=(0, 100),
    )


def plot_clock_drift_vs_detection(num_qubits=2048, trials=DEFAULT_TRIALS):
    base = ResearchConfig(num_qubits=num_qubits, detector_window_ns=2.0)
    rows = paired_sweep("clock_drift_ppm", [0, 10, 25, 50, 75, 100, 150, 200], base, trials)
    write_csv(rows, "clock_drift_vs_timing_capture.csv")
    return _plot_metric(
        rows,
        "Clock drift (ppm)",
        "Timing-window capture rate (%)",
        "QCS compensates clock-frequency drift during key exchange",
        "clock_drift_vs_timing_capture.png",
        "timing_capture_rate",
        scale=100,
        error_bounds=(0, 100),
    )


def plot_timing_jitter_vs_detection(num_qubits=2048, trials=DEFAULT_TRIALS):
    base = ResearchConfig(num_qubits=num_qubits, detector_window_ns=2.0)
    rows = paired_sweep("timing_jitter_ns", [0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5], base, trials)
    write_csv(rows, "timing_jitter_vs_timing_capture.csv")
    return _plot_metric(
        rows,
        "Timing jitter standard deviation (ns)",
        "Timing-window capture rate (%)",
        "QCS timing capture under increasing arrival-time jitter",
        "timing_jitter_vs_timing_capture.png",
        "timing_capture_rate",
        scale=100,
        error_bounds=(0, 100),
    )


def plot_raw_qubits_vs_final_key(num_qubits=None, trials=DEFAULT_TRIALS):
    base = ResearchConfig(noise_rate=0.03, eve_rate=0.1, detector_window_ns=2.0)
    rows = paired_sweep("num_qubits", [256, 512, 1024, 2048, 4096, 8192], base, trials)
    write_csv(rows, "raw_qubits_vs_final_key.csv")
    return _plot_metric(
        rows,
        "Raw transmitted qubits",
        "Final key length (bits)",
        "Final secure key length after reconciliation and privacy amplification",
        "raw_qubits_vs_final_key.png",
        "final_key_bits",
        error_bounds=(0, 256),
    )


def plot_sifted_key_rate(num_qubits=2048, trials=DEFAULT_TRIALS):
    base = ResearchConfig(num_qubits=num_qubits, noise_rate=0.03, use_qcs=True)
    rows = sweep("eve_rate", np.linspace(0.0, 0.6, 7), base, trials, "BB84-QCS")
    write_csv(rows, "eve_vs_sifted_key_rate.csv")
    return _plot_metric(
        rows,
        "Eve interception probability",
        "Sifted key rate (%)",
        "Sifted key availability under partial interception",
        "eve_vs_sifted_key_rate.png",
        "sifted_key_rate",
        scale=100,
        error_bounds=(0, 100),
    )


def plot_acceptance_probability(num_qubits=2048, trials=DEFAULT_TRIALS):
    base = ResearchConfig(num_qubits=num_qubits, use_qcs=True)
    rows = sweep("eve_rate", np.linspace(0.0, 0.8, 9), base, trials, "Acceptance probability")
    write_csv(rows, "eve_vs_acceptance_probability.csv")
    return _plot_metric(
        rows,
        "Eve interception probability",
        "Accepted trials (%)",
        "Security decision probability using the 11% QBER threshold",
        "eve_vs_acceptance_probability.png",
        "accepted",
        scale=100,
        error_bounds=(0, 100),
    )


def plot_distance_vs_secret_key_rate(num_qubits=4096, trials=DEFAULT_TRIALS):
    base = ResearchConfig(num_qubits=num_qubits, noise_rate=0.03, eve_rate=0.1, use_qcs=True)
    rows = sweep("distance_km", [0, 5, 10, 15, 20, 30, 40, 50], base, trials, "BB84-QCS")
    write_csv(rows, "distance_vs_secret_key_rate.csv")
    return _plot_metric(
        rows,
        "Fiber distance (km)",
        "Final secret key rate (%)",
        "Distance-dependent key generation under channel attenuation",
        "distance_vs_secret_key_rate.png",
        "secret_key_rate",
        scale=100,
        error_bounds=(0, 100),
    )


def plot_privacy_amplification_budget(num_qubits=2048, trials=DEFAULT_TRIALS):
    base = ResearchConfig(num_qubits=num_qubits, noise_rate=0.03, use_qcs=True)
    rows = sweep("eve_rate", np.linspace(0.0, 0.6, 7), base, trials, "After privacy amplification")
    write_csv(rows, "privacy_amplification_budget.csv")
    return _plot_metric(
        rows,
        "Eve interception probability",
        "Final key length (bits)",
        "Privacy amplification budget under increasing Eve information",
        "privacy_amplification_budget.png",
        "final_key_bits",
        error_bounds=(0, 256),
    )


def generate_publication_graphs(num_qubits=2048, trials=DEFAULT_TRIALS):
    print("=" * 72)
    print("  GENERATING PUBLICATION-GRADE BB84-QCS ANALYSIS")
    print("=" * 72)
    print(f"  Trials per point: {trials}")
    print(f"  Default raw qubits per trial: {num_qubits}")
    print(f"  Output directory: {OUTPUT_DIR}")

    graph_functions = [
        plot_noise_vs_qber,
        plot_attack_vs_qber,
        plot_detection_window_comparison,
        plot_detection_decomposition,
        plot_clock_offset_vs_detection,
        plot_clock_drift_vs_detection,
        plot_timing_jitter_vs_detection,
        plot_raw_qubits_vs_final_key,
        plot_sifted_key_rate,
        plot_acceptance_probability,
        plot_distance_vs_secret_key_rate,
        plot_privacy_amplification_budget,
    ]

    paths = []
    for function in graph_functions:
        print(f"  Running {function.__name__}...")
        paths.append(function(num_qubits=num_qubits, trials=trials))

    print()
    print("Generated graphs:")
    for path in paths:
        print(f"  {path}")
    print("CSV tables saved beside the figures.")
    return paths


if __name__ == "__main__":
    generate_publication_graphs()
