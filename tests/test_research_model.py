"""Checks that the research model agrees with closed-form expectations."""

import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import research_simulation as rs  # noqa: E402
from bb84.qcs_tracking import acquire_preamble  # noqa: E402
from bb84.security import (  # noqa: E402
    asymptotic_secret_fraction,
    binary_entropy,
    finite_key_length,
    wilson_interval,
)
from bb84.timing_attacks import eve_information  # noqa: E402


def test_binary_entropy_values():
    assert binary_entropy(0.5) == pytest.approx(1.0)
    assert binary_entropy(0.11) == pytest.approx(0.4999, abs=1e-3)


def test_shor_preskill_threshold():
    # 1 - 2h(Q) vanishes near Q = 11 %
    assert asymptotic_secret_fraction(0.11, f_ec=1.0) == pytest.approx(0.0, abs=2e-3)


def test_finite_key_grows_with_block_and_aborts_above_tolerance():
    small = finite_key_length(10_000, 1_000, 0.02)
    large = finite_key_length(1_000_000, 100_000, 0.02)
    assert large / 1_000_000 > small / 10_000
    assert finite_key_length(1_000_000, 100_000, 0.12) == 0


def test_wilson_interval_contains_estimate():
    p, lo, hi = wilson_interval(0, 50)
    assert p == 0 and lo == 0 and 0 < hi < 0.1


def test_signal_error_is_xor_of_noise_and_eve():
    cfg = rs.ResearchConfig(pauli_error_rate=0.03, eve_rate=1.0)
    e_ch, e_eve = 0.02, 0.25
    assert rs.signal_error_probability(cfg) == pytest.approx(e_ch * (1 - e_eve) + e_eve * (1 - e_ch))


@pytest.mark.parametrize("eve", [0.0, 0.3])
def test_monte_carlo_qber_matches_closed_form(eve):
    cfg = rs.ResearchConfig(sync_strategy="ideal", num_slots=10 ** 6, eve_rate=eve)
    results = rs.run_trials(cfg, 20, rs.make_rng("test_qber", eve))
    measured = np.mean([r.qber for r in results])
    assert measured == pytest.approx(rs.expected_qber(cfg), abs=2e-3)


def test_ideal_capture_matches_erf():
    cfg = rs.ResearchConfig(sync_strategy="ideal")
    result = rs.simulate_trial(cfg, rs.make_rng("test_capture"))
    expected = math.erf(cfg.detector_window_ns / 2 / (cfg.timing_jitter_ns * math.sqrt(2)))
    assert result.timing_capture_rate == pytest.approx(expected, rel=1e-9)


def test_no_sync_fails_and_qcs_tracking_recovers_timing():
    cfg = rs.ResearchConfig()
    none = rs.simulate_trial(replace(cfg, sync_strategy="none"), rs.make_rng("t1"))
    qcs = rs.simulate_trial(replace(cfg, sync_strategy="qcs_tracking"), rs.make_rng("t2"))
    assert none.timing_capture_rate < 0.05
    assert qcs.timing_capture_rate > 0.98
    assert qcs.sync_overhead > 0


def test_acquisition_tolerates_dark_counts():
    rng = np.random.default_rng(1)
    offset, drift, sigma, spacing = 7.0, 35e-6, 0.35, 50.0
    t_signal = np.sort(rng.choice(np.arange(4000) * spacing, 120, replace=False))
    z_signal = offset + drift * t_signal + rng.normal(0, sigma, len(t_signal))
    t_dark = np.round(rng.uniform(0, 4000 * spacing, 60) / spacing) * spacing
    z_dark = rng.uniform(-spacing / 2, spacing / 2, len(t_dark))
    t = np.concatenate([t_signal, t_dark])
    z = np.concatenate([z_signal, z_dark])
    order = np.argsort(t)
    state = acquire_preamble(t[order], z[order], sigma, wrap_period=spacing, max_drift=100e-6)
    t_ref, tau, nu = state[:3]
    assert tau == pytest.approx(offset + drift * t_ref, abs=0.2)
    assert nu == pytest.approx(drift, abs=1e-6)


def test_results_are_reproducible():
    cfg = rs.ResearchConfig()
    a = rs.simulate_trial(cfg, rs.make_rng("repro"))
    b = rs.simulate_trial(cfg, rs.make_rng("repro"))
    assert a == b


def test_time_shift_leaks_nothing_at_gate_centre():
    info, rate = eve_information(np.array([0.0, 1.0]), 0.4, 2.0, 0.35)
    assert info[0] == pytest.approx(0.0, abs=1e-12)
    assert info[1] > 0.1 and rate[1] < 1
