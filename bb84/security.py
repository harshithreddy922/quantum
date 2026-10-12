"""
Security bounds used by the research simulation.

All key lengths are computed from quantities Alice and Bob can actually
observe (the QBER measured on a random test subset), never from Eve's true
interception rate, which the legitimate parties cannot know.

References
----------
- P. W. Shor and J. Preskill, PRL 85, 441 (2000)              (asymptotic rate)
- M. Tomamichel, C. C. W. Lim, N. Gisin, R. Renner,
  Nat. Commun. 3, 634 (2012)                                   (finite-key bound)
- S. Pirandola, R. Laurenza, C. Ottaviani, L. Banchi,
  Nat. Commun. 8, 15043 (2017)                                 (PLOB bound)
"""

import math

import numpy as np


QBER_TOLERANCE = 0.11          # abort threshold on the tested QBER
EC_EFFICIENCY = 1.16           # error-correction inefficiency f >= 1
EPS_SEC = 1e-10                # secrecy parameter
EPS_COR = 1e-15                # correctness parameter


def binary_entropy(p):
    """h(p) in bits; works on scalars and numpy arrays."""
    p = np.clip(np.asarray(p, dtype=float), 1e-15, 1 - 1e-15)
    h = -p * np.log2(p) - (1 - p) * np.log2(1 - p)
    return h if h.ndim else float(h)


def statistical_fluctuation(n, k, eps_sec=EPS_SEC):
    """
    Width mu of the confidence interval that bounds the phase-error rate on
    the n key bits given the error rate observed on k test bits
    (Tomamichel et al. 2012, Eq. 2).
    """
    if n <= 0 or k <= 0:
        return math.inf
    return math.sqrt((n + k) / (n * k) * (k + 1) / k * math.log(2 / eps_sec))


def finite_key_length(
    n_key,
    k_test,
    qber_test,
    f_ec=EC_EFFICIENCY,
    eps_sec=EPS_SEC,
    eps_cor=EPS_COR,
    qber_tolerance=QBER_TOLERANCE,
):
    """
    Secure key length (bits) extractable from n_key sifted bits after k_test
    bits were disclosed to estimate the QBER.

        l = n [1 - h(Q + mu)] - leak_EC - log2(2 / (eps_sec^2 eps_cor))

    Returns 0 when the protocol aborts (tested QBER above tolerance) or when
    the bound is not positive.
    """
    if n_key <= 0 or k_test <= 0 or qber_test > qber_tolerance:
        return 0
    mu = statistical_fluctuation(n_key, k_test, eps_sec)
    phase_error = min(0.5, qber_test + mu)
    leak_ec = f_ec * n_key * binary_entropy(qber_test)
    length = (
        n_key * (1 - binary_entropy(phase_error))
        - leak_ec
        - math.log2(2 / (eps_sec ** 2 * eps_cor))
    )
    return max(0, int(math.floor(length)))


def asymptotic_secret_fraction(qber, f_ec=EC_EFFICIENCY):
    """Shor-Preskill secret fraction 1 - h(Q) - f h(Q), clipped at zero."""
    fraction = 1 - binary_entropy(qber) - f_ec * binary_entropy(qber)
    return np.maximum(0.0, fraction)


def plob_bound(transmittance):
    """Repeaterless secret-key capacity -log2(1 - eta) in bits per pulse."""
    eta = np.clip(np.asarray(transmittance, dtype=float), 0, 1 - 1e-15)
    return -np.log2(1 - eta)


def wilson_interval(successes, trials, z=1.96):
    """Wilson score interval for a binomial proportion."""
    if trials == 0:
        return 0.0, 0.0, 1.0
    p = successes / trials
    denom = 1 + z ** 2 / trials
    centre = (p + z ** 2 / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + z ** 2 / (4 * trials ** 2)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


# ---------------------------------------------------------------------------
# Decoy-state BB84 with weak coherent pulses
# ---------------------------------------------------------------------------
#
# C. C. W. Lim, M. Curty, N. Walenta, F. Xu, H. Zbinden,
# "Concise security bounds for practical decoy-state quantum key
# distribution", Phys. Rev. A 89, 022307 (2014).
#
# Three intensities mu1 > mu2 + mu3, mu2 > mu3 >= 0, chosen with
# probabilities p1, p2, p3. Key from Z-basis detections, phase error
# estimated from X-basis detections (biased basis choice).


def _tau(n, intensities, probabilities):
    return sum(math.exp(-k) * k ** n * p / math.factorial(n) for k, p in zip(intensities, probabilities))


def decoy_key_components(
    n_z,
    m_z,
    n_x,
    m_x,
    intensities,
    probabilities,
    f_ec=EC_EFFICIENCY,
    eps_sec=EPS_SEC,
    eps_cor=EPS_COR,
    finite=True,
):
    """
    Secret key length of decoy-state BB84 (Lim et al. 2014, Eqs. 2-6).

    n_z, m_z: Z-basis detections and errors per intensity (3 entries each);
    n_x, m_x: the same for the X basis. With finite=False the statistical
    fluctuation terms and the fixed composable cost are dropped, giving the
    asymptotic estimate from the same counts.

    Returns a dict with the key length and its budget:
    s_z0, s_z1 (vacuum and single-photon detection bounds), phase_error,
    leak_ec, pa_bits (= s_z1 h(phase_error)), fixed_cost, length.
    """
    mu1, mu2, mu3 = intensities
    p = probabilities
    n_z_total, m_x_total = sum(n_z), sum(m_x)
    n_x_total = sum(n_x)
    out = {"s_z0": 0.0, "s_z1": 0.0, "phase_error": 0.5, "leak_ec": 0.0, "pa_bits": 0.0,
           "fixed_cost": 0.0, "length": 0, "length_raw": 0.0, "n_z": n_z_total}
    if n_z_total <= 0 or n_x_total <= 0:
        return out

    ln_term = math.log(21 / eps_sec)
    delta_z = math.sqrt(n_z_total / 2 * ln_term) if finite else 0.0
    delta_x = math.sqrt(n_x_total / 2 * ln_term) if finite else 0.0
    delta_mx = math.sqrt(max(m_x_total, 0) / 2 * ln_term) if finite else 0.0

    def bound(counts, delta, sign):
        return [math.exp(k) / pk * (c + sign * delta) for k, pk, c in zip(intensities, p, counts)]

    tau0, tau1 = _tau(0, intensities, p), _tau(1, intensities, p)

    def vacuum_and_single(counts, delta):
        minus, plus = bound(counts, delta, -1), bound(counts, delta, +1)
        s0 = tau0 * (mu2 * minus[2] - mu3 * plus[1]) / (mu2 - mu3)
        s0 = max(0.0, s0)
        s1 = tau1 * mu1 * (minus[1] - plus[2] - (mu2 ** 2 - mu3 ** 2) / mu1 ** 2 * (plus[0] - s0 / tau0)) / (
            mu1 * (mu2 - mu3) - mu2 ** 2 + mu3 ** 2)
        return s0, max(0.0, s1)

    s_z0, s_z1 = vacuum_and_single(n_z, delta_z)
    _, s_x1 = vacuum_and_single(n_x, delta_x)
    m_plus, m_minus = bound(m_x, delta_mx, +1), bound(m_x, delta_mx, -1)
    v_x1 = max(0.0, tau1 * (m_plus[1] - m_minus[2]) / (mu2 - mu3))

    if s_z1 <= 0 or s_x1 <= 0:
        phase = 0.5
    else:
        ratio = min(0.5, v_x1 / s_x1)
        phase = ratio
        if finite and 0 < ratio < 0.5:
            c, d = s_z1, s_x1
            arg = (c + d) / (c * d * (1 - ratio) * ratio) * 21 ** 2 / eps_sec ** 2
            phase += math.sqrt((c + d) * (1 - ratio) * ratio / (c * d * math.log(2)) * math.log2(arg))
        phase = min(0.5, phase)

    e_z = sum(m_z) / n_z_total
    leak = f_ec * n_z_total * binary_entropy(e_z)
    fixed = (6 * math.log2(21 / eps_sec) + math.log2(2 / eps_cor)) if finite else 0.0
    pa = s_z1 * binary_entropy(phase)
    length = s_z0 + s_z1 - pa - leak - fixed
    out.update(s_z0=s_z0, s_z1=s_z1, phase_error=phase, leak_ec=leak, pa_bits=pa, fixed_cost=fixed,
               length=max(0, int(math.floor(length))), length_raw=length)
    return out
