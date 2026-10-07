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
