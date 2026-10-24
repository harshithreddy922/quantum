# Research Methodology

This document describes the simulation model behind the paper figures, the
assumptions a reviewer will ask about, and how to reproduce every result.
Figure-by-figure captions and headline numbers are in
[`research_outputs/FIGURES.md`](research_outputs/FIGURES.md).

## 1. Contribution

The study evaluates **qubit-based clock synchronization (QCS) for BB84**:
Bob recovers Alice's clock from the detection times of single-photon sync
pulses that travel over the quantum channel itself, instead of relying on a
separate classical timing link.

In-band (qubit-based) synchronization is **already published** (Calderaro et
al. 2020; Cochran and Gauthier 2021; Chen et al. 2023; Krause et al. 2025;
Millet et al. 2026; Tiefenthaler et al. 2026) and must be cited, not claimed.
The contributions of this work, stated "to our knowledge", are:

1. A photon-limited synchronization model. Sync photons suffer the same fibre
   loss, detector inefficiency and dark counts as key photons, and the slots
   they occupy are charged to the key rate.
2. A two-stage estimator: drift-search (2-D cross-correlation) acquisition on a
   sparse preamble, followed by **recursive Kalman tracking** of offset and
   drift on interleaved secret pilot pulses, with innovation gating against
   dark counts. Kalman filters are already used in **continuous-variable** QKD
   to track the reference phase or polarization from bright pilot / coherent
   measurements (Wang et al. 2019; Huang et al. 2020; Chin et al. 2021;
   Kasthuri et al. 2024; review: Ma et al. 2022). The claim here is narrower:
   Kalman tracking of the **clock (timing offset and drift)** in
   **discrete-variable, photon-counting** QKD, where measurements are sparse
   Poisson click times, dark counts are outliers that must be gated, and lock
   can be lost; we found no prior work on this, and it is stated "to our
   knowledge".
   The closest qubit-based work, Millet et al. 2026 (ID Quantique, time-bin
   BB84, experimental), estimates drift from the circular means of two
   consecutive start-stop histograms (155 us to 500 ms each), corrects once
   and repeats: a batch estimator with no memory or uncertainty carried
   between corrections, dark counts treated as a flat histogram background,
   and no Kalman filtering (Kalman appears only in its citation of the
   classical ACES method). Its analytical model links drift-induced time
   shift to QBER and gives clock-stability requirements; ours predicts the
   tracker's RMS gate error, lock-loss probability and minimum pilot
   overhead. Millet et al. use the key detections themselves (no pilots) and
   validate in the field (100 km lab, 24 h metro network); our results are
   simulation only, which must be stated as a limitation.
   Acquisition accuracy is validated against the Cramér–Rao bound (Fig. 2c).
   The tracker runs either on 1 % interleaved pilots or **data-aided**, on
   the time tags of ordinary key clicks with no pilot overhead (the arrival
   time of a click carries no bit or basis information). Fig. 14 compares it
   with two baselines on the same clicks: batch cross-correlation re-sync on
   pilots, and a reimplementation of the Millet et al. two-histogram
   circular-mean method on key clicks (including its short-to-long histogram
   convergence schedule), tuned to its best histogram duration at every
   point (Fig. 16c).
3. A comparison against realistic baselines (no synchronization, a classical
   timing reference with sub-ns residual error, preamble-only QCS, batch
   re-synchronization, and perfect synchronization) under clock offset,
   drift, frequency wander, jitter, gate width, distance and block size.
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
| QCS, batch re-sync (baseline) | acquisition, then a fresh cross-correlation fit per batch of 32 pilot clicks, held until the next batch | preamble + 1 % pilot slots |
| QCS, preamble + tracking | acquisition, then Kalman updates from pilots | preamble + 1 % pilot slots |
| QCS, histogram re-sync (baseline) | acquisition, then Millet et al. 2026: circular means of two consecutive histograms of key-click tags folded over T, one correction per pair; histograms start at ~10 clicks and grow 4x every 3 corrections up to T_int | preamble only |
| QCS, data-aided tracking | acquisition, then Kalman updates from key-click tags (thinned to ≤ 10⁶ per segment, applied in groups of ≤ 25 clicks) | preamble only |
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

**Batch baseline.** `run_batch_resync` uses exactly the same pilot clicks. It
collects 32 clicks, fits the residual offset and drift with the same robust
cross-correlation used for acquisition (search range ±100 ppm), and holds
that line until the next batch completes. This represents the batch /
cross-correlation family of published qubit-based methods; it is a
re-implementation, not the authors' code.

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
| Source | decoy-state weak coherent pulses | intensities μ = 0.5 / 0.2 / 0.0002, chosen with probability 0.6 / 0.2 / 0.2; Z basis with probability 0.8 (tuned for 10¹⁰-slot key blocks). An ideal single-photon source is available as `source="single_photon"` |
| Sync segment | 10⁶–10⁸ slots | simulated pulse by pulse (offset, drift, wander, sync photons) |
| Key block N | 10¹⁰ slots (100 s at 100 MHz) | privacy-amplification block; Figs. 4 and 11 vary it |

Signal errors combine channel noise and Eve independently (XOR):
e = e_ch(1 − e_E) + e_E(1 − e_ch), with e_E = f/4 for intercept-resend on a
fraction f of pulses. Dark-count clicks and double clicks are assigned a
random bit (error ½). Each intensity μ gives a click probability
1 − exp(−η·C·μ) + dark counts, where η is fibre × detector transmittance and C
the timing capture. Sync pulses are sent at the signal intensity and are
simulated individually. Key-slot detections are drawn per (intensity, basis)
category with multinomial and binomial draws using the segment's mean capture
probability, which is exact in expectation.

**Sync segment and key block.** Synchronization is simulated pulse by pulse
over one segment (10⁸ slots = 1 s by default). Detection statistics are then
accumulated over a key block of 10¹⁰ slots, assuming every segment in the
block is synchronized with the same (stationary) statistics; the finite-key
bound is applied to the key block. Decoy-state finite-key bounds need such
long blocks: at 10⁸ slots the key vanishes before 100 km.

### 2.3 Protocol and security

**Decoy-state BB84 (default)** follows Lim et al. (2014):

1. Key bits come from Z-basis detections of all intensities; X-basis
   detections estimate the phase error.
2. Vacuum and single-photon detections s_Z,0 and s_Z,1 are lower-bounded from
   the per-intensity counts with Hoeffding fluctuation terms; the
   single-photon phase error φ_Z is upper-bounded from the X-basis errors.
3. The secure length is

       ℓ = s_Z,0 + s_Z,1 [1 − h(φ_Z)] − λ_EC − 6 log₂(21/ε_sec) − log₂(2/ε_cor)

   with λ_EC = f·n_Z·h(E_Z), f = 1.16, ε_sec = 10⁻¹⁰, ε_cor = 10⁻¹⁵
   (`bb84/security.decoy_key_components`).

**Ideal single-photon source (`source="single_photon"`)**: 10 % of sifted
bits estimate the QBER, the protocol aborts above 11 %, and the length
follows Tomamichel et al. (2012):

       ℓ = n[1 − h(Q_test + μ)] − f·n·h(Q_test) − log₂(2/(ε_sec² ε_cor))

In both cases Eve's true interception rate is never used in the key length.

The secret key rate is ℓ divided by **all** slots in the block, including sync
overhead. Asymptotic rates (the same bounds without fluctuation terms) and the
PLOB bound are plotted for reference.

### 2.5 Analytical model of the tracker (`bb84/tracking_theory.py`)

Pilot detections form a Poisson process with mean spacing
Δ = pilot spacing × T_slot / p_detect. The frequency error performs a random
walk with diffusion q (from the oscillator wander) and each detection
measures the timing error with variance r = σ_jitter².

1. **Steady state.** Iterating the Kalman predict/update equations at fixed Δ
   gives the posterior covariance (P11, P12, P22).
2. **Timing error.** Between updates V(t) = P11 + 2tP12 + t²P22 + qt³/3;
   averaging over exponential gaps gives the mean-square gate error
   P11 + 2P12Δ + 2P22Δ² + 2qΔ³. This matches the simulation within a few
   percent wherever the tracker is locked (Fig. 15a).
3. **Lock loss.** Two hazards: a gap long enough for the error to leave the
   ±T_slot/2 pilot window, and a dark count accepted by the 3σ innovation
   gate while V > r. Their rates give P_lost = 1 − exp(−λT) per segment,
   which predicts the lock boundary to within one distance step (Fig. 15b).
4. **Design rule.** Solving P_lost ≤ 1 % per second for the pilot spacing gives
   the minimum pilot overhead versus distance and oscillator quality
   (Fig. 15c).

### 2.4 Statistics and reproducibility

- Every sweep point has its own random generator, seeded from a master seed
  (20261007) and the experiment name. Results do not depend on run order or on
  the number of worker processes.
- Error bars are 95 % confidence intervals of the mean (1.96·s/√n).
  Acceptance probabilities use Wilson intervals.
- Sample size: every plotted point averages 100 to 1,000 independent blocks
  (Monte Carlo repetitions) of 10⁶ to 10⁸ photon slots, i.e. 10⁸ to 10¹¹
  simulated photon slots per point (heatmap cells: 50 blocks of 10⁸ slots;
  Fig. 10: median and 10–90 % band over 100 one-second blocks). The exact
  numbers and the median relative 95 % confidence half-width per figure are
  written to `research_outputs/table_statistics.md` by every run.
- `tests/test_research_model.py` (15 tests) checks the Monte Carlo against
  closed forms (QBER, capture, decoy QBER), the decoy bound (finite below
  asymptotic), the tracker theory against simulation, acquisition under dark
  counts, and reproducibility.

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
| 14 | `fig14_kalman_vs_batch` | Kalman tracking (pilots and data-aided) versus batch and Millet-style histogram re-sync, two oscillators (novelty) |
| 15 | `fig15_tracking_theory` | Analytical tracking error and lock-loss model versus simulation; minimum pilot overhead |
| 16 | `fig16_fairness` | Batch size and histogram duration tuned for the baselines; classical-reference quality sweep |
| — | `table_operating_points` | Numbers for the comparison table in the paper |
| — | `table_statistics` | Sample size and precision behind every figure |

Every figure is saved as PDF (vector, for LaTeX) and 300 dpi PNG, next to a
CSV of the plotted values. Each panel of a multi-panel figure is also saved on its own
in `research_outputs/panels/`. Legends always sit outside the plotting area. Figures carry no titles; captions belong in the
manuscript.

## 4. Limitations to state in the paper

- This is a simulation study, not an optical experiment.
- Decoy-state statistics are accumulated over 10¹⁰-slot key blocks assuming
  stationary synchronization across the 1 s segments of a block.
- Polarization drift, afterpulsing and detector dead time are not modelled.
- The Kalman tracker has no lock-loss detection or re-acquisition. Under heavy
  oscillator wander at long range it can lose lock (Fig. 10b).
- The classical-reference baseline is reduced to a constant residual error per
  block. Fig. 16b sweeps it: a classical reference better than about 100–200 ps
  matches or exceeds QCS (which pays about 1 % pilot overhead); QCS's advantage
  is at larger classical errors and in the timing-attack resistance (Fig. 13).
- The time-shift analysis assumes a rectangular-gate efficiency mismatch
  blurred by Gaussian jitter. Real detectors have smoother mismatch curves.
- The intercept-resend attack is used for QBER behaviour only. Security of the
  key length comes from the decoy-state finite-key bound, which covers general
  attacks, including photon-number splitting.

## 5. Reproduce

```bash
pip install -r requirements.txt
python -m pytest -q tests                 # model validation
python generate_graphs.py --quick         # draft figures in ~1 min
python generate_graphs.py                 # paper figures (tens of minutes on 4 cores)
python generate_graphs.py --only fig08    # one figure
```

## 6. References (verify page numbers before submission)

Related qubit-based synchronization work (cite in the related-work section):

- L. Calderaro et al., Phys. Rev. Applied 13, 054041 (2020) — Qubit4Sync.
- R. D. Cochran, D. J. Gauthier, Entropy 23, 988 (2021) — Bayesian qubit-based synchronization.
- Y. Chen et al., arXiv:2308.13154 — qubit-based distributed frame synchronization; R. Guan et al., arXiv:2510.17659 — field trial.
- J. Krause et al., Phys. Rev. Applied 23, 044015 (2025) — iQSync offset recovery.
- C. Spiess, F. Steinlechner, Quantum Sci. Technol. (2023) — clock synchronization with pulsed single photons.
- L. Millet, B. Korzh, R. Thew, G. Boso, arXiv:2605.26705 (2026) — clock-drift model (frequency mismatch vs QBER) and timestamp-based synchronization algorithm; no Kalman filter.
- G. Giorgi, C. Narduzzi, IEEE Trans. Instrum. Meas. 60, 2902 (2011); ISPCS 2013, 59 — Kalman-filter clock servos for IEEE 1588 (classical networks).
- B. R. Hamilton, X. Ma, Q. Zhao, J. Xu, "ACES: adaptive clock estimation and synchronization using Kalman filtering", MobiCom 2008 — classical-network Kalman clock sync.
- L. Tiefenthaler et al., Optics Express (2026), arXiv:2605.20857 — decoy-state-based time synchronization.

Kalman filtering in QKD (all continuous-variable phase/polarization tracking,
not clock synchronization; cite to delimit the claim):

- Y. Wang, P. Huang, et al., Opt. Express 27(19), 26689 (2019) — Kalman polarization tracking in CV-QKD.
- P. Huang, D. Huang, Z. Peng, Opt. Express 28(19), 28727 (2020) — Kalman reference-phase tracking in CV-QKD.
- H.-M. Chin et al., npj Quantum Inf. 7, 20 (2021) — unscented Kalman phase compensation in CV-QKD.
- J. Ma, et al., Symmetry 14(12), 2478 (2022) — review of Kalman filtering in quantum systems.
- Kasthuri et al., Optica Applicata 54(4), 483 (2024) — EKF + RNN phase estimation in CV-QKD.

Foundations:

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
