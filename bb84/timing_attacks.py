"""
Timing side-channel attacks on the synchronization layer.

Bob's two detectors (D0 for bit 0, D1 for bit 1) have gates of width W
whose centres are offset by +-mismatch/2 relative to his synchronized gate
centre - a detector-efficiency mismatch in the time domain (Makarov,
Anisimov, Skaar, PRA 74, 022313 (2006)). A photon arriving at relative
time t is detected by D_b with probability

    eta_b(t) = Phi((c_b + W/2 - t) / sigma) - Phi((c_b - W/2 - t) / sigma)

If Eve can move photon arrivals away from the centre, a click becomes
correlated with the bit value without disturbing the QBER (time-shift
attack, Qi, Fung, Lo, Ma, QIC 7, 73 (2007)).

Two ways of moving arrivals are modelled:

* Reference-delay attack. With a classical timing reference Eve can delay
  the reference signal by delta; Bob's gates move but the photons do not.
  With QCS the reference is derived from the photons themselves, so a
  uniform delay is absorbed by the tracker and the relative shift is zero.
* Random time-shift attack. Eve shifts each photon by +s or -s at random.
  QCS cannot absorb this, but the arrival-time residuals that QCS already
  measures become wider; a variance test on them flags the attack.
"""

import math

import numpy as np
from scipy.special import ndtr, ndtri

from bb84.security import binary_entropy


def detector_efficiency(arrival, centre, window_ns, jitter_ns):
    half = window_ns / 2
    return ndtr((centre + half - arrival) / jitter_ns) - ndtr((centre - half - arrival) / jitter_ns)


def eve_information(shift_ns, mismatch_ns, window_ns, jitter_ns):
    """
    Eve's information (bits per sifted bit) when photons arrive shifted by
    shift_ns relative to Bob's gate centre, and the relative detection
    efficiency compared with an unshifted arrival.
    """
    shift = np.asarray(shift_ns, dtype=float)
    eta0 = detector_efficiency(shift, -mismatch_ns / 2, window_ns, jitter_ns)
    eta1 = detector_efficiency(shift, +mismatch_ns / 2, window_ns, jitter_ns)
    total = eta0 + eta1
    posterior = np.where(total > 0, eta1 / np.maximum(total, 1e-300), 0.5)
    information = 1 - binary_entropy(posterior)
    reference = 2 * detector_efficiency(0.0, mismatch_ns / 2, window_ns, jitter_ns)
    return information, total / reference


def _detected_residuals(rng, size, shift_ns, mismatch_ns, window_ns, jitter_ns):
    """Arrival-time residuals of detected photons (rejection sampling)."""
    out = []
    remaining = size
    while remaining > 0:
        batch = max(4 * remaining, 1024)
        bits = rng.integers(0, 2, batch)
        signs = rng.choice((-1.0, 1.0), batch)
        arrivals = signs * shift_ns + rng.normal(0, jitter_ns, batch)
        centres = (bits - 0.5) * mismatch_ns
        keep = np.abs(arrivals - centres) <= window_ns / 2
        out.append(arrivals[keep][:remaining])
        remaining -= len(out[-1])
    return np.concatenate(out)


def variance_monitor_power(
    shifts_ns,
    detections,
    mismatch_ns,
    window_ns,
    jitter_ns,
    false_alarm=1e-3,
    rng=None,
    moment_samples=400_000,
):
    """
    Probability that Bob's residual-variance test flags a random time-shift
    attack of magnitude s, using n detections at a fixed false-alarm rate.

    The sample variance of n residuals is approximately normal with mean
    sigma^2 and variance (mu4 - sigma^4) / n; the moments under H0 and H1 are
    estimated from a large sample of detected residuals.
    """
    rng = rng or np.random.default_rng(0)

    def moments(shift):
        r = _detected_residuals(rng, moment_samples, shift, mismatch_ns, window_ns, jitter_ns)
        r = r - r.mean()
        var = float(np.mean(r ** 2))
        return var, float(np.mean(r ** 4)) - var ** 2

    var0, spread0 = moments(0.0)
    z = float(ndtri(1 - false_alarm))
    power = np.zeros((len(detections), len(shifts_ns)))
    for j, shift in enumerate(shifts_ns):
        var1, spread1 = moments(shift) if shift > 0 else (var0, spread0)
        for i, n in enumerate(detections):
            threshold = var0 + z * math.sqrt(spread0 / n)
            power[i, j] = 1 - ndtr((threshold - var1) / math.sqrt(spread1 / n))
    return power
