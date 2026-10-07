import random


def generate_emission_times(num_qubits, clock_period_ns):
    """
    Alice sends one photon/qubit in each clock slot.
    """
    return [i * clock_period_ns for i in range(num_qubits)]


def simulate_arrival_times(
    emission_times,
    propagation_delay_ns,
    clock_offset_ns,
    clock_drift_ppm,
    timing_jitter_ns,
):
    """
    Simulate photon arrival times at Bob.

    offset: constant clock mismatch between Alice and Bob
    drift : slow rate mismatch between the two clocks
    jitter: random timing uncertainty from source/channel/detector
    """
    drift = clock_drift_ppm / 1_000_000
    arrival_times = []

    for send_time in emission_times:
        jitter = random.gauss(0, timing_jitter_ns)
        arrival_time = propagation_delay_ns + clock_offset_ns
        arrival_time += send_time * (1 + drift)
        arrival_time += jitter
        arrival_times.append(arrival_time)

    return arrival_times


def estimate_clock_model(emission_times, arrival_times, sync_sample_count=40):
    """
    Estimate Bob's corrected gate timing as:
        arrival_time ~= intercept + slope * alice_send_time

    This keeps the simulation simple while still showing the real QCS idea:
    Bob learns the offset and drift before opening detector gates.
    """
    sample_count = min(sync_sample_count, len(emission_times), len(arrival_times))

    if sample_count == 0:
        return 0.0, 1.0

    xs = emission_times[:sample_count]
    ys = arrival_times[:sample_count]

    mean_x = sum(xs) / sample_count
    mean_y = sum(ys) / sample_count

    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs)

    slope = numerator / denominator if denominator else 1.0
    intercept = mean_y - slope * mean_x

    return intercept, slope


def detection_mask(arrival_times, gate_centers, detector_window_ns):
    """
    Return True when Bob's detector gate catches the arriving photon.
    """
    half_window = detector_window_ns / 2

    return [
        abs(arrival - gate_center) <= half_window
        for arrival, gate_center in zip(arrival_times, gate_centers)
    ]


def detection_percentage(mask):
    if not mask:
        return 0.0

    return (sum(1 for item in mask if item) / len(mask)) * 100


def filter_detected(items, mask):
    return [item for item, detected in zip(items, mask) if detected]


def build_qcs_result(
    num_qubits,
    clock_period_ns=10.0,
    propagation_delay_ns=50.0,
    clock_offset_ns=4.0,
    clock_drift_ppm=40.0,
    timing_jitter_ns=0.35,
    detector_window_ns=2.0,
    sync_sample_count=200,
):
    """
    Build timing data for one BB84 attempt and return both synchronized
    and unsynchronized detection results.
    """
    emission_times = generate_emission_times(num_qubits, clock_period_ns)
    arrival_times = simulate_arrival_times(
        emission_times,
        propagation_delay_ns,
        clock_offset_ns,
        clock_drift_ppm,
        timing_jitter_ns,
    )

    unsynced_gate_centers = [
        propagation_delay_ns + send_time
        for send_time in emission_times
    ]

    intercept, slope = estimate_clock_model(
        emission_times,
        arrival_times,
        sync_sample_count=sync_sample_count,
    )

    synced_gate_centers = [
        intercept + slope * send_time
        for send_time in emission_times
    ]

    unsynced_mask = detection_mask(
        arrival_times,
        unsynced_gate_centers,
        detector_window_ns,
    )
    synced_mask = detection_mask(
        arrival_times,
        synced_gate_centers,
        detector_window_ns,
    )

    return {
        "emission_times": emission_times,
        "arrival_times": arrival_times,
        "unsynced_mask": unsynced_mask,
        "synced_mask": synced_mask,
        "estimated_offset_ns": intercept - propagation_delay_ns,
        "estimated_drift_ppm": (slope - 1) * 1_000_000,
        "unsynced_detection_pct": detection_percentage(unsynced_mask),
        "synced_detection_pct": detection_percentage(synced_mask),
        "detector_window_ns": detector_window_ns,
    }


def compare_detection_windows(
    num_qubits,
    window_sizes_ns,
    clock_period_ns=10.0,
    propagation_delay_ns=50.0,
    clock_offset_ns=4.0,
    clock_drift_ppm=40.0,
    timing_jitter_ns=0.35,
    sync_sample_count=200,
):
    """
    Use the same timing run for each detector window so the comparison is fair.
    """
    emission_times = generate_emission_times(num_qubits, clock_period_ns)
    arrival_times = simulate_arrival_times(
        emission_times,
        propagation_delay_ns,
        clock_offset_ns,
        clock_drift_ppm,
        timing_jitter_ns,
    )

    unsynced_gate_centers = [
        propagation_delay_ns + send_time
        for send_time in emission_times
    ]

    intercept, slope = estimate_clock_model(
        emission_times,
        arrival_times,
        sync_sample_count=sync_sample_count,
    )

    synced_gate_centers = [
        intercept + slope * send_time
        for send_time in emission_times
    ]

    rows = []

    for window_ns in window_sizes_ns:
        unsynced_mask = detection_mask(arrival_times, unsynced_gate_centers, window_ns)
        synced_mask = detection_mask(arrival_times, synced_gate_centers, window_ns)

        rows.append({
            "window_ns": window_ns,
            "unsynced_detected": sum(1 for item in unsynced_mask if item),
            "synced_detected": sum(1 for item in synced_mask if item),
            "unsynced_pct": detection_percentage(unsynced_mask),
            "synced_pct": detection_percentage(synced_mask),
        })

    return rows
