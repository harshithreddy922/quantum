"""
Research model of QCS-assisted BB84.

The model is a Monte Carlo simulation of one key-exchange block:

1. Timing layer   - Alice emits one pulse per clock slot. Bob's clock has an
                    offset, a linear drift and (optionally) random-walk
                    frequency wander. Bob opens a detector gate of width W
                    around his estimate of each arrival time. The gate
                    estimate comes from one of the synchronization strategies
                    in SYNC_STRATEGIES.
2. Physical layer - fibre attenuation, detector efficiency, dark counts that
                    scale with the gate width, Pauli channel noise and a
                    partial intercept-resend attack.
3. Protocol layer - basis sifting, QBER estimation on a random test subset,
                    error-correction leakage and privacy amplification sized
                    by the finite-key bound in bb84.security.

Sync pulses (preamble and interleaved pilots) are simulated photon by photon
and are subject to the same loss and dark counts as key pulses; the slots
they occupy are charged to the key rate as overhead.

Signal clicks in key slots are drawn from a binomial with the mean capture
probability of the block, which is exact in expectation and keeps the model
fast enough for 10^7-slot blocks.
"""

import csv
import math
import zlib
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
from scipy.special import ndtr

from bb84.qcs_tracking import acquire_preamble, predict_timing_error, run_timing_tracker
from bb84.security import (
    QBER_TOLERANCE,
    asymptotic_secret_fraction,
    finite_key_length,
    wilson_interval,
)


OUTPUT_DIR = Path("research_outputs")
MASTER_SEED = 20261007
CAPTURE_SAMPLE_POINTS = 50_000

SYNC_STRATEGIES = ("none", "classical", "qcs_preamble", "qcs_tracking", "ideal")
STRATEGY_LABELS = {
    "none": "No synchronization",
    "classical": "Classical reference",
    "qcs_preamble": "QCS (preamble only)",
    "qcs_tracking": "QCS (preamble + pilot tracking)",
    "ideal": "Perfect synchronization",
}


@dataclass(frozen=True)
class ResearchConfig:
    # Block
    num_slots: int = 100_000
    clock_period_ns: float = 10.0

    # Channel and detectors
    distance_km: float = 25.0
    fiber_loss_db_per_km: float = 0.2
    detector_efficiency: float = 0.6
    dark_count_rate_hz: float = 1e4          # per detector
    pauli_error_rate: float = 0.03           # bit error = 2/3 of this
    eve_rate: float = 0.0                    # intercept-resend fraction

    # Timing impairments
    clock_offset_ns: float = 4.0
    clock_drift_ppm: float = 20.0
    freq_wander_ppm_per_sqrt_ms: float = 0.01      # random-walk FM of Bob's oscillator
    timing_jitter_ns: float = 0.35
    detector_window_ns: float = 2.0

    # Synchronization
    sync_strategy: str = "qcs_tracking"
    preamble_target_detections: int = 64     # acquisition stops after ~this many photons
    preamble_max_fraction: float = 0.2       # cap on preamble share of the block
    preamble_spacing_slots: int = 5
    pilot_spacing_slots: int = 100           # 1 pilot per 100 slots = 1 %
    classical_residual_ns: float = 0.5
    prior_drift_ppm: float = 100.0           # acquisition search range

    # Protocol
    test_fraction: float = 0.1


@dataclass
class TrialResult:
    num_slots: int
    key_slots: int
    sync_overhead: float
    sync_detections: int
    sync_rms_error_ns: float
    timing_capture_rate: float
    detection_rate: float
    sifted_bits: int
    qber: float
    qber_test: float
    accepted: int
    final_key_bits: int
    secret_key_rate: float
    asymptotic_key_rate: float


# ---------------------------------------------------------------------------
# Physical quantities
# ---------------------------------------------------------------------------

def channel_transmittance(config):
    return 10 ** (-config.fiber_loss_db_per_km * config.distance_km / 10)


def total_efficiency(config):
    return channel_transmittance(config) * config.detector_efficiency


def dark_probability(config, window_ns):
    """Probability that either of Bob's two detectors fires in a gate."""
    return 1 - math.exp(-2 * config.dark_count_rate_hz * window_ns * 1e-9)


def signal_error_probability(config):
    """Bit error on a sifted signal click: channel noise XOR Eve's error."""
    e_channel = 2 * config.pauli_error_rate / 3
    e_eve = config.eve_rate / 4
    return e_channel * (1 - e_eve) + e_eve * (1 - e_channel)


def gate_capture_probability(gate_error_ns, window_ns, jitter_ns):
    """P(|gate_error + jitter| <= W/2) for Gaussian jitter."""
    half = window_ns / 2
    return ndtr((half - gate_error_ns) / jitter_ns) - ndtr((-half - gate_error_ns) / jitter_ns)


# ---------------------------------------------------------------------------
# Timing layer
# ---------------------------------------------------------------------------

def _wander_path(config, rng, duration_ns):
    """Sampled random-walk frequency wander integrated into a timing error."""
    if config.freq_wander_ppm_per_sqrt_ms <= 0:
        return None
    grid = np.linspace(0.0, duration_ns, 4097)
    dt = grid[1] - grid[0]
    sigma_step = config.freq_wander_ppm_per_sqrt_ms * 1e-6 * math.sqrt(dt / 1e6)
    nu = np.concatenate([[0.0], np.cumsum(rng.normal(0, sigma_step, len(grid) - 1))])
    phase = np.concatenate([[0.0], np.cumsum(nu[:-1] * dt)])
    return grid, phase


def true_timing_error(config, times_ns, wander):
    error = config.clock_offset_ns + config.clock_drift_ppm * 1e-6 * np.asarray(times_ns)
    if wander is not None:
        error = error + np.interp(times_ns, wander[0], wander[1])
    return error


def _sync_slot_layout(config):
    """Times of preamble and pilot sync slots and the overhead they cost."""
    period = config.clock_period_ns
    strategy = config.sync_strategy
    if strategy not in ("qcs_preamble", "qcs_tracking"):
        return np.empty(0), np.empty(0), 0, 0.0

    # Bob keeps the preamble running until he expects the target number of
    # detected photons, so acquisition time grows as 1/eta with distance.
    wanted = math.ceil(config.preamble_target_detections / total_efficiency(config))
    cap = int(config.preamble_max_fraction * config.num_slots / config.preamble_spacing_slots)
    n_pre = max(2, min(wanted, cap))
    preamble_slots = n_pre * config.preamble_spacing_slots
    pre_times = np.arange(n_pre) * config.preamble_spacing_slots * period

    pilot_times = np.empty(0)
    if strategy == "qcs_tracking" and config.pilot_spacing_slots > 0:
        pilot_slots = np.arange(preamble_slots, config.num_slots, config.pilot_spacing_slots)
        pilot_times = pilot_slots * period

    overhead_slots = preamble_slots + len(pilot_times)
    return pre_times, pilot_times, overhead_slots, preamble_slots * period


def synchronize(config, rng, wander):
    """
    Simulate the sync layer and return (gate_error_fn, sync_detections,
    overhead_slots, key_start_ns).

    gate_error_fn(times) -> true arrival time minus Bob's gate centre.
    """
    strategy = config.sync_strategy
    if strategy == "ideal":
        return (lambda t: np.zeros_like(t)), 0, 0, 0.0
    if strategy == "none":
        return (lambda t: true_timing_error(config, t, wander)), 0, 0, 0.0
    if strategy == "classical":
        residual = rng.normal(0.0, config.classical_residual_ns)
        return (lambda t: np.full_like(t, residual)), 0, 0, 0.0

    pre_times, pilot_times, overhead_slots, key_start = _sync_slot_layout(config)
    eta = total_efficiency(config)
    jitter = config.timing_jitter_ns

    # Stage 1: acquisition. Bob free-runs his time tagger during a sparse
    # preamble; every tag is referred to the nearest preamble pulse, so the
    # timing error is known modulo the preamble spacing. Dark counts arrive
    # uniformly over the whole preamble.
    spacing_ns = config.preamble_spacing_slots * config.clock_period_ns
    survive = rng.random(len(pre_times)) < eta
    signal_times = pre_times[survive]
    signal_z = true_timing_error(config, signal_times, wander) + rng.normal(0, jitter, len(signal_times))
    n_dark = rng.poisson(2 * config.dark_count_rate_hz * key_start * 1e-9)
    dark_times = np.sort(rng.uniform(0, key_start, n_dark))
    dark_times = np.round(dark_times / spacing_ns) * spacing_ns
    tag_times = np.concatenate([signal_times, dark_times])
    tag_z = np.concatenate([signal_z, rng.uniform(-spacing_ns / 2, spacing_ns / 2, n_dark)])
    order = np.argsort(tag_times, kind="stable")
    state = acquire_preamble(
        tag_times[order],
        np.mod(tag_z[order] + spacing_ns / 2, spacing_ns) - spacing_ns / 2,
        jitter,
        wrap_period=spacing_ns,
        max_drift=config.prior_drift_ppm * 1e-6,
    )
    if state is None:
        # Acquisition failed: Bob falls back to his nominal schedule.
        state = (key_start, 0.0, 0.0, (spacing_ns / 4) ** 2, 0.0, (config.prior_drift_ppm * 1e-6) ** 2)

    # Stage 2: Kalman tracking on interleaved pilots.
    # Kalman process noise matched to the oscillator's frequency wander.
    tracker_q = (max(config.freq_wander_ppm_per_sqrt_ms, 0.005) * 1e-6) ** 2 / 1e6
    # Pilot clicks are time-tagged over the whole clock slot; dark counts
    # in that window are removed by the tracker's innovation gate.
    acq_pilot = config.clock_period_ns / 2
    p_dark_pilot = 1 - math.exp(-2 * config.dark_count_rate_hz * 2 * acq_pilot * 1e-9)
    pilot_survive = rng.random(len(pilot_times)) < eta
    pilot_dark = rng.random(len(pilot_times)) < p_dark_pilot
    events = pilot_survive | pilot_dark
    times = pilot_times[events]
    update_t, tau, nu = run_timing_tracker(
        event_times=times,
        true_error=true_timing_error(config, times, wander),
        signal_present=pilot_survive[events],
        jitter=rng.normal(0.0, jitter, len(times)),
        dark_present=pilot_dark[events],
        dark_uniform=rng.random(len(times)),
        acquisition_half_width=np.full(len(times), acq_pilot),
        jitter_sigma=jitter,
        initial_state=state,
        process_noise_nu=tracker_q,
    )
    sync_detections = int(survive.sum() + pilot_survive.sum())
    freeze = key_start if strategy == "qcs_preamble" else None

    def gate_error(t):
        estimate = predict_timing_error(t, update_t, tau, nu, freeze_after=freeze)
        return true_timing_error(config, t, wander) - estimate

    return gate_error, sync_detections, overhead_slots, key_start


# ---------------------------------------------------------------------------
# One block
# ---------------------------------------------------------------------------

def simulate_trial(config, rng):
    duration = config.num_slots * config.clock_period_ns
    wander = _wander_path(config, rng, duration)
    gate_error_fn, sync_detections, overhead_slots, key_start = synchronize(config, rng, wander)

    key_slots = max(0, config.num_slots - overhead_slots)
    sample_times = np.linspace(key_start, duration, min(CAPTURE_SAMPLE_POINTS, max(key_slots, 1)))
    gate_error = gate_error_fn(sample_times)
    capture = float(np.mean(gate_capture_probability(
        gate_error, config.detector_window_ns, config.timing_jitter_ns
    )))
    sync_rms = float(np.sqrt(np.mean(gate_error ** 2)))

    p_signal = total_efficiency(config) * capture
    p_dark = dark_probability(config, config.detector_window_ns)

    n_signal = rng.binomial(key_slots, p_signal)
    n_dark_only = rng.binomial(key_slots - n_signal, p_dark)
    n_double = rng.binomial(n_signal, p_dark)
    n_clean = n_signal - n_double
    n_noisy = n_dark_only + n_double

    sift_clean = rng.binomial(n_clean, 0.5)
    sift_noisy = rng.binomial(n_noisy, 0.5)
    errors = rng.binomial(sift_clean, signal_error_probability(config)) + rng.binomial(sift_noisy, 0.5)
    sifted = sift_clean + sift_noisy

    k_test = int(math.ceil(config.test_fraction * sifted)) if sifted else 0
    test_errors = rng.hypergeometric(errors, sifted - errors, k_test) if k_test else 0
    qber_test = test_errors / k_test if k_test else 0.0
    qber = errors / sifted if sifted else 0.0

    final_bits = finite_key_length(sifted - k_test, k_test, qber_test)
    accepted = int(sifted > 0 and qber_test <= QBER_TOLERANCE and final_bits > 0)

    asymptotic = 0.0
    if sifted and qber <= QBER_TOLERANCE:
        asymptotic = sifted / config.num_slots * float(asymptotic_secret_fraction(qber))

    return TrialResult(
        num_slots=config.num_slots,
        key_slots=key_slots,
        sync_overhead=overhead_slots / config.num_slots,
        sync_detections=sync_detections,
        sync_rms_error_ns=sync_rms,
        timing_capture_rate=capture,
        detection_rate=(n_signal + n_dark_only) / key_slots if key_slots else 0.0,
        sifted_bits=sifted,
        qber=qber,
        qber_test=qber_test,
        accepted=accepted,
        final_key_bits=final_bits,
        secret_key_rate=final_bits / config.num_slots,
        asymptotic_key_rate=asymptotic,
    )


# ---------------------------------------------------------------------------
# Analytic expectations (used to validate the Monte Carlo engine)
# ---------------------------------------------------------------------------

def expected_detection_rate(config, capture):
    p_signal = total_efficiency(config) * capture
    return p_signal + (1 - p_signal) * dark_probability(config, config.detector_window_ns)


def expected_qber(config, capture=1.0):
    p_signal = total_efficiency(config) * capture
    p_dark = dark_probability(config, config.detector_window_ns)
    clean = p_signal * (1 - p_dark)
    noisy = p_dark * (1 - p_signal) + p_signal * p_dark
    return (clean * signal_error_probability(config) + 0.5 * noisy) / (clean + noisy)


def expected_asymptotic_rate(config, capture=1.0):
    rate = 0.5 * expected_detection_rate(config, capture)
    return rate * asymptotic_secret_fraction(expected_qber(config, capture))


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------

def make_rng(*keys):
    """Deterministic generator derived from the master seed and string keys."""
    material = [MASTER_SEED] + [
        zlib.crc32(str(key).encode()) for key in keys
    ]
    return np.random.default_rng(material)


def run_trials(config, trials, rng):
    return [simulate_trial(config, rng) for _ in range(trials)]


def summarize(results):
    summary = {}
    n = len(results)
    for key in asdict(results[0]):
        values = np.array([getattr(r, key) for r in results], dtype=float)
        mean = float(values.mean())
        std = float(values.std(ddof=1)) if n > 1 else 0.0
        summary[f"{key}_mean"] = mean
        summary[f"{key}_std"] = std
        summary[f"{key}_ci95"] = 1.96 * std / math.sqrt(n) if n > 1 else 0.0
    _, lo, hi = wilson_interval(int(sum(r.accepted for r in results)), n)
    summary["accepted_wilson_low"] = lo
    summary["accepted_wilson_high"] = hi
    return summary


def _run_point(task):
    config, trials, keys = task
    return summarize(run_trials(config, trials, make_rng(*keys)))


_EXECUTOR = None


def set_workers(workers):
    """Run sweep points on a process pool (workers > 1) or serially."""
    global _EXECUTOR
    if _EXECUTOR is not None:
        _EXECUTOR.shutdown()
        _EXECUTOR = None
    if workers and workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        _EXECUTOR = ProcessPoolExecutor(max_workers=workers)


def run_points(tasks):
    if _EXECUTOR is None:
        return [_run_point(task) for task in tasks]
    return list(_EXECUTOR.map(_run_point, tasks))


def sweep_tasks(experiment, parameter, values, base_config, trials, label=None):
    label = label or base_config.sync_strategy
    tasks, meta = [], []
    for value in values:
        cast = type(getattr(base_config, parameter))
        config = replace(base_config, **{parameter: cast(value)})
        tasks.append((config, trials, (experiment, label, parameter, value)))
        meta.append({
            "experiment": experiment,
            "series": label,
            "parameter": parameter,
            "value": value,
            "trials": trials,
        })
    return tasks, meta


def run_sweeps(specs):
    """Run several sweeps in one batch. specs: list of sweep_tasks() args."""
    all_tasks, all_meta = [], []
    for spec in specs:
        tasks, meta = sweep_tasks(*spec)
        all_tasks.extend(tasks)
        all_meta.extend(meta)
    return [{**m, **summary} for m, summary in zip(all_meta, run_points(all_tasks))]


def sweep(experiment, parameter, values, base_config, trials, label=None):
    return run_sweeps([(experiment, parameter, values, base_config, trials, label)])


def strategy_sweep(experiment, parameter, values, base_config, trials, strategies=SYNC_STRATEGIES):
    return run_sweeps([
        (experiment, parameter, values, replace(base_config, sync_strategy=s), trials, s)
        for s in strategies
    ])


def timing_trace(config, rng, bins=200):
    """Timing-capture rate in time bins across one block (one realization)."""
    duration = config.num_slots * config.clock_period_ns
    wander = _wander_path(config, rng, duration)
    gate_error_fn, _, _, key_start = synchronize(config, rng, wander)
    times = np.linspace(key_start, duration, bins * 250)
    capture = gate_capture_probability(
        gate_error_fn(times), config.detector_window_ns, config.timing_jitter_ns
    )
    return times.reshape(bins, -1).mean(axis=1), capture.reshape(bins, -1).mean(axis=1)


def write_csv(rows, filename, output_dir=OUTPUT_DIR):
    output_dir.mkdir(exist_ok=True)
    path = output_dir / filename
    if not rows:
        return path
    fieldnames = list(rows[0].keys())
    for row in rows[1:]:
        fieldnames.extend(key for key in row if key not in fieldnames)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path

