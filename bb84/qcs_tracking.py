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

    # Work in time relative to the first tag, so the unwrapped line is
    # anchored inside this batch (not at t = 0 of the whole block).
    rel = times - times[0]
    span = max(rel[-1], 1.0)
    step = max(jitter_sigma / span, 1e-9)
    candidates = np.arange(-max_drift, max_drift + step, step)
    bin_width = 2 * jitter_sigma
    n_bins = max(1, int(round(wrap_period / bin_width)))

    best_count, best_nu, best_peak = -1, 0.0, 0.0
    for chunk in np.array_split(candidates, max(1, len(candidates) // 512)):
        r = _wrap(z[None, :] - chunk[:, None] * rel[None, :], wrap_period)
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

    r = _wrap(z - best_nu * rel - best_peak, wrap_period)
    inliers = np.abs(r) < max(3 * jitter_sigma, bin_width)
    if inliers.sum() < 2:
        return None
    x = rel[inliers]
    y = best_nu * x + best_peak + r[inliers]

    t_ref = times[-1]
    t_ref_rel = rel[-1]
    x_mean = x.mean()
    x_c = x - x_mean
    sxx = float((x_c ** 2).sum())
    if sxx == 0:
        return None
    nu = float((x_c * (y - y.mean())).sum() / sxx)
    tau = float(y.mean() + nu * (t_ref_rel - x_mean))

    var = jitter_sigma ** 2
    lever = t_ref_rel - x_mean
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


def run_batch_resync(
    event_times,
    true_error,
    signal_present,
    jitter,
    dark_present,
    dark_uniform,
    acquisition_half_width,
    jitter_sigma,
    initial_state,
    batch_detections=32,
    max_residual_drift=100e-6,
):
    """
    Baseline representative of published qubit-based synchronization
    (cross-correlation / batch estimation, e.g. Calderaro et al. 2020;
    Cochran and Gauthier 2021): pilot clicks are collected in batches of
    `batch_detections`, the residual offset and drift of each batch are
    found with the same robust cross-correlation fit used for acquisition,
    and that estimate is held (extrapolated linearly) until the next batch
    completes. No recursive filtering between batches.

    Same inputs as run_timing_tracker; returns (update_times, tau, nu).
    """
    t_ref, tau_ref, nu_ref = initial_state[0], initial_state[1], initial_state[2]
    out_t, out_tau, out_nu = [t_ref], [tau_ref], [nu_ref]
    batch_t, batch_r = [], []

    for k in range(len(event_times)):
        t = event_times[k]
        pred = tau_ref + nu_ref * (t - t_ref)
        half = acquisition_half_width[k]
        z = None
        if signal_present[k]:
            z_signal = true_error[k] + jitter[k]
            if abs(z_signal - pred) <= half:
                z = z_signal
        if dark_present[k]:
            z_dark = pred + (2 * dark_uniform[k] - 1) * half
            if z is None or z_dark < z:
                z = z_dark
        if z is None:
            continue
        batch_t.append(t)
        batch_r.append(z - pred)
        if len(batch_t) < batch_detections:
            continue

        fit = acquire_preamble(np.array(batch_t), np.array(batch_r), jitter_sigma,
                               wrap_period=2 * half, max_drift=max_residual_drift)
        if fit is not None:
            t_new, tau_res, nu_res = fit[0], fit[1], fit[2]
            tau_ref = tau_ref + nu_ref * (t_new - t_ref) + tau_res
            nu_ref = nu_ref + nu_res
            t_ref = t_new
            out_t.append(t_ref)
            out_tau.append(tau_ref)
            out_nu.append(nu_ref)
        batch_t, batch_r = [], []

    return np.array(out_t), np.array(out_tau), np.array(out_nu)


def _observed_residuals(true_error, signal_present, jitter, dark_present, dark_uniform, half, pred):
    """
    What Bob's time tagger reports for a set of events, relative to his
    prediction `pred`: the photon tag when it falls inside +-half of the
    prediction, else (or if earlier) a dark-count tag uniform over the
    window. Returns (residual, seen) arrays.
    """
    z_sig = true_error + jitter - pred
    sig_seen = signal_present & (np.abs(z_sig) <= half)
    z_dark = (2 * dark_uniform - 1) * half
    use_dark = dark_present & (~sig_seen | (z_dark < z_sig))
    residual = np.where(use_dark, z_dark, z_sig)
    return residual, sig_seen | use_dark


def run_chunked_tracker(
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
    max_chunks=40_000,
):
    """
    The Kalman tracker of run_timing_tracker for dense event streams
    (data-aided tracking on key-slot clicks, up to ~10^6 events per
    segment). Events are processed in consecutive groups of g events: each
    event is gated individually against the prediction, and the accepted
    innovations are applied as one measurement at their mean time with
    variance r / n_accepted. For a linear timing error this equals the
    sequential update up to process noise inside a group, which spans only
    a few microseconds at the event rates used.

    Same inputs and outputs as run_timing_tracker.
    """
    t_last, tau, nu, p11, p12, p22 = initial_state
    r = jitter_sigma ** 2
    q = process_noise_nu
    gate2 = INNOVATION_GATE_SIGMA ** 2
    n = len(event_times)
    g = max(1, -(-n // max_chunks))
    out_t, out_tau, out_nu = [t_last], [tau], [nu]

    for a in range(0, n, g):
        b = min(n, a + g)
        t = event_times[a:b]
        dt = t - t_last
        pred = tau + nu * dt
        p11p = p11 + 2 * dt * p12 + dt * dt * p22 + q * dt ** 3 / 3
        innovation, seen = _observed_residuals(
            true_error[a:b], signal_present[a:b], jitter[a:b], dark_present[a:b],
            dark_uniform[a:b], acquisition_half_width[a:b], pred)
        accept = seen & (innovation * innovation <= gate2 * (p11p + r))
        k = int(accept.sum())
        if k == 0:
            continue
        t_bar = float(t[accept].mean())
        e_bar = float(innovation[accept].mean())
        d = t_bar - t_last
        tau_p = tau + nu * d
        a11 = p11 + 2 * d * p12 + d * d * p22 + q * d ** 3 / 3
        a12 = p12 + d * p22 + q * d ** 2 / 2
        a22 = p22 + q * d
        s = a11 + r / k
        k1, k2 = a11 / s, a12 / s
        tau = tau_p + k1 * e_bar
        nu = nu + k2 * e_bar
        p11, p12, p22 = (1 - k1) * a11, (1 - k1) * a12, a22 - k2 * a12
        t_last = t_bar
        out_t.append(t_last)
        out_tau.append(tau)
        out_nu.append(nu)

    return np.array(out_t), np.array(out_tau), np.array(out_nu)


def run_histogram_resync(
    event_times,
    true_error,
    signal_present,
    jitter,
    dark_present,
    dark_uniform,
    acquisition_half_width,
    jitter_sigma,
    initial_state,
    window_ns,
    period_ns,
    start_counts=10,
):
    """
    Histogram-based synchronization in the style of Millet et al.,
    arXiv:2605.26705 (2026): Bob folds his detection time tags over the
    clock period, acquires two consecutive histograms of duration
    window_ns, estimates the residual drift from the phase difference of
    their circular means and the residual offset from the second one,
    corrects his clock once, and repeats with two new histograms. Dark
    counts enter as a flat background. No state or uncertainty is carried
    between corrections beyond the corrected clock itself. Histograms start
    short (about start_counts clicks) and grow 4x every three corrections up
    to window_ns, as in the paper's convergence schedule.

    Same event inputs as run_timing_tracker; returns (update_times, tau, nu).
    """
    t_ref, tau_ref, nu_ref = initial_state[0], initial_state[1], initial_state[2]
    out_t, out_tau, out_nu = [t_ref], [tau_ref], [nu_ref]
    if len(event_times) == 0:
        return np.array(out_t), np.array(out_tau), np.array(out_nu)
    two_pi = 2 * np.pi
    start = t_ref
    end_time = event_times[-1]
    # Convergence schedule of Millet et al.: start with histograms of about
    # start_counts clicks and quadruple the duration every three corrections
    # until window_ns is reached.
    rate = len(event_times) / max(end_time - start, 1.0)
    window = min(window_ns, start_counts / max(rate, 1e-12))
    iteration = 0

    while start + window < end_time:
        lo = np.searchsorted(event_times, start, side="left")
        mid = np.searchsorted(event_times, start + window, side="left")
        hi = np.searchsorted(event_times, start + 2 * window, side="left")
        t_new = start + 2 * window
        if mid > lo and hi > mid:
            t = event_times[lo:hi]
            pred = tau_ref + nu_ref * (t - t_ref)
            res, seen = _observed_residuals(
                true_error[lo:hi], signal_present[lo:hi], jitter[lo:hi], dark_present[lo:hi],
                dark_uniform[lo:hi], acquisition_half_width[lo:hi], pred)
            phase = np.exp(1j * two_pi * res / period_ns)
            first = seen & (t < start + window)
            second = seen & (t >= start + window)
            if first.any() and second.any():
                m1, m2 = phase[first].mean(), phase[second].mean()
                d_nu = period_ns / (two_pi * window) * np.angle(m2 * np.conj(m1))
                offset = period_ns / two_pi * np.angle(m2) + d_nu * window / 2
                tau_ref = tau_ref + nu_ref * (t_new - t_ref) + offset
                nu_ref = nu_ref + d_nu
                t_ref = t_new
                out_t.append(t_ref)
                out_tau.append(tau_ref)
                out_nu.append(nu_ref)
        start = t_new
        iteration += 1
        if iteration % 3 == 0:
            window = min(window_ns, 4 * window)

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
