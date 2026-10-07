# Figure captions and headline results

Default parameters unless stated: T = 10 ns slots, 0.2 dB/km fibre,
detector efficiency 0.6, dark counts 10⁴ Hz per detector, Pauli p = 0.03
(2 % optical QBER), σ = 0.35 ns jitter, W = 2 ns gates, clock offset 4 ns,
drift 20 ppm, wander 0.01 ppm/√ms, 1 % pilots, classical-reference residual
0.5 ns, ε_sec = 10⁻¹⁰, ε_cor = 10⁻¹⁵. Error bars are 95 % confidence
intervals of the mean; shaded bands in Fig. 4 are Wilson intervals. Numbers
come from the CSV beside each figure.

**Fig. 1 — System model.**
(a) Alice, the quantum channel and Bob, with the QCS acquisition/tracking
loop and the classical post-processing chain. (b) Timing diagram. Alice's
emissions, photon arrivals shifted by clock offset and drift, Bob's nominal
gates (miss), and QCS-corrected gates (hit).

**Fig. 2 — Model validation.**
(a) Simulated QBER (markers) matches the closed form
e = e_ch(1 − f/4) + (f/4)(1 − e_ch) for three noise levels. (b) Click
probability per slot against gate width at 100 and 150 km matches
η·erf(W/(2√2σ)) plus gate-width-dependent dark counts. (c) Timing error at
the end of the acquisition preamble approaches the Cramér–Rao bound
σ·√((4n − 2)/(n(n + 1))) once more than about 15 photons are detected. With
fewer photons, dark-count outliers occasionally break acquisition.

**Fig. 3 — QBER under noise and attack.**
(a) QBER against channel Pauli error probability, with no Eve and with 20 %
interception. (b) QBER against Eve's interception fraction for a noiseless
channel and p = 0.03. The 11 % abort threshold is crossed at an interception
fraction of about 0.37 (noisy channel) and 0.44 (noiseless channel).

**Fig. 4 — Finite-size acceptance.**
Fraction of blocks that yield a positive finite-key length against Eve's
interception fraction. Blocks have 10⁵, 10⁶ and 10⁷ slots (200 blocks per
point). The 50 % point moves from f ≈ 0.075 (10⁵) to 0.25 (10⁶) and 0.30
(10⁷), towards the asymptotic QBER = 11 % limit (dashed). Small blocks abort
early because the statistical correction μ consumes the margin.

**Fig. 5 — Robustness to timing impairments (1 ms blocks, 25 km).**
Timing capture against (a) initial offset, (b) drift with zero offset and
(c) jitter, for five strategies.
- Without synchronization, capture is below 5 % except at zero drift.
- The classical reference loses 7–13 % to its 0.5 ns residual.
- Preamble-only QCS extrapolates its drift estimate over the block and keeps
  only 20–30 %.
- QCS with pilot tracking stays within 0.1 % of perfect synchronization
  across 0–20 ns offset and 0–200 ppm drift. At large jitter all strategies
  converge to the erf limit set by W/σ.

**Fig. 6 — Gate-width trade-off at 125 km (N = 10⁸).**
(a) Timing capture, (b) QBER and (c) finite-key secret key rate against gate
width W. Dark counts grow with W, so the key rate has an optimum.
- QCS tracking: optimum at W ≈ 1.5–2 ns, 3.07×10⁻⁴ bits/slot (perfect sync:
  3.20×10⁻⁴).
- Classical reference: 2.75×10⁻⁴ at W = 2 ns. It needs W ≈ 3 ns to absorb
  its residual error.
- Preamble-only QCS: produces no key.

**Fig. 7 — Synchronization overhead (N = 10⁸, wander 0.1 ppm/√ms).**
(a) RMS gate timing error and (b) key rate, normalized to the best overhead,
against the fraction of slots used as pilots.
- At 25 and 75 km, 0.1–1 % pilots reach 20–300 ps error, and the key rate is
  flat to within 10 %.
- At 125 km tracking loses lock below about 1 % pilots: errors reach the
  nanosecond-to-microsecond range and the key collapses.
- The best overhead therefore grows with distance (≈ 3 % at 125 km).

**Fig. 8 — Secret key rate against distance (N = 10⁸).**
Finite-key rate for the classical reference, QCS with tracking and perfect
synchronization, with the asymptotic perfect-sync rate and the PLOB bound
for reference.
- QCS tracking is within 1.5 % of perfect synchronization up to 100 km.
- It beats the classical reference by 3 % at 25 km, 8 % at 50 km, 6 % at
  100 km and 15 % at 150 km.
- Between 150 and 175 km all strategies stop producing a key: dark counts
  push the QBER above threshold and finite-size effects dominate.
- Preamble-only QCS loses lock within a 1 s block and is omitted here (see
  the table).

**Fig. 9 — Sensitivity maps (QCS tracking).**
(a) Finite-key rate at 125 km over gate width × jitter. The optimal W widens
with jitter, from ≤ 1 ns at σ ≤ 0.1 ns to 3–6 ns at σ ≥ 1 ns. (b) Key rate relative to perfect synchronization over
distance × pilot overhead (wander 0.1 ppm/√ms).
- At ≤ 100 km, 0.33–3.3 % pilots give ≥ 95 % of the ideal rate.
- At 125 km, at least 1 % is needed.
- At 150 km, at least 3.3 % is needed; even then QCS recovers only about 60 %
  of the ideal rate.

**Fig. 10 — Long-run stability over a 1 s block (wander 0.2 ppm/√ms).**
Timing capture over time at (a) 25 km and (b) 125 km.
- Preamble-only QCS loses alignment within milliseconds.
- Pilot tracking holds about 99.5 % capture at 25 km.
- At 125 km pilot tracking dips whenever no pilot is detected for several
  milliseconds. In this realization it loses lock at about 900 ms and does
  not recover, because the tracker has no re-acquisition step. Lock-loss
  detection with automatic re-acquisition is the obvious extension; at long
  range, more pilots (Fig. 9b) are needed.
- The classical reference is flat at a level set by its residual offset.

**Fig. 11 — Finite-key convergence.**
Secret key rate against block size at (a) 25 km and (b) 100 km. All
strategies approach the asymptotic limit (dotted) slowly. At 100 km no key
is possible below about 10⁶ slots. QCS tracking matches perfect
synchronization once N ≥ 3×10⁵ (25 km) or 3×10⁶ (100 km).

**Fig. 12 — Where the sifted bits go (25 km, N = 10⁷).**
Breakdown of sifted bits into test bits, error-correction leakage,
asymptotic and finite-size privacy amplification, and the final key, against
Eve's interception fraction. Without Eve 55 % of sifted bits become key. The
protocol aborts at f ≈ 0.30, before the asymptotic threshold, because of the
finite-size penalty.

**Fig. 13 — Timing side-channel attacks** (W = 2 ns, σ = 0.35 ns).
(a) Eve's information per sifted bit when she delays a classical timing
reference, for detector gate mismatch 0.2, 0.4 and 0.8 ns. With mismatch
0.8 ns, a 1 ns delay leaks 0.45 bit per sifted bit, and the QBER is
unchanged. QCS derives timing from the photons themselves, so a uniform delay
is absorbed and leaks nothing. (b) The same delay reduces Bob's click rate
(about 50 % at 1 ns), which is the only symptom visible without timing
analysis. (c) Against a random ±s time-shift attack, the variance test on
QCS arrival-time residuals (false-alarm rate 10⁻³) detects the attack with
99 % probability at s = 0.20 ns using 1 000 detections, or s = 0.125 ns using
10 000 detections. Over this range, Eve's information for 0.4 ns mismatch
stays below 0.015 bit.

**Table — `table_operating_points.md`.**
Overhead, gate timing error, capture, QBER, key rate and acceptance at 25,
50, 100 and 150 km for each strategy (N = 10⁸).
