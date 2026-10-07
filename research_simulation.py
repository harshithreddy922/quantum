import csv
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, stdev

from bb84.module10_qber_decision import qber_decision
from bb84.qcs_synchronization import build_qcs_result


OUTPUT_DIR = Path("research_outputs")
QBER_THRESHOLD = 0.11


@dataclass
class ResearchConfig:
    num_qubits: int = 2048
    noise_rate: float = 0.03
    eve_rate: float = 0.0
    detector_efficiency: float = 0.85
    dark_count_rate: float = 0.001
    channel_loss_db_per_km: float = 0.2
    distance_km: float = 10.0
    clock_period_ns: float = 10.0
    propagation_delay_ns: float = 50.0
    clock_offset_ns: float = 4.0
    clock_drift_ppm: float = 40.0
    timing_jitter_ns: float = 0.35
    detector_window_ns: float = 2.0
    sync_sample_count: int = 200
    use_qcs: bool = True
    final_key_target_bits: int = 256


@dataclass
class TrialResult:
    raw_qubits: int
    timing_captured_bits: int
    timing_capture_rate: float
    detected_bits: int
    detection_rate: float
    sifted_bits: int
    sifted_key_rate: float
    qber: float
    accepted: int
    corrected_errors: int
    leaked_reconciliation_bits: float
    estimated_eve_known_bits: float
    final_key_bits: int
    secret_key_rate: float


def binary_entropy(p):
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def channel_survival_probability(config):
    attenuation_db = config.channel_loss_db_per_km * config.distance_km
    channel_transmission = 10 ** (-attenuation_db / 10)
    return max(0.0, min(1.0, channel_transmission * config.detector_efficiency))


def estimate_privacy_amplified_length(sifted_bits, qber, eve_rate, target_bits):
    if sifted_bits <= 0 or qber > QBER_THRESHOLD:
        return 0

    reconciliation_leak = 1.16 * sifted_bits * binary_entropy(qber)
    eve_information = 0.5 * eve_rate * sifted_bits
    security_margin = 0.05 * sifted_bits
    remaining = sifted_bits - reconciliation_leak - eve_information - security_margin
    return max(0, min(target_bits, int(remaining)))


def simulate_research_trial(config):
    qcs_result = build_qcs_result(
        num_qubits=config.num_qubits,
        clock_period_ns=config.clock_period_ns,
        propagation_delay_ns=config.propagation_delay_ns,
        clock_offset_ns=config.clock_offset_ns,
        clock_drift_ppm=config.clock_drift_ppm,
        timing_jitter_ns=config.timing_jitter_ns,
        detector_window_ns=config.detector_window_ns,
        sync_sample_count=config.sync_sample_count,
    )
    timing_mask = qcs_result["synced_mask"] if config.use_qcs else qcs_result["unsynced_mask"]
    survival_probability = channel_survival_probability(config)
    timing_captured_bits = sum(1 for timing_detected in timing_mask if timing_detected)

    detected_bits = 0
    sifted_bits = 0
    error_bits = 0

    for timing_detected in timing_mask:
        photon_detected = timing_detected and random.random() < survival_probability
        dark_detected = random.random() < config.dark_count_rate

        if not photon_detected and not dark_detected:
            continue

        detected_bits += 1

        alice_basis = random.randrange(2)
        bob_basis = random.randrange(2)
        if alice_basis != bob_basis:
            continue

        sifted_bits += 1

        if dark_detected and not photon_detected:
            error_probability = 0.5
        else:
            channel_error = config.noise_rate * 0.5
            eve_error = config.eve_rate * 0.25
            error_probability = 1 - (1 - channel_error) * (1 - eve_error)

        if random.random() < error_probability:
            error_bits += 1

    qber = error_bits / sifted_bits if sifted_bits else 0.0
    accepted = int(qber_decision(qber) and sifted_bits > 0)
    final_key_bits = estimate_privacy_amplified_length(
        sifted_bits=sifted_bits,
        qber=qber,
        eve_rate=config.eve_rate,
        target_bits=config.final_key_target_bits,
    )
    if not accepted:
        final_key_bits = 0

    reconciliation_leak = 1.16 * sifted_bits * binary_entropy(qber)
    eve_known_bits = 0.5 * config.eve_rate * sifted_bits

    return TrialResult(
        raw_qubits=config.num_qubits,
        timing_captured_bits=timing_captured_bits,
        timing_capture_rate=timing_captured_bits / config.num_qubits,
        detected_bits=detected_bits,
        detection_rate=detected_bits / config.num_qubits,
        sifted_bits=sifted_bits,
        sifted_key_rate=sifted_bits / config.num_qubits,
        qber=qber,
        accepted=accepted,
        corrected_errors=error_bits,
        leaked_reconciliation_bits=reconciliation_leak,
        estimated_eve_known_bits=eve_known_bits,
        final_key_bits=final_key_bits,
        secret_key_rate=final_key_bits / config.num_qubits,
    )


def summarize_results(results):
    keys = asdict(results[0]).keys()
    summary = {}
    for key in keys:
        values = [getattr(result, key) for result in results]
        summary[f"{key}_mean"] = mean(values)
        summary[f"{key}_std"] = stdev(values) if len(values) > 1 else 0.0
    return summary


def run_trials(config, trials=50):
    return [simulate_research_trial(config) for _ in range(trials)]


def sweep(parameter_name, values, base_config=None, trials=50, label=None):
    base_config = base_config or ResearchConfig()
    rows = []

    for value in values:
        config_values = asdict(base_config)
        config_values[parameter_name] = value
        config = ResearchConfig(**config_values)
        results = run_trials(config, trials=trials)
        row = {
            "experiment": label or parameter_name,
            "parameter": parameter_name,
            "value": value,
            "trials": trials,
            **summarize_results(results),
        }
        rows.append(row)

    return rows


def paired_sweep(parameter_name, values, base_config=None, trials=50):
    base_config = base_config or ResearchConfig()
    without_config = ResearchConfig(**{**asdict(base_config), "use_qcs": False})
    with_config = ResearchConfig(**{**asdict(base_config), "use_qcs": True})

    rows = []
    rows.extend(sweep(parameter_name, values, without_config, trials, label="Without QCS"))
    rows.extend(sweep(parameter_name, values, with_config, trials, label="With QCS"))
    return rows


def write_csv(rows, filename):
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / filename
    if not rows:
        return path

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return path
