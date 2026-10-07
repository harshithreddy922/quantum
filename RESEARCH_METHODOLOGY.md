# Research Methodology

This document describes the simulation model behind the paper figures, the
assumptions a reviewer will ask about, and how to reproduce every result.
Figure-by-figure captions and headline numbers are in
[`research_outputs/FIGURES.md`](research_outputs/FIGURES.md).

## 1. Contribution

The study evaluates **qubit-based clock synchronization (QCS) for BB84**:
Bob recovers Alice's clock from the detection times of single-photon sync
pulses that travel over the quantum channel itself, instead of relying on a
separate classical timing link. The contributions are:

1. A photon-limited synchronization model. Sync photons suffer the same fibre
   loss, detector inefficiency and dark counts as key photons, and the slots
   they occupy are charged to the key rate.
2. A two-stage estimator: drift-search (2-D cross-correlation) acquisition on a
   sparse preamble, followed by Kalman tracking on interleaved pilot pulses.
   Its accuracy is validated against the Cramér–Rao bound (Fig. 2c).
3. A comparison against realistic baselines (no synchronization, a classical
   timing reference with sub-ns residual error, preamble-only QCS, and perfect
   synchronization) under clock offset, drift, frequency wander, jitter, gate
   width, distance and block size.
4. Composable finite-key rates (Tomamichel et al. 2012) computed only from
   quantities Alice and Bob observe.
5. A security analysis of the timing layer: a delay attack on a classical
   reference exploits detector-efficiency mismatch without raising the QBER,
   while QCS absorbs uniform delays and its timing residuals expose random
   time-shift attacks (Fig. 13).

### What "QCS" means here

The synchronization signal is a stream of single photons on the quantum
channel, as in Qubit4Sync (Calderaro et al. 2020). It is not
entanglement-based clock synchronization (Jozsa et al. 2000; Valencia et al.
2004). The paper should say this explicitly and cite both lines of work. An
entanglement-based variant is listed under future work.

## 2. Model

### 2.1 Timing layer

Alice emits one pulse per slot (T = 10 ns). Relative to Bob's nominal gate
schedule, the photon in the slot sent at time t arrives with error

    e(t) = offset + drift · t + w(t) + ε,      ε ~ N(0, σ²)

where w(t) is integrated random-walk frequency noise (oscillator wander).
Bob opens a gate of width W at his estimate ê(t). The timing capture
probability for a slot is

    P_cap = Φ((W/2 − d)/σ) − Φ((−W/2 − d)/σ),   d = e(t) − ê(t) − ε

Synchronization strategies (`research_simulation.SYNC_STRATEGIES`):

| Strategy | Gate estimate ê(t) | Overhead |
|---|---|---|
| No synchronization | 0 (nominal schedule) | none |
| Classical reference | true error + constant residual ~ N(0, 0.5 ns) per block | none (separate link) |
| QCS, preamble only | acquisition fit, extrapolated for the whole block | preamble slots |
| QCS, preamble + tracking | acquisition, then Kalman updates from pilots | preamble + 1 % pilot slots |
| Perfect synchronization | true error | none |

**Acquisition.** The preamble sends one pulse every 5 slots (50 ns) until
about 64 photons are expected to be detected, so acquisition time grows as
1/η with distance (capped at 20 % of the block). Bob free-runs his time
tagger, so each tag is known only modulo 50 ns, and dark counts arrive
throughout. A grid search over drift (±100 ppm, step σ/span) histograms the
de-rotated tags; the tallest peak gives coarse offset and drift. The inliers
are then refined by least squares (`bb84/qcs_tracking.acquire_preamble`).

**Tracking.** Pilot pulses occupy every 100th slot, at positions drawn from
pre-shared secret randomness so Eve cannot single them out. (The simulation
spaces them evenly, which has the same timing statistics.) Each pilot click
updates a two-state Kalman filter (timing error, frequency error). The process
noise is matched to the oscillator wander, and a 3σ innovation gate rejects
dark counts (`run_timing_tracker`). Gates use only past updates (causal).

### 2.2 Physical layer

| Parameter | Default | Note |
|---|---|---|
| Fibre loss | 0.2 dB/km | standard SMF-28 at 1550 nm |
| Detector efficiency | 0.6 | per detector |
| Dark-count rate | 10⁴ Hz per detector | dark probability = 1 − exp(−2·R·W): scales with gate width |
| Channel noise | Pauli p = 0.03 | X, Y or Z applied with probability p; bit error 2p/3, as in `main.py` |
| Jitter σ | 0.35 ns | source + fibre + detector |
| Gate width W | 2 ns | |
| Clock offset / drift | 4 ns / 20 ppm | crystal-oscillator class |
| Oscillator wander | 0.01 ppm/√ms | 0.1–0.2 ppm/√ms in stress tests |
| Block size N | 10⁵–10⁸ slots | stated per figure |

Signal errors combine channel noise and Eve independently (XOR):
e = e_ch(1 − e_E) + e_E(1 − e_ch), with e_E = f/4 for intercept-resend on a
fraction f of pulses. Dark-count clicks and double clicks are assigned a
random bit (error ½). Sync photons are simulated individually. Key-slot clicks
are drawn from a binomial with the block's mean capture probability, which is
exact in expectation and makes 10⁸-slot blocks tractable.

### 2.3 Protocol and security

1. Sifting keeps matching bases (probability ½).
2. A random 10 % of sifted bits is disclosed to estimate the QBER Q_test.
3. The protocol aborts if Q_test > 11 %.
4. The secure length follows Tomamichel et al. (2012):

       ℓ = n[1 − h(Q_test + μ)] − f·n·h(Q_test) − log₂(2/(ε_sec² ε_cor))

   with f = 1.16, ε_sec = 10⁻¹⁰, ε_cor = 10⁻¹⁵ and μ the statistical
   fluctuation term (`bb84/security.py`).
5. Eve's true interception rate is never used in the key-length calculation.

The secret key rate is ℓ divided by **all** slots in the block, including sync
overhead. Asymptotic Shor–Preskill rates and the PLOB bound are plotted for
reference.

### 2.4 Statistics and reproducibility

- Every sweep point has its own random generator, seeded from a master seed
  (20261007) and the experiment name. Results do not depend on run order or on
  the number of worker processes.
- Error bars are 95 % confidence intervals of the mean (1.96·s/√n).
  Acceptance probabilities use Wilson intervals.
- Trial counts: 50 for timing sweeps, 200 for acceptance, and 10–20 for
  10⁸-slot blocks (heatmaps: 4 per cell).
- `tests/test_research_model.py` checks the Monte Carlo against closed forms
  (QBER, capture), checks acquisition under dark counts, and checks
  reproducibility.

## 3. Figures

| # | File | Question it answers |
|---|---|---|
| 1 | `fig01_system_model` | System model and timing diagram |
| 2 | `fig02_model_validation` | Does the simulator match theory (QBER, click probability, Cramér–Rao)? |
| 3 | `fig03_qber_security` | How do noise and intercept-resend move the QBER? |
| 4 | `fig04_acceptance` | When is a key produced, and how does block size change that? |
| 5 | `fig05_timing_impairments` | Robustness to offset, drift and jitter versus the baselines |
| 6 | `fig06_window_tradeoff` | Optimal gate width once dark counts scale with W |
| 7 | `fig07_sync_overhead` | Cost of pilots: timing accuracy versus key rate |
| 8 | `fig08_distance` | Finite-key rate versus distance, with PLOB and asymptotic references |
| 9 | `fig09_heatmaps` | Sensitivity: (W, σ) and (distance, pilot overhead) |
| 10 | `fig10_long_run` | Stability over a 1 s block with oscillator wander |
| 11 | `fig11_finite_key` | Convergence to the asymptotic rate with block size |
| 12 | `fig12_key_budget` | Where the sifted bits go (test, EC, PA, finite-size) |
| 13 | `fig13_timing_attacks` | Delay and time-shift attacks on the sync layer |
| — | `table_operating_points` | Numbers for the comparison table in the paper |

Every figure is saved as PDF (vector, for LaTeX) and 300 dpi PNG, next to a
CSV of the plotted values. Figures carry no titles; captions belong in the
manuscript.

## 4. Limitations to state in the paper

- This is a simulation study, not an optical experiment.
- The source is an ideal single-photon source. A weak-coherent-pulse
  implementation needs decoy states (Hwang 2003; Lo, Ma, Chen 2005) and
  decoy-state finite-key bounds (Lim et al. 2014). This is future work.
- Afterpulsing, detector dead time and polarization drift are not modelled.
- The Kalman tracker has no lock-loss detection or re-acquisition. Under heavy
  oscillator wander at long range it can lose lock (Fig. 10b).
- The classical-reference baseline is reduced to a constant residual error per
  block. Its σ (0.5 ns) is a parameter. Sub-100 ps systems such as White Rabbit
  would close much of the gap shown here.
- The time-shift analysis assumes a rectangular-gate efficiency mismatch
  blurred by Gaussian jitter. Real detectors have smoother mismatch curves.
- The intercept-resend attack is used for QBER behaviour only. Security of the
  key length comes from the finite-key bound, which covers general attacks on
  the BB84 single-photon source assumed here.

## 5. Reproduce

```bash
pip install -r requirements.txt
python -m pytest -q tests                 # model validation
python generate_graphs.py --quick         # draft figures in ~1 min
python generate_graphs.py                 # paper figures (tens of minutes on 4 cores)
python generate_graphs.py --only fig08    # one figure
```

## 6. References (verify page numbers before submission)

- C. H. Bennett, G. Brassard, Proc. IEEE ICCSSP, 175 (1984).
- P. W. Shor, J. Preskill, Phys. Rev. Lett. 85, 441 (2000).
- D. Gottesman, H.-K. Lo, N. Lütkenhaus, J. Preskill, Quantum Inf. Comput. 4, 325 (2004).
- M. Tomamichel, C. C. W. Lim, N. Gisin, R. Renner, Nat. Commun. 3, 634 (2012).
- C. C. W. Lim, M. Curty, N. Walenta, F. Xu, H. Zbinden, Phys. Rev. A 89, 022307 (2014).
- S. Pirandola, R. Laurenza, C. Ottaviani, L. Banchi, Nat. Commun. 8, 15043 (2017).
- L. Calderaro et al., Phys. Rev. Applied 13, 054041 (2020) — Qubit4Sync.
- R. Jozsa, D. S. Abrams, J. P. Dowling, C. P. Williams, Phys. Rev. Lett. 85, 2010 (2000).
- V. Giovannetti, S. Lloyd, L. Maccone, Nature 412, 417 (2001).
- A. Valencia, G. Scarcelli, Y. Shih, Appl. Phys. Lett. 85, 2655 (2004).
- V. Makarov, A. Anisimov, J. Skaar, Phys. Rev. A 74, 022313 (2006).
- B. Qi, C.-H. F. Fung, H.-K. Lo, X. Ma, Quantum Inf. Comput. 7, 73 (2007).
- Y. Zhao, C.-H. F. Fung, B. Qi, C. Chen, H.-K. Lo, Phys. Rev. A 78, 042333 (2008).
- W.-Y. Hwang, Phys. Rev. Lett. 91, 057901 (2003); H.-K. Lo, X. Ma, K. Chen, Phys. Rev. Lett. 94, 230504 (2005).
- M. Lipiński et al., "White Rabbit: a PTP application for robust sub-nanosecond synchronization", ISPCS (2011).

## Suggested title

**Photon-Limited Clock Synchronization for BB84: Finite-Key Performance and
Timing-Layer Security under Drift, Jitter and Time-Shift Attacks**
