"""
Photon-limited (qubit-based) clock synchronization for BB84.

Bob recovers Alice's clock from the detection times of single-photon sync
pulses sent over the quantum channel itself (the approach of Qubit4Sync,
Calderaro et al., Phys. Rev. Applied 13, 054041 (2020)). Unlike the earlier
`qcs_synchronization` demo, Bob does not see every sync photon: each sync
pulse survives fibre loss and detector inefficiency only with probability
eta, and dark counts inside the acquisition window produce false timestamps.

Bob's timing error relative to his nominal gate schedule is modelled as

    e(t) = offset + drift * t + wander(t)

and estimated in two stages:

1. Acquisition - a robust (RANSAC) line fit to the time tags collected
   during a sparse sync preamble, which tolerates dark-count outliers.
2. Tracking    - a two-state Kalman filter (timing error tau, frequency
   error nu) updated by interleaved pilot detections. Dark counts are
   rejected with an innovation gate.
"""

import math

import numpy as np


INNOVATION_GATE_SIGMA = 3.0


def _wrap(x, period):
    return (x + period / 2) % period - period / 2


def acquire_preamble(times, measurements, jitter_sigma, wrap_period, max_drift):
    """
    Robust acquisition of (offset, drift) from free-running preamble time tags.

    Bob time-tags every click during the preamble. measurements[i] is the
    click time minus the nominal time of the nearest preamble pulse, so it
    is only known modulo wrap_period (the preamble pulse spacing). Some tags
    are dark counts.

    The drift is found by a grid search: for each candidate drift the tags
    are de-rotated and histogrammed modulo wrap_period, and the candidate
    with the tallest histogram peak wins (a 2-D cross-correlation, as used
    in time-tagger acquisition). Inliers around the peak are unwrapped and
    refined with a least-squares line fit.

    Returns (t_ref, tau, nu, p11, p12, p22) - state and covariance at the
    last tag time - or None when no consistent peak is found.
    """
    times = np.asarray(times, dtype=float)
    z = np.asarray(measurements, dtype=float)
    if len(times) < 2:
        return None

    span = max(times[-1] - times[0], 1.0)
    step = max(jitter_sigma / span, 1e-9)
    candidates = np.arange(-max_drift, max_drift + step, step)
    bin_width = 2 * jitter_sigma
    n_bins = max(1, int(round(wrap_period / bin_width)))

    best_count, best_nu, best_peak = -1, 0.0, 0.0
    for chunk in np.array_split(candidates, max(1, len(candidates) // 512)):
        r = _wrap(z[None, :] - chunk[:, None] * times[None, :], wrap_period)
        bins = ((r + wrap_period / 2) / wrap_period * n_bins).astype(int) % n_bins
        # Count tags per (candidate, bin) and per neighbouring bin pair so a
        # peak split across a bin edge is still found.
        offsets = np.arange(len(chunk))[:, None] * n_bins
        counts = np.bincount((bins + offsets).ravel(), minlength=len(chunk) * n_bins)
        counts = counts.reshape(len(chunk), n_bins)
        paired = counts + np.roll(counts, -1, axis=1)
        flat = int(np.argmax(paired))
        row, col = divmod(flat, n_bins)
        if paired[row, col] > best_count:
            best_count = int(paired[row, col])
            best_nu = float(chunk[row])
            best_peak = (col + 1) * wrap_period / n_bins - wrap_period / 2

    if best_count < 2:
        return None

    r = _wrap(z - best_nu * times - best_peak, wrap_period)
    inliers = np.abs(r) < max(3 * jitter_sigma, bin_width)
    if inliers.sum() < 2:
        return None
    x = times[inliers]
    y = best_nu * x + best_peak + r[inliers]

    t_ref = times[-1]
    x_mean = x.mean()
    x_c = x - x_mean
    sxx = float((x_c ** 2).sum())
    if sxx == 0:
        return None
    nu = float((x_c * (y - y.mean())).sum() / sxx)
    tau = float(y.mean() + nu * (t_ref - x_mean))

    var = jitter_sigma ** 2
    lever = t_ref - x_mean
    p22 = var / sxx
    p11 = var * (1 / len(x) + lever ** 2 / sxx)
    p12 = var * lever / sxx
    return t_ref, tau, nu, p11, p12, p22


def run_timing_tracker(
    event_times,
    true_error,
    signal_present,
    jitter,
    dark_present,
    dark_uniform,
    acquisition_half_width,
    jitter_sigma,
    initial_state,
    process_noise_nu,
):
    """
    Run the Kalman timing tracker over sync-pulse events.

    Parameters are equal-length arrays, one entry per sync slot that holds
    any event (surviving photon and/or dark count). Times are in ns.

    initial_state is (t_ref, tau, nu, p11, p12, p22) from acquisition.

    Returns arrays (update_times, tau, nu) holding Bob's estimate of the
    timing error after every accepted measurement, starting with the
    acquisition state.
    """
    t_last, tau, nu, p11, p12, p22 = initial_state
    r = jitter_sigma ** 2
    q = process_noise_nu
    gate2 = INNOVATION_GATE_SIGMA ** 2

    out_t, out_tau, out_nu = [t_last], [tau], [nu]

    for k in range(len(event_times)):
        t = event_times[k]
        dt = t - t_last

        # Predict
        tau_p = tau + nu * dt
        p11p = p11 + 2 * dt * p12 + dt * dt * p22 + q * dt ** 3 / 3
        p12p = p12 + dt * p22 + q * dt ** 2 / 2
        p22p = p22 + q * dt
        half = acquisition_half_width[k]

        # Bob time-tags whatever click falls in his acquisition window
        z = None
        if signal_present[k]:
            z_signal = true_error[k] + jitter[k]
            if abs(z_signal - tau_p) <= half:
                z = z_signal
        if dark_present[k]:
            z_dark = tau_p + (2 * dark_uniform[k] - 1) * half
            if z is None or z_dark < z:   # first click wins
                z = z_dark
        if z is None:
            continue

        s = p11p + r
        innovation = z - tau_p
        if innovation * innovation > gate2 * s:
            continue

        k1 = p11p / s
        k2 = p12p / s
        tau = tau_p + k1 * innovation
        nu = nu + k2 * innovation
        p11 = (1 - k1) * p11p
        p12 = (1 - k1) * p12p
        p22 = p22p - k2 * p12p
        t_last = t

        out_t.append(t)
        out_tau.append(tau)
        out_nu.append(nu)

    return np.array(out_t), np.array(out_tau), np.array(out_nu)


def predict_timing_error(query_times, update_times, tau, nu, freeze_after=None):
    """
    Bob's estimate of the timing error at query_times, using only updates
    made before each query (causal). With freeze_after set, updates later
    than that time are ignored (preamble-only synchronization).
    """
    query_times = np.asarray(query_times, dtype=float)
    if freeze_after is not None and len(update_times):
        keep = update_times <= freeze_after
        update_times, tau, nu = update_times[keep], tau[keep], nu[keep]
    if len(update_times) == 0:
        return np.zeros_like(query_times)

    idx = np.searchsorted(update_times, query_times, side="right") - 1
    has_update = idx >= 0
    idx = np.clip(idx, 0, None)
    estimate = tau[idx] + nu[idx] * (query_times - update_times[idx])
    return np.where(has_update, estimate, 0.0)


def cramer_rao_endpoint_sigma(jitter_sigma, detections):
    """
    Lower bound on the timing-error standard deviation at the end of a
    uniformly spaced sync preamble with `detections` detected photons
    (least-squares line fit evaluated at the last sample): sigma*sqrt(4/n).
    """
    n = np.asarray(detections, dtype=float)
    return jitter_sigma * np.sqrt((4 * n - 2) / (n * (n + 1)))
