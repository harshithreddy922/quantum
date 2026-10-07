"""
Generate the publication figures and data tables for the QCS-assisted BB84
study. Every figure is written as PDF (vector, for the manuscript) and PNG
(300 dpi, for previews), with a CSV holding the plotted numbers.

    python generate_graphs.py                 # full run
    python generate_graphs.py --quick         # fewer trials, for drafts
    python generate_graphs.py --only fig05 fig08
"""

import argparse
import math
import os
import pickle
import time
from dataclasses import replace

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.ticker import NullFormatter
from scipy.special import erf

import research_simulation as rs
from bb84.qcs_tracking import cramer_rao_endpoint_sigma
from bb84.security import (
    EPS_COR,
    EPS_SEC,
    QBER_TOLERANCE,
    binary_entropy,
    plob_bound,
    statistical_fluctuation,
)
from bb84.timing_attacks import eve_information, variance_monitor_power
from research_simulation import OUTPUT_DIR, ResearchConfig, write_csv


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#d9d8d4"
NEUTRAL = "#8a8985"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]   # blue, orange, aqua, yellow

STRATEGY_STYLE = {
    "none": dict(color=NEUTRAL, marker="x", linestyle=":"),
    "classical": dict(color=SERIES[1], marker="s", linestyle="-"),
    "qcs_preamble": dict(color=SERIES[2], marker="^", linestyle="-"),
    "qcs_tracking": dict(color=SERIES[0], marker="o", linestyle="-"),
    "ideal": dict(color=INK, marker=None, linestyle="--"),
}
SERIES_MARKERS = ["o", "s", "^", "D"]

BLUES = LinearSegmentedColormap.from_list(
    "seq_blue", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)

plt.rcParams.update({
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "legend.fontsize": 7,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "axes.edgecolor": INK_2,
    "axes.labelcolor": INK,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.5,
    "lines.linewidth": 1.6,
    "lines.markersize": 4.5,
    "legend.frameon": False,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
})

DOUBLE_COLUMN = 7.0
SINGLE_COLUMN = 3.4


class Context:
    def __init__(self, quick=False):
        self.quick = quick

    def trials(self, n):
        return max(3, n // 5) if self.quick else n

    def slots(self, n):
        """Block size; quick mode caps very large blocks."""
        return min(n, 10 ** 7) if self.quick else n


def new_figure(ncols, width=DOUBLE_COLUMN, height=3.1, nrows=1):
    fig, axes = plt.subplots(nrows, ncols, figsize=(width, height), constrained_layout=True)
    return fig, np.atleast_1d(axes).ravel()


def panel_label(ax, letter):
    ax.text(-0.02, 1.04, f"({letter})", transform=ax.transAxes, fontweight="bold",
            ha="right", va="bottom", color=INK)


PANEL_DIR = OUTPUT_DIR / "panels"
PANEL_SIZE = (3.6, 3.3)


def shared_legend(fig, ax, ncol=3):
    """One legend for all panels, in a row above them (never over data)."""
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=ncol, borderaxespad=0.2)


def below_legend(ax, ncol=1, **kwargs):
    """Legend for one panel, placed under its x-axis label."""
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=ncol, **kwargs)


def _export_panels(fig, name, panels):
    """
    Save every panel of a multi-panel figure as its own figure. The figure
    is copied, all other axes are removed, and the remaining axes is given
    the whole canvas plus its own legend underneath.
    """
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = pickle.dumps(fig)
    indices = [fig.axes.index(ax) for ax in panels]
    for letter, index in zip("abcdef", indices):
        copy = pickle.loads(snapshot)
        keep = copy.axes[index]
        for other in list(copy.axes):
            if other is not keep:
                copy.delaxes(other)
        for legend in list(copy.legends):
            legend.remove()
        keep.set_subplotspec(copy.add_gridspec(1, 1)[0])
        if keep.get_legend() is None:
            handles, labels = keep.get_legend_handles_labels()
            if handles:
                below_legend(keep, ncol=2)
        copy.set_size_inches(*PANEL_SIZE)
        copy.savefig(PANEL_DIR / f"{name}_{letter}.pdf")
        copy.savefig(PANEL_DIR / f"{name}_{letter}.png")
        plt.close(copy)


def save(fig, name, panels=None):
    """Save PDF + PNG; with panels, also save each panel on its own."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    if panels is not None and len(panels) > 1:
        _export_panels(fig, name, panels)
    fig.savefig(OUTPUT_DIR / f"{name}.pdf")
    fig.savefig(OUTPUT_DIR / f"{name}.png")
    plt.close(fig)
    return OUTPUT_DIR / f"{name}.png"


def series_rows(rows, series):
    return sorted((r for r in rows if r["series"] == series), key=lambda r: r["value"])


def plot_metric(ax, rows, series, metric, style, label, scale=1.0, x_scale=1.0, log_drop_zero=False):
    group = series_rows(rows, series)
    x = np.array([r["value"] for r in group], dtype=float) * x_scale
    y = np.array([r[f"{metric}_mean"] for r in group], dtype=float) * scale
    ci = np.array([r[f"{metric}_ci95"] for r in group], dtype=float) * scale
    if log_drop_zero:
        keep = y > 0
        x, y, ci = x[keep], y[keep], ci[keep]
        lower = np.minimum(ci, 0.95 * y)
    else:
        lower = np.minimum(ci, np.maximum(y, 0))   # all plotted metrics are non-negative
    ax.errorbar(x, y, yerr=[lower, ci], label=label, capsize=1.8, elinewidth=0.8,
                markeredgewidth=0.9, **style)


# ---------------------------------------------------------------------------
# Fig. 1 - system model
# ---------------------------------------------------------------------------

def _box(ax, x, y, w, h, title, lines, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                linewidth=1.0, edgecolor=color, facecolor="white"))
    ax.text(x + w / 2, y + h - 0.18, title, ha="center", va="top", fontweight="bold", color=INK)
    ax.text(x + w / 2, y + h - 0.52, "\n".join(lines), ha="center", va="top",
            color=INK_2, fontsize=6.6, linespacing=1.45)


def fig01_system_model(ctx):
    fig = plt.figure(figsize=(DOUBLE_COLUMN, 4.6), constrained_layout=True)
    grid = fig.add_gridspec(2, 1, height_ratios=[1.25, 1.0])
    ax = fig.add_subplot(grid[0])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.4)
    ax.axis("off")
    panel_label(ax, "a")

    _box(ax, 0.1, 1.15, 2.6, 2.1, "Alice", [
        "QRNG bits and bases", "BB84 polarization encoder",
        "clock: one pulse per 10 ns slot",
        "sync preamble + secret pilot slots",
    ], SERIES[0])
    _box(ax, 3.55, 1.15, 2.9, 2.1, "Quantum channel", [
        "fibre loss 0.2 dB/km", "Pauli noise (bit error 2p/3)",
        "arrival jitter, clock offset/drift",
        "Eve: intercept-resend, time shift",
    ], SERIES[1])
    _box(ax, 7.3, 1.15, 2.6, 2.1, "Bob", [
        "D0/D1 gated detectors (W ns)", "time tagger, dark counts",
        "QCS: drift-search acquisition", "+ Kalman pilot tracking",
    ], SERIES[0])
    for x0, x1 in ((2.7, 3.55), (6.45, 7.3)):
        ax.add_patch(FancyArrowPatch((x0, 2.2), (x1, 2.2), arrowstyle="-|>",
                                     mutation_scale=10, color=INK, linewidth=1.1))
    ax.add_patch(FancyArrowPatch((1.4, 1.0), (8.6, 1.0), arrowstyle="<|-|>",
                                 mutation_scale=9, color=NEUTRAL, linewidth=1.0, linestyle="--"))
    ax.text(5.0, 0.88, "authenticated classical channel", ha="center", va="top", color=INK_2, fontsize=7)
    ax.text(5.0, 0.55,
            "sifting  →  QBER test on random subset  →  error correction (f = 1.16)"
            "  →  privacy amplification (finite-key bound)",
            ha="center", va="top", color=INK_2, fontsize=6.6)

    ax = fig.add_subplot(grid[1])
    panel_label(ax, "b")
    period, offset, drift, jitter, window = 10.0, 3.0, 0.04, 0.35, 2.0
    slots = np.arange(6)
    rows = {"Alice emission": 3.0, "photon arrival": 2.0, "nominal gate": 1.0, "QCS gate": 0.0}
    for t in slots * period:
        ax.vlines(t, rows["Alice emission"] - 0.3, rows["Alice emission"] + 0.3, color=SERIES[0], linewidth=1.6)
        arrival = t + offset + drift * t
        xs = np.linspace(arrival - 1.5, arrival + 1.5, 60)
        ax.fill_between(xs, rows["photon arrival"] - 0.3,
                        rows["photon arrival"] - 0.3 + 0.6 * np.exp(-0.5 * ((xs - arrival) / jitter) ** 2),
                        color=SERIES[2], alpha=0.9, linewidth=0)
        ax.add_patch(Rectangle((t - window / 2, rows["nominal gate"] - 0.25), window, 0.5,
                               facecolor=NEUTRAL, edgecolor="none"))
        ax.add_patch(Rectangle((arrival - window / 2, rows["QCS gate"] - 0.25), window, 0.5,
                               facecolor=SERIES[0], edgecolor="none"))
    ax.set_yticks(list(rows.values()), list(rows.keys()))
    ax.set_ylim(-0.6, 3.6)
    ax.set_xlim(-3, 60)
    ax.set_xlabel("Time at Bob (ns); offset 3 ns, drift exaggerated to 4 % for visibility")
    ax.grid(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    return save(fig, "fig01_system_model")


# ---------------------------------------------------------------------------
# Fig. 2 - model validation
# ---------------------------------------------------------------------------

def fig02_model_validation(ctx):
    fig, axes = new_figure(3)
    base = ResearchConfig(sync_strategy="ideal", num_slots=10 ** 6, distance_km=25)
    csv_rows = []

    # (a) QBER: Monte Carlo against the closed form
    ax = axes[0]
    eve_values = np.linspace(0, 1, 11)
    specs = [("fig02a", "eve_rate", eve_values, replace(base, pauli_error_rate=p), ctx.trials(20), f"p={p}")
             for p in (0.0, 0.03, 0.09)]
    rows = rs.run_sweeps(specs)
    csv_rows += rows
    fine = np.linspace(0, 1, 101)
    for i, p in enumerate((0.0, 0.03, 0.09)):
        cfg = replace(base, pauli_error_rate=p)
        analytic = [rs.expected_qber(replace(cfg, eve_rate=e)) * 100 for e in fine]
        ax.plot(fine, analytic, color=SERIES[i], linewidth=1.0)
        plot_metric(ax, rows, f"p={p}", "qber", dict(color=SERIES[i], marker=SERIES_MARKERS[i], linestyle="none"),
                    f"p = {p:g}", scale=100)
    ax.set_xlabel("Eve interception fraction")
    ax.set_ylabel("QBER (%)")
    below_legend(ax, ncol=3, title="Pauli error p (markers: simulation, lines: theory)", title_fontsize=6.5)
    panel_label(ax, "a")

    # (b) detection probability versus gate width, including dark counts
    ax = axes[1]
    windows = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
    fine_w = np.linspace(0.2, 8.0, 200)
    for i, distance in enumerate((100, 150)):
        cfg = replace(base, distance_km=distance, num_slots=ctx.slots(10 ** 7))
        rows = rs.sweep("fig02b", "detector_window_ns", windows, cfg, ctx.trials(10), f"{distance} km")
        csv_rows += rows
        analytic = [rs.expected_detection_rate(
            replace(cfg, detector_window_ns=w), erf(w / 2 / (cfg.timing_jitter_ns * math.sqrt(2)))) * 1e3
            for w in fine_w]
        ax.plot(fine_w, analytic, color=SERIES[i], linewidth=1.0)
        plot_metric(ax, rows, f"{distance} km", "detection_rate",
                    dict(color=SERIES[i], marker=SERIES_MARKERS[i], linestyle="none"), f"{distance} km", scale=1e3)
    ax.set_xlabel("Detector gate width W (ns)")
    ax.set_ylabel("Click probability per slot (×10⁻³)")
    below_legend(ax, ncol=2, title="markers: simulation, lines: theory", title_fontsize=6.5)
    panel_label(ax, "b")

    # (c) acquisition accuracy against the Cramer-Rao bound
    ax = axes[2]
    targets = [4, 8, 16, 32, 64, 128, 256, 512]
    cfg = replace(base, sync_strategy="qcs_preamble", num_slots=10 ** 6, freq_wander_ppm_per_sqrt_ms=0.0)
    measured, detections = [], []
    for target in targets:
        rng = rs.make_rng("fig02c", target)
        c = replace(cfg, preamble_target_detections=target)
        errors, counts = [], []
        for _ in range(ctx.trials(300)):
            gate_error, n_det, _, key_start = rs.synchronize(c, rng, None)
            errors.append(float(gate_error(np.array([key_start]))[0]))
            counts.append(n_det)
        measured.append(float(np.sqrt(np.mean(np.square(errors)))))
        detections.append(float(np.mean(counts)))
        csv_rows.append({"experiment": "fig02c", "series": "preamble", "parameter": "preamble_target_detections",
                         "value": target, "detections_mean": detections[-1], "endpoint_rms_error_ns": measured[-1],
                         "cramer_rao_ns": float(cramer_rao_endpoint_sigma(cfg.timing_jitter_ns, detections[-1]))})
    n_fine = np.logspace(np.log10(3), np.log10(600), 100)
    ax.plot(n_fine, cramer_rao_endpoint_sigma(cfg.timing_jitter_ns, n_fine) * 1e3, color=INK, linestyle="--",
            linewidth=1.0, label="Cramér–Rao bound")
    ax.plot(detections, np.array(measured) * 1e3, color=SERIES[0], marker="o", linestyle="none",
            label="QCS acquisition (simulated)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Detected preamble photons")
    ax.set_ylabel("Timing error at preamble end (ps, RMS)")
    below_legend(ax, ncol=1)
    panel_label(ax, "c")

    write_csv(csv_rows, "fig02_model_validation.csv")
    return save(fig, "fig02_model_validation", axes)


# ---------------------------------------------------------------------------
# Fig. 3 - QBER under noise and attack
# ---------------------------------------------------------------------------

def fig03_qber_security(ctx):
    fig, axes = new_figure(2, width=DOUBLE_COLUMN * 0.85)
    base = ResearchConfig(num_slots=10 ** 6)
    noise = np.linspace(0, 0.3, 11)
    rows_a = rs.run_sweeps([
        ("fig03a", "pauli_error_rate", noise, replace(base, eve_rate=e), ctx.trials(50), f"eve={e}")
        for e in (0.0, 0.2)
    ])
    eve = np.linspace(0, 1, 11)
    rows_b = rs.run_sweeps([
        ("fig03b", "eve_rate", eve, replace(base, pauli_error_rate=p), ctx.trials(50), f"p={p}")
        for p in (0.0, 0.03)
    ])
    for i, (e, label) in enumerate(((0.0, "No Eve"), (0.2, "Eve intercepts 20 %"))):
        plot_metric(axes[0], rows_a, f"eve={e}", "qber",
                    dict(color=SERIES[i], marker=SERIES_MARKERS[i], linestyle="-"), label, scale=100)
    for i, (p, label) in enumerate(((0.0, "Noiseless channel"), (0.03, "Pauli p = 0.03"))):
        plot_metric(axes[1], rows_b, f"p={p}", "qber",
                    dict(color=SERIES[i], marker=SERIES_MARKERS[i], linestyle="-"), label, scale=100)
    for ax, letter, xlabel in ((axes[0], "a", "Channel Pauli error probability p"),
                               (axes[1], "b", "Eve interception fraction")):
        ax.axhline(QBER_TOLERANCE * 100, color=INK_2, linestyle="--", linewidth=0.9)
        # Bottom-right of the threshold line is empty in both panels.
        ax.text(ax.get_xlim()[1] - 0.02 * np.ptp(ax.get_xlim()), QBER_TOLERANCE * 100 - 0.6,
                "11 % abort threshold", ha="right", va="top", color=INK_2, fontsize=6.5)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("QBER (%)")
        below_legend(ax, ncol=2)
        panel_label(ax, letter)
    write_csv(rows_a + rows_b, "fig03_qber_security.csv")
    return save(fig, "fig03_qber_security", axes)


# ---------------------------------------------------------------------------
# Fig. 4 - key acceptance and finite-size effects
# ---------------------------------------------------------------------------

def fig04_acceptance(ctx):
    fig, axes = new_figure(1, width=SINGLE_COLUMN + 0.4, height=3.3)
    ax = axes[0]
    base = ResearchConfig()
    eve = np.round(np.arange(0, 0.6001, 0.025), 3)
    sizes = [10 ** 5, 10 ** 6, 10 ** 7]
    rows = rs.run_sweeps([
        ("fig04", "eve_rate", eve, replace(base, num_slots=ctx.slots(n)), ctx.trials(200), f"N={n}")
        for n in sizes
    ])
    for i, n in enumerate(sizes):
        group = series_rows(rows, f"N={n}")
        x = [r["value"] for r in group]
        y = np.array([r["accepted_mean"] for r in group]) * 100
        lo = np.array([r["accepted_wilson_low"] for r in group]) * 100
        hi = np.array([r["accepted_wilson_high"] for r in group]) * 100
        ax.fill_between(x, lo, hi, color=SERIES[i], alpha=0.18, linewidth=0)
        ax.plot(x, y, color=SERIES[i], marker=SERIES_MARKERS[i], label=f"N = 10$^{int(math.log10(n))}$ slots")

    e_ch = 2 * base.pauli_error_rate / 3
    eve_at_threshold = 4 * (QBER_TOLERANCE - e_ch) / (1 - 2 * e_ch)
    ax.axvline(eve_at_threshold, color=INK_2, linestyle="--", linewidth=0.9)
    ax.text(eve_at_threshold + 0.01, 50, "QBER = 11 %\n(asymptotic)", color=INK_2, fontsize=6.5, va="center")
    ax.set_xlabel("Eve interception fraction")
    ax.set_ylabel("Blocks producing a key (%)")
    below_legend(ax, ncol=3, title="block size", title_fontsize=6.5)
    write_csv(rows, "fig04_acceptance.csv")
    return save(fig, "fig04_acceptance")


# ---------------------------------------------------------------------------
# Fig. 5 - timing impairments
# ---------------------------------------------------------------------------

def fig05_timing_impairments(ctx):
    fig, axes = new_figure(3)
    base = ResearchConfig(num_slots=10 ** 5)
    trials = ctx.trials(50)
    panels = [
        ("clock_offset_ns", np.arange(0, 20.01, 2.5), base, "Initial clock offset (ns)"),
        ("clock_drift_ppm", [0, 5, 10, 20, 50, 100, 150, 200],
         replace(base, clock_offset_ns=0.0, prior_drift_ppm=250.0), "Clock drift (ppm), offset = 0"),
        ("timing_jitter_ns", [0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5], base, "Arrival-time jitter σ (ns)"),
    ]
    all_rows = []
    for ax, letter, (parameter, values, cfg, xlabel) in zip(axes, "abc", panels):
        rows = rs.strategy_sweep(f"fig05_{parameter}", parameter, values, cfg, trials)
        all_rows += rows
        for strategy in rs.SYNC_STRATEGIES:
            plot_metric(ax, rows, strategy, "timing_capture_rate", STRATEGY_STYLE[strategy],
                        rs.STRATEGY_LABELS[strategy], scale=100)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Timing capture (%)")
        ax.set_ylim(-4, 104)
        panel_label(ax, letter)
    shared_legend(fig, axes[0])
    write_csv(all_rows, "fig05_timing_impairments.csv")
    return save(fig, "fig05_timing_impairments", axes)


# ---------------------------------------------------------------------------
# Fig. 6 - gate-width trade-off
# ---------------------------------------------------------------------------

def fig06_window_tradeoff(ctx):
    fig, axes = new_figure(3)
    base = ResearchConfig(distance_km=125, num_slots=ctx.slots(10 ** 8))
    windows = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
    strategies = ("classical", "qcs_preamble", "qcs_tracking", "ideal")
    rows = rs.strategy_sweep("fig06", "detector_window_ns", windows, base, ctx.trials(20), strategies)
    metrics = [("timing_capture_rate", 100, "Timing capture (%)"),
               ("qber", 100, "QBER (%)"),
               ("secret_key_rate", 1e4, "Secret key rate (10⁻⁴ bits/slot)")]
    for ax, letter, (metric, scale, ylabel) in zip(axes, "abc", metrics):
        for strategy in strategies:
            plot_metric(ax, rows, strategy, metric, STRATEGY_STYLE[strategy], rs.STRATEGY_LABELS[strategy], scale=scale)
        ax.set_xscale("log")
        ax.set_xticks(windows[::2], [f"{w:g}" for w in windows[::2]])
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xlabel("Detector gate width W (ns)")
        ax.set_ylabel(ylabel)
        panel_label(ax, letter)
    axes[1].axhline(QBER_TOLERANCE * 100, color=INK_2, linestyle="--", linewidth=0.9)
    shared_legend(fig, axes[0], ncol=4)
    write_csv(rows, "fig06_window_tradeoff.csv")
    return save(fig, "fig06_window_tradeoff", axes)


# ---------------------------------------------------------------------------
# Fig. 7 - synchronization overhead
# ---------------------------------------------------------------------------

def fig07_sync_overhead(ctx):
    fig, axes = new_figure(2, width=DOUBLE_COLUMN * 0.85)
    spacings = [1000, 300, 100, 30, 10]
    distances = (25, 75, 125)
    base = ResearchConfig(num_slots=ctx.slots(10 ** 8), freq_wander_ppm_per_sqrt_ms=0.1)
    rows = rs.run_sweeps([
        ("fig07", "pilot_spacing_slots", spacings, replace(base, distance_km=d), ctx.trials(8), f"{d} km")
        for d in distances
    ])
    for row in rows:
        row["pilot_overhead_pct"] = 100.0 / row["value"]
    for i, d in enumerate(distances):
        group = series_rows(rows, f"{d} km")
        x = [100.0 / r["value"] for r in group]
        style = dict(color=SERIES[i], marker=SERIES_MARKERS[i])
        y = np.array([r["sync_rms_error_ns_mean"] * 1e3 for r in group])
        ci = np.array([r["sync_rms_error_ns_ci95"] * 1e3 for r in group])
        axes[0].errorbar(x, y, yerr=[np.minimum(ci, 0.9 * y), ci], capsize=1.8,
                         elinewidth=0.8, label=f"{d} km", **style)
        ref = max(r["secret_key_rate_mean"] for r in group) or 1.0
        y = np.array([r["secret_key_rate_mean"] / ref for r in group])
        ci = np.array([r["secret_key_rate_ci95"] / ref for r in group])
        axes[1].errorbar(x, y, yerr=[np.minimum(ci, y), ci], capsize=1.8,
                         elinewidth=0.8, label=f"{d} km", **style)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Gate timing error (ps, RMS)")
    axes[1].set_ylabel("Secret key rate (normalized to best)")
    for ax, letter in zip(axes, "ab"):
        ax.set_xscale("log")
        ax.set_xlabel("Pilot overhead (% of slots)")
        panel_label(ax, letter)
    shared_legend(fig, axes[0])
    write_csv(rows, "fig07_sync_overhead.csv")
    return save(fig, "fig07_sync_overhead", axes)


# ---------------------------------------------------------------------------
# Fig. 8 - distance
# ---------------------------------------------------------------------------

def fig08_distance(ctx):
    fig, axes = new_figure(1, width=SINGLE_COLUMN + 0.9, height=4.0)
    ax = axes[0]
    base = ResearchConfig(num_slots=ctx.slots(10 ** 8))
    distances = [0, 10, 25, 50, 75, 100, 125, 150, 175, 200]
    strategies = ("classical", "qcs_preamble", "qcs_tracking", "ideal")
    rows = rs.strategy_sweep("fig08", "distance_km", distances, base, ctx.trials(10), strategies)

    fine = np.linspace(0, 220, 221)
    plob = [plob_bound(rs.channel_transmittance(replace(base, distance_km=d))) for d in fine]
    asym = [rs.expected_asymptotic_rate(replace(base, distance_km=d),
                                        erf(base.detector_window_ns / 2 / (base.timing_jitter_ns * math.sqrt(2))))
            for d in fine]
    ax.plot(fine, plob, color=NEUTRAL, linestyle="-.", linewidth=1.0, label="PLOB bound")
    asym = np.array(asym)
    ax.plot(fine[asym > 0], asym[asym > 0], color=INK_2, linestyle=":", linewidth=1.1,
            label="Asymptotic, perfect sync")
    # Preamble-only QCS loses lock within a 1 s block (see table_operating_points);
    # it is simulated for the table but not drawn.
    for strategy in ("classical", "qcs_tracking", "ideal"):
        label = rs.STRATEGY_LABELS[strategy]
        if strategy == "ideal":
            label += " (finite key)"
        plot_metric(ax, rows, strategy, "secret_key_rate", STRATEGY_STYLE[strategy], label, log_drop_zero=True)
    ax.set_yscale("log")
    ax.set_ylim(1e-7, 3)
    ax.set_xlim(-5, 215)
    ax.set_xlabel("Fibre distance (km)")
    ax.set_ylabel("Secret key rate (bits/slot)")
    below_legend(ax, ncol=2)
    write_csv(rows, "fig08_distance.csv")
    _write_operating_point_table(rows)
    return save(fig, "fig08_distance")


def _write_operating_point_table(rows):
    keep = [25, 50, 100, 150]
    order = ("classical", "qcs_preamble", "qcs_tracking", "ideal")
    table = []
    for d in keep:
        for strategy in order:
            match = [r for r in rows if r["series"] == strategy and r["value"] == d]
            if not match:
                continue
            r = match[0]
            table.append({
                "distance_km": d,
                "strategy": rs.STRATEGY_LABELS[strategy],
                "sync_overhead_pct": round(r["sync_overhead_mean"] * 100, 2),
                "gate_rms_error_ps": round(r["sync_rms_error_ns_mean"] * 1e3, 1),
                "timing_capture_pct": round(r["timing_capture_rate_mean"] * 100, 2),
                "qber_pct": round(r["qber_mean"] * 100, 2),
                "secret_key_rate_bits_per_slot": f"{r['secret_key_rate_mean']:.3e}",
                "blocks_accepted_pct": round(r["accepted_mean"] * 100, 1),
            })
    write_csv(table, "table_operating_points.csv")
    header = list(table[0].keys())
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(row[h]) for h in header) + " |" for row in table]
    (OUTPUT_DIR / "table_operating_points.md").write_text(
        "Operating points (N = 10^8 slots per block, W = 2 ns, sigma = 0.35 ns, "
        "offset 4 ns, drift 20 ppm).\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Fig. 9 - sensitivity heatmaps
# ---------------------------------------------------------------------------

def _heatmap(ax, matrix, x_labels, y_labels, xlabel, ylabel, cbar_label, fig):
    image = ax.imshow(matrix, origin="lower", aspect="auto", cmap=BLUES)
    ax.set_xticks(range(len(x_labels)), x_labels)
    ax.set_yticks(range(len(y_labels)), y_labels)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(False)
    vmax = np.nanmax(matrix) if np.isfinite(matrix).any() else 1
    for (i, j), value in np.ndenumerate(matrix):
        color = "white" if value > 0.55 * vmax else INK
        ax.text(j, i, f"{value:.1f}" if value > 0 else "0", ha="center", va="center", fontsize=6, color=color)
    fig.colorbar(image, ax=ax, label=cbar_label, shrink=0.9)


def fig09_heatmaps(ctx):
    fig, axes = new_figure(2, height=3.2)
    windows = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]
    jitters = [0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5]
    base = ResearchConfig(distance_km=125, num_slots=ctx.slots(10 ** 8))
    rows_a = rs.run_sweeps([
        ("fig09a", "detector_window_ns", windows, replace(base, timing_jitter_ns=j), ctx.trials(4), f"jitter={j}")
        for j in jitters
    ])
    matrix_a = np.array([[r["secret_key_rate_mean"] * 1e4 for r in series_rows(rows_a, f"jitter={j}")]
                         for j in jitters])
    _heatmap(axes[0], matrix_a, [f"{w:g}" for w in windows], [f"{j:g}" for j in jitters],
             "Detector gate width W (ns)", "Arrival-time jitter σ (ns)",
             "Secret key rate (10⁻⁴ bits/slot)", fig)
    panel_label(axes[0], "a")

    spacings = [1000, 300, 100, 30, 10]
    distances = [50, 75, 100, 125, 150, 175]
    base_b = ResearchConfig(num_slots=ctx.slots(10 ** 8), freq_wander_ppm_per_sqrt_ms=0.1)
    rows_b = rs.run_sweeps([
        ("fig09b", "pilot_spacing_slots", spacings, replace(base_b, distance_km=d), ctx.trials(4), f"{d} km")
        for d in distances
    ])
    ideal_rows = rs.run_sweeps([("fig09b_ideal", "distance_km", distances,
                                 replace(base_b, sync_strategy="ideal"), ctx.trials(20), "ideal")])
    ideal = {row["value"]: row for row in ideal_rows}
    matrix_b = np.array([[
        100 * r["secret_key_rate_mean"] / ideal[d]["secret_key_rate_mean"]
        if ideal[d]["secret_key_rate_mean"] > 0 else 0.0
        # series_rows sorts by spacing ascending; reverse so columns follow the labels
        for r in series_rows(rows_b, f"{d} km")[::-1]] for d in distances])
    _heatmap(axes[1], matrix_b, [f"{100 / s:.2g}" for s in spacings], [str(d) for d in distances],
             "Pilot overhead (% of slots)", "Fibre distance (km)",
             "Key rate relative to perfect sync (%)", fig)
    panel_label(axes[1], "b")
    for row in rows_b:
        row["ideal_secret_key_rate"] = ideal[int(row["series"].split()[0])]["secret_key_rate_mean"]
    write_csv(rows_a + rows_b, "fig09_heatmaps.csv")
    return save(fig, "fig09_heatmaps")


# ---------------------------------------------------------------------------
# Fig. 10 - long-run stability
# ---------------------------------------------------------------------------

def fig10_long_run(ctx):
    fig, axes = new_figure(2, width=DOUBLE_COLUMN)
    csv_rows = []
    for ax, letter, distance in zip(axes, "ab", (25, 125)):
        cfg = ResearchConfig(distance_km=distance, num_slots=ctx.slots(10 ** 8), freq_wander_ppm_per_sqrt_ms=0.2)
        for strategy in rs.SYNC_STRATEGIES:
            times, capture = rs.timing_trace(replace(cfg, sync_strategy=strategy), rs.make_rng("fig10", distance))
            style = dict(STRATEGY_STYLE[strategy])
            style.pop("marker")
            ax.plot(times / 1e6, capture * 100, label=rs.STRATEGY_LABELS[strategy], **style)
            csv_rows += [{"distance_km": distance, "strategy": strategy, "time_ms": t / 1e6, "capture_pct": c * 100}
                         for t, c in zip(times, capture)]
        ax.set_xlabel("Time in block (ms)")
        ax.set_ylabel("Timing capture (%)")
        ax.set_ylim(-4, 104)
        ax.set_title(f"{distance} km, oscillator wander 0.2 ppm/√ms", loc="left", color=INK_2)
        panel_label(ax, letter)
    shared_legend(fig, axes[0])
    write_csv(csv_rows, "fig10_long_run.csv")
    return save(fig, "fig10_long_run", axes)


# ---------------------------------------------------------------------------
# Fig. 11 - finite-key scaling
# ---------------------------------------------------------------------------

def fig11_finite_key(ctx):
    fig, axes = new_figure(2, width=DOUBLE_COLUMN * 0.85)
    sizes = [10 ** 4, 3 * 10 ** 4, 10 ** 5, 3 * 10 ** 5, 10 ** 6, 3 * 10 ** 6, 10 ** 7, 3 * 10 ** 7, 10 ** 8]
    if ctx.quick:
        sizes = [n for n in sizes if n <= 10 ** 7]
    strategies = ("classical", "qcs_tracking", "ideal")
    all_rows = []
    for ax, letter, distance in zip(axes, "ab", (25, 100)):
        base = ResearchConfig(distance_km=distance)
        rows = rs.strategy_sweep(f"fig11_{distance}", "num_slots", sizes, base, ctx.trials(20), strategies)
        all_rows += rows
        capture = erf(base.detector_window_ns / 2 / (base.timing_jitter_ns * math.sqrt(2)))
        ax.axhline(rs.expected_asymptotic_rate(base, capture), color=INK_2, linestyle=":", linewidth=1.1,
                   label="Asymptotic limit")
        for strategy in strategies:
            plot_metric(ax, rows, strategy, "secret_key_rate", STRATEGY_STYLE[strategy],
                        rs.STRATEGY_LABELS[strategy], log_drop_zero=True)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Block size N (slots)")
        ax.set_ylabel("Secret key rate (bits/slot)")
        ax.set_title(f"{distance} km", loc="left", color=INK_2)
        panel_label(ax, letter)
    shared_legend(fig, axes[1], ncol=4)
    write_csv(all_rows, "fig11_finite_key.csv")
    return save(fig, "fig11_finite_key", axes)


# ---------------------------------------------------------------------------
# Fig. 12 - where the sifted bits go
# ---------------------------------------------------------------------------

def fig12_key_budget(ctx):
    fig, axes = new_figure(1, width=SINGLE_COLUMN + 1.4, height=3.1)
    ax = axes[0]
    base = ResearchConfig(num_slots=ctx.slots(10 ** 7))
    eve = np.round(np.arange(0, 0.4501, 0.01), 3)
    rows = rs.sweep("fig12", "eve_rate", eve, base, ctx.trials(20))
    budget = []
    for r in rows:
        sifted = r["sifted_bits_mean"]
        q = r["qber_mean"]
        k = math.ceil(base.test_fraction * sifted)
        n = sifted - k
        mu = statistical_fluctuation(n, k)
        parts = {
            "Parameter estimation (test bits)": k,
            "Error-correction leakage": 1.16 * n * binary_entropy(q),
            "Privacy amplification, asymptotic": n * binary_entropy(q),
            "Privacy amplification, finite-size": n * (binary_entropy(min(0.5, q + mu)) - binary_entropy(q))
            + math.log2(2 / (EPS_SEC ** 2 * EPS_COR)),
        }
        used = sum(parts.values())
        aborted = q > QBER_TOLERANCE or used >= sifted
        if aborted:
            parts = {key: 0.0 for key in parts}
            parts["Discarded (abort)"] = sifted
            parts["Final secret key"] = 0.0
        else:
            parts["Discarded (abort)"] = 0.0
            parts["Final secret key"] = sifted - used
        budget.append({"eve_rate": r["value"], "qber": q, **{key: v / sifted for key, v in parts.items()}})

    order = ["Final secret key", "Error-correction leakage", "Privacy amplification, asymptotic",
             "Privacy amplification, finite-size", "Parameter estimation (test bits)", "Discarded (abort)"]
    colors = [SERIES[0], SERIES[1], SERIES[2], SERIES[3], NEUTRAL, "#e6e5e1"]
    x = [b["eve_rate"] for b in budget]
    ax.stackplot(x, *[[b[key] * 100 for b in budget] for key in order], labels=order, colors=colors,
                 edgecolor="white", linewidth=0.6)
    ax.set_xlim(0, max(x))
    ax.set_ylim(0, 100)
    ax.set_xlabel("Eve interception fraction")
    ax.set_ylabel("Share of sifted bits (%)")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=6.3)
    ax.grid(False)
    write_csv(budget, "fig12_key_budget.csv")
    return save(fig, "fig12_key_budget")


# ---------------------------------------------------------------------------
# Fig. 13 - timing side-channel attacks
# ---------------------------------------------------------------------------

def fig13_timing_attacks(ctx):
    fig, axes = new_figure(3, height=3.5)
    window, jitter = 2.0, 0.35
    shifts = np.linspace(0, 1.5, 61)
    mismatches = (0.2, 0.4, 0.8)
    csv_rows = []
    for i, mismatch in enumerate(mismatches):
        info, rate = eve_information(shifts, mismatch, window, jitter)
        axes[0].plot(shifts, info, color=SERIES[i], label=f"classical ref., mismatch {mismatch:g} ns")
        axes[1].plot(shifts, rate * 100, color=SERIES[i], label=f"mismatch {mismatch:g} ns")
        csv_rows += [{"mismatch_ns": mismatch, "shift_ns": s, "eve_information_bits": v, "relative_click_rate": r}
                     for s, v, r in zip(shifts, info, rate)]
    axes[0].plot(shifts, np.zeros_like(shifts), color=INK, linestyle="--", label="QCS (uniform delay absorbed)")
    axes[0].set_xlabel("Reference delay / time shift (ns)")
    axes[0].set_ylabel("Eve's information (bits per sifted bit)")
    below_legend(axes[0], ncol=1)
    axes[1].set_xlabel("Reference delay / time shift (ns)")
    axes[1].set_ylabel("Bob's click rate (% of unattacked)")
    below_legend(axes[1], ncol=1)

    monitor_shifts = np.linspace(0, 0.6, 25)
    detections = (100, 1000, 10000)
    power = variance_monitor_power(monitor_shifts, detections, 0.4, window, jitter,
                                   rng=rs.make_rng("fig13"), moment_samples=100_000 if ctx.quick else 400_000)
    for i, n in enumerate(detections):
        axes[2].plot(monitor_shifts, power[i] * 100, color=SERIES[i], marker=SERIES_MARKERS[i],
                     label=f"{n:,} detections")
        csv_rows += [{"monitor_detections": n, "shift_ns": s, "detection_probability": p}
                     for s, p in zip(monitor_shifts, power[i])]
    info_04, _ = eve_information(monitor_shifts, 0.4, window, jitter)
    for row in csv_rows:
        if "monitor_detections" in row:
            row["eve_information_bits_mismatch_0.4"] = float(np.interp(row["shift_ns"], monitor_shifts, info_04))
    axes[2].set_xlabel("Random time shift ±s (ns)")
    axes[2].set_ylabel("Attack flagged by QCS monitor (%)")
    below_legend(axes[2], ncol=1, title="detections used (false alarm 10⁻³)", title_fontsize=6.5)
    for ax, letter in zip(axes, "abc"):
        panel_label(ax, letter)
    write_csv(csv_rows, "fig13_timing_attacks.csv")
    return save(fig, "fig13_timing_attacks", axes)


FIGURES = [
    fig01_system_model,
    fig02_model_validation,
    fig03_qber_security,
    fig04_acceptance,
    fig05_timing_impairments,
    fig06_window_tradeoff,
    fig07_sync_overhead,
    fig08_distance,
    fig09_heatmaps,
    fig10_long_run,
    fig11_finite_key,
    fig12_key_budget,
    fig13_timing_attacks,
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="fewer trials and capped block sizes")
    parser.add_argument("--only", nargs="*", help="figure prefixes to generate, e.g. fig05 fig08")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = parser.parse_args()

    ctx = Context(quick=args.quick)
    rs.set_workers(args.workers)
    selected = [f for f in FIGURES if not args.only or any(f.__name__.startswith(p) for p in args.only)]
    print(f"Generating {len(selected)} figure(s) into {OUTPUT_DIR}/ "
          f"({'quick' if args.quick else 'full'} mode, {args.workers} workers)")
    try:
        for function in selected:
            start = time.time()
            path = function(ctx)
            print(f"  {path}  ({time.time() - start:.0f} s)")
    finally:
        rs.set_workers(0)


if __name__ == "__main__":
    main()
