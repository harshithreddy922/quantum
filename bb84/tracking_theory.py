"""
Analytical model of the Kalman timing tracker in bb84/qcs_tracking.py.

The tracker estimates Bob's timing error tau and frequency error nu from
pilot detections. Between detections the oscillator's frequency performs a
random walk with diffusion q (ns^-1), and each detection measures tau with
Gaussian noise of variance r = sigma_jitter^2.

Pilot detections arrive as a Poisson process with mean spacing

    Delta = pilot_spacing * T_slot / p_detect,

where p_detect is the chance that one pilot pulse is detected.

Three results follow:

1. Steady-state covariance: iterating the Kalman predict/update equations
   with a fixed spacing Delta gives the posterior covariance P = [[P11, P12],
   [P12, P22]] right after an update.
2. RMS gate error: between updates the error variance grows as
       V(t) = P11 + 2 t P12 + t^2 P22 + q t^3 / 3.
   Averaging V over time inside exponentially distributed gaps g ~ Exp(Delta)
   gives the mean-square gate error
       MS = P11 + 2 P12 Delta + 2 P22 Delta^2 + 2 q Delta^3.
3. Lock loss, from two hazards:
   - overrun: if the error at the end of a gap exceeds the pilot
     acquisition half-window h (= T_slot / 2), the next pilot is not seen;
     per gap p_gap = E_g[ 2 (1 - Phi(h / sqrt(V(g)))) ], g ~ Exp(Delta);
   - dark capture: a dark count accepted by the 3-sigma innovation gate
     while V > r (the filter trusts the tag more than its prediction)
     pulls the estimate onto a false time.
   Over a segment of duration T, P_lost = 1 - exp(-(rate_overrun +
   rate_dark) T).
"""

import math

import numpy as np
from scipy.special import ndtr


def steady_state_covariance(q, r, delta, iterations=5000, tol=1e-12):
    """Posterior covariance (P11, P12, P22) right after a steady-state update."""
    p11, p12, p22 = 1e6 * r, 0.0, 1e-8
    for _ in range(iterations):
        a11 = p11 + 2 * delta * p12 + delta ** 2 * p22 + q * delta ** 3 / 3
        a12 = p12 + delta * p22 + q * delta ** 2 / 2
        a22 = p22 + q * delta
        s = a11 + r
        k1, k2 = a11 / s, a12 / s
        n11, n12, n22 = (1 - k1) * a11, (1 - k1) * a12, a22 - k2 * a12
        if abs(n11 - p11) <= tol * max(n11, 1e-30) and abs(n22 - p22) <= tol * max(n22, 1e-30):
            return n11, n12, n22
        p11, p12, p22 = n11, n12, n22
    return p11, p12, p22


def error_variance(posterior, q, t):
    p11, p12, p22 = posterior
    return p11 + 2 * t * p12 + t ** 2 * p22 + q * t ** 3 / 3


def rms_gate_error(q, r, delta):
    """RMS gate timing error (ns) in steady state, averaged over Poisson gaps."""
    p11, p12, p22 = steady_state_covariance(q, r, delta)
    return math.sqrt(p11 + 2 * p12 * delta + 2 * p22 * delta ** 2 + 2 * q * delta ** 3)


def _integrate(values, grid):
    trapezoid = getattr(np, "trapezoid", None) or np.trapz
    return float(trapezoid(values, grid))


def lock_loss_probability(q, r, delta, half_window, duration, pilot_period=None, dark_per_pilot=0.0,
                          gate_sigma=3.0, points=4000):
    """
    Probability that the tracker loses lock within `duration` ns.

    Two mechanisms, treated as independent Poisson hazards:
      * overrun - a long gap lets the error leave the +-half_window
        acquisition window, so the next pilot is not seen;
      * dark capture - a dark count inside the innovation gate is accepted
        while the prediction is less certain than one measurement (V > r);
        the filter then follows the false time tag.
    pilot_period: ns between pilot slots; dark_per_pilot: dark-count
    probability in one pilot acquisition window (2 * half_window wide).
    """
    posterior = steady_state_covariance(q, r, delta)
    t = np.linspace(0, 40 * delta, points)
    survival = np.exp(-t / delta)
    var = np.maximum(error_variance(posterior, q, t), 1e-30)

    # Overrun hazard per gap, averaged over g ~ Exp(delta).
    miss = 2 * (1 - ndtr(half_window / np.sqrt(var)))
    p_gap = min(max(_integrate(miss * survival / delta, t), 0.0), 1.0)
    rate_overrun = -math.log1p(-p_gap) / delta if p_gap < 1 else math.inf

    # Dark-capture hazard: darks arrive every pilot slot with probability
    # dark_per_pilot, uniformly over the window; the gate accepts a fraction
    # gate_sigma * sqrt(V + r) / half_window of them.
    rate_dark = 0.0
    if pilot_period and dark_per_pilot > 0:
        accepted = np.minimum(1.0, gate_sigma * np.sqrt(var + r) / half_window)
        harmful = (var > r).astype(float)
        mean_harmful = _integrate(accepted * harmful * survival, t) / delta
        rate_dark = dark_per_pilot / pilot_period * mean_harmful

    total = rate_overrun + rate_dark
    return 1.0 if math.isinf(total) else 1 - math.exp(-total * duration)


def pilot_gap_ns(pilot_spacing_slots, slot_ns, p_detect):
    return pilot_spacing_slots * slot_ns / p_detect


def wander_to_q(wander_ppm_per_sqrt_ms):
    """Random-walk frequency diffusion q (ns^-1) from ppm per sqrt(ms)."""
    return (wander_ppm_per_sqrt_ms * 1e-6) ** 2 / 1e6


def minimum_pilot_fraction(q, r, slot_ns, p_detect, half_window, duration, dark_per_pilot=0.0,
                           target=0.01, spacings=None):
    """Smallest pilot fraction (1 / spacing) keeping P_lost <= target."""
    if spacings is None:
        spacings = np.unique(np.round(np.logspace(0, 4, 200)).astype(int))
    best = None
    for spacing in sorted(spacings, reverse=True):
        delta = pilot_gap_ns(spacing, slot_ns, p_detect)
        if lock_loss_probability(q, r, delta, half_window, duration, pilot_period=spacing * slot_ns,
                                 dark_per_pilot=dark_per_pilot) <= target:
            best = 1.0 / spacing
            break
    return best
