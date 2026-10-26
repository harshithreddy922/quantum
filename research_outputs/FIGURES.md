# Figure captions and headline results

Default parameters unless stated: decoy-state BB84 with weak coherent pulses
(intensities μ = 0.5 / 0.2 / 0.0002 sent with probabilities 0.6 / 0.2 / 0.2,
Z basis chosen with probability 0.8), key blocks of N = 10¹⁰ pulse slots,
T = 10 ns slots, 0.2 dB/km fibre, detector efficiency 0.6, dark counts 10⁴ Hz,
Pauli p = 0.03 (2 % optical QBER), σ = 0.35 ns jitter, W = 2 ns gates, clock
offset 4 ns, drift 20 ppm, wander 0.01 ppm/√ms, 1 % pilots, classical-reference
residual 0.5 ns, ε_sec = 10⁻¹⁰, ε_cor = 10⁻¹⁵. Synchronization is simulated
pulse by pulse over a 10⁸-slot segment (1 s) and is assumed stationary over
the rest of the key block. Error bars are 95 % confidence intervals of the
mean; Fig. 4 uses Wilson intervals. The sample size behind every figure
(10¹¹–10¹⁴ simulated pulse slots per figure) is listed in
`table_statistics.md`. Numbers come from the CSV beside each figure.

The strategies compared are: no synchronization; a classical timing
reference; QCS with a preamble only; QCS with batch cross-correlation
re-synchronization on pilots (representative of published qubit-based
synchronization, e.g. Qubit4Sync); QCS with histogram re-synchronization on
key clicks (a reimplementation of Millet et al. 2026, Figs. 14 and 16 only);
QCS with Kalman tracking (this work), either on 1 % pilots or data-aided on
key clicks with no pilots (Figs. 14 and 16 only); and perfect
synchronization.

**Fig. 1 — System model.**
(a) Alice, the quantum channel and Bob, with the QCS acquisition/tracking
loop and the classical post-processing chain. (b) Timing diagram. Alice's
emissions, photon arrivals shifted by clock offset and drift, Bob's nominal
gates (miss), and QCS-corrected gates (hit).

**Fig. 2 — Model validation.**
(a) Simulated QBER (markers) matches the closed form for three channel noise
levels against Eve's interception fraction. (b) Click probability per slot
against gate width at 100 and 150 km matches η·erf(W/(2√2σ)) plus
gate-width-dependent dark counts. (c) Timing error at the end of the
acquisition preamble against the number of detected photons n, with the
Cramér–Rao bound σ·√((4n − 2)/(n(n + 1))). The estimator is within 7 % of the
bound for n ≥ 32 (e.g. 64 photons: 96 ps against 86 ps) and within 25 % for
n = 16. With 4–8 photons dark-count outliers occasionally break acquisition.

**Fig. 3 — QBER under noise and attack.**
(a) QBER against channel Pauli error probability, with no Eve and with 20 %
interception. (b) QBER against Eve's interception fraction for a noiseless
channel and p = 0.03. The QBER rises by f/4: the 11 % abort threshold is
crossed at f ≈ 0.37 (p = 0.03) and f ≈ 0.44 (noiseless).

**Fig. 4 — Finite-size acceptance.**
Fraction of blocks (1 000 per point) that yield a positive decoy-state
finite key against Eve's interception fraction, for N = 10⁸, 10⁹ and 10¹⁰
slots. The last accepted interception fraction moves from 0.075 (10⁸) to
0.125 (10⁹) and 0.15 (10¹⁰), approaching the point where even the
asymptotic key vanishes (dashed). Small blocks stop earlier because the
statistical corrections consume the margin.

**Fig. 5 — Robustness to timing impairments (25 km).**
Timing capture against (a) initial offset, (b) drift and (c) jitter.
- Without synchronization capture is below 1 % except at zero drift.
- The classical reference loses 8–12 % to its 0.5 ns residual.
- Preamble-only QCS extrapolates its drift estimate over the block and keeps
  6–10 %.
- Batch re-sync keeps 95–97 %.
- Kalman tracking keeps 99.5 %, within 0.05 % of perfect synchronization,
  across 0–20 ns offset and 0–200 ppm drift. At large jitter all strategies
  converge to the erf limit set by W/σ.

**Fig. 6 — Gate-width trade-off at 100 km.**
(a) Timing capture, (b) QBER and (c) finite-key rate against gate width W.
Dark counts grow with W, so the key rate has an optimum.
- Kalman tracking: optimum 2.40×10⁻⁴ bits/slot at W = 1.5 ns (perfect sync
  2.48×10⁻⁴).
- Batch re-sync: 2.22×10⁻⁴ at W = 2 ns. Classical reference: 2.01×10⁻⁴ at
  W = 2 ns; it needs wider gates to absorb its residual error.
- At W = 0.5 ns tracking keeps 91 % of the perfect-sync rate, batch 68 %
  and the classical reference 48 %.
- Preamble-only QCS produces no key.

**Fig. 7 — Pilot overhead.**
(a) RMS gate timing error and (b) key rate, normalized to the best overhead,
against the fraction of slots used as pilots, at 25, 75 and 100 km.
- At 25 km even 0.1 % pilots give 140 ps error and the full key rate.
- At 75 km and 100 km lock is lost in a growing share of runs below about
  1 % pilots (100 km: 3 % of runs at 1 %, 75 % at 0.33 %, all at 0.1 %;
  75 km: 45 % at 0.1 %), and the mean error rises to 15–550 ns. At 0.1 %
  pilots the key falls to 74 % (75 km) and 5 % (100 km) of the best.
- 1 % pilots keep ≥ 99 % of the best key at all three distances; 3.3 %
  gives ≤ 140 ps error everywhere; 10 % costs about 10 % of the key for
  little gain.

**Fig. 8 — Secret key rate against distance.**
Finite-key rate for the classical reference, the three QCS baselines and
variants (batch re-sync on pilots; histogram re-sync on key clicks after
Millet et al. 2026, with its histogram duration tuned at every distance;
Kalman tracking on pilots; Kalman tracking on key clicks) and perfect
synchronization, with the asymptotic perfect-sync rate and the PLOB bound.
- Key-click Kalman tracking is within 0.1 % of perfect synchronization up to
  100 km; pilot Kalman is within 2 %; the tuned histogram method is within
  0.1 % up to 75 km and 3.6 % at 100 km (QBER 4.3 % against 2.9 %, because
  3 % of its runs lose lock); batch re-sync is 3-7 % below.
- Key-click Kalman exceeds the classical reference by 7.5 % (25 km), 12 %
  (50 km), 15 % (75 km) and 14 % (100 km), and the histogram method by 3.7 %
  at 100 km. Pilot Kalman exceeds the classical reference by 6 %, 11 %, 13 %
  and 12 % at the same distances.
- At 125 km only the Kalman variants give any key. The rate is a few hundred
  bits per block there, so the percentages are noisy (key-click Kalman: 58 %
  of perfect here, 45 % in Fig. 14); nothing is extractable at 150 km with
  10^10-slot blocks.
- Preamble-only QCS gives essentially no key at any distance and is omitted
  from the plot (see `table_operating_points.md`).

**Fig. 9 — Sensitivity maps (Kalman tracking).**
(a) Finite-key rate at 100 km over gate width × jitter. The best gate widens
with jitter, from 0.5–0.75 ns at σ ≤ 0.1 ns to 3–4 ns at σ ≥ 1 ns.
(b) Key rate relative to perfect synchronization over distance × pilot
overhead.
- Up to 50 km every overhead from 0.1 % to 3.3 % gives ≥ 96 %.
- At 75 km ≥ 0.33 % pilots are needed; at 100 km ≥ 1 % (95 %).
- 10 % pilots cap the rate at about 88–90 %.

**Fig. 10 — Long-run stability over a 1 s segment (wander 0.2 ppm/√ms).**
Median timing capture over 100 independent runs with a 10–90 % band, at
(a) 25 km and (b) 125 km.
- At 25 km Kalman tracking holds 99.5 % throughout, batch re-sync 96–98 %,
  the classical reference 96.8 %; preamble-only QCS loses alignment within
  milliseconds.
- At 125 km with this poor oscillator batch re-sync loses lock within about
  20 ms and Kalman tracking within about 100 ms (median; some runs last
  ~250 ms). The tracker has no re-acquisition step; lock-loss detection with
  automatic re-acquisition is the obvious extension, and Fig. 15c gives the
  pilot overhead needed to avoid it.

**Fig. 11 — Finite-key convergence.**
Key rate against key-block size N at (a) 25 km and (b) 100 km.
- At 25 km Kalman tracking stays within 1–2 % of perfect synchronization for
  all N; the classical reference is 9–16 % lower.
- At 100 km no key is possible below about 3×10⁹ slots; tracking is within
  2–3 % of perfect sync from there on.
- Both converge slowly towards the asymptotic limit (dotted).

**Fig. 12 — Where the key-basis detections go (25 km, N = 10¹⁰, analytic).**
Decoy-state key budget against Eve's interception fraction. Without Eve 34 %
of Z-basis detections become secret key; 38 % are not certified as single
photon (multi-photon pulses), 17 % are spent on error correction and 12 % on
privacy amplification. The finite-size fixed cost is negligible at this
block size. The key vanishes at f ≈ 0.16.

**Fig. 13 — Timing side-channel attacks** (W = 2 ns, σ = 0.35 ns).
(a) Eve's information per sifted bit when she delays a classical timing
reference, for detector gate mismatch 0.2, 0.4 and 0.8 ns. With 0.8 ns
mismatch a 1 ns delay leaks about 0.45 bit per sifted bit without raising the
QBER. QCS derives timing from the photons themselves, so a uniform delay is
absorbed and leaks nothing. (b) The delay reduces Bob's click rate (about
50 % at 1 ns), the only symptom visible without timing analysis. (c) Against
a random ±s time-shift attack, a variance test on QCS arrival-time residuals
(false-alarm rate 10⁻³) detects the attack with > 90 % probability at
s = 0.325 ns (100 detections), 0.175 ns (1 000) and 0.10 ns (10 000).

**Fig. 14 — Kalman tracking versus published-style re-synchronization (novelty).**
Four methods for a stable (0.01 ppm/√ms, top row) and a poor (0.2 ppm/√ms,
bottom row) oscillator: batch cross-correlation re-sync on 1 % pilots;
histogram re-sync on key clicks after Millet et al. 2026, tuned to its best
histogram duration (100 µs–3 ms) at every point; Kalman tracking on 1 %
pilots; and Kalman tracking on key clicks with no pilots. (a, d) Median gate
timing error, (b, e) mean timing capture, (c, f) key rate relative to
perfect synchronization. 100 runs of 10⁸ slots per point.
- Kalman on key clicks is the most accurate everywhere: 13–24 ps up to
  100 km and 68 ps at 150 km (stable); 28–51 ps up to 100 km and 153 ps at
  150 km (poor). That is 3–5× below the tuned histogram method up to 125 km
  (39–201 ps stable, 79–420 ps poor) and 8–26× below it at 150 km, with no
  pilot overhead and no lock loss up to 125 km.
- At 125 km it keeps 45 % (stable) and 61 % (poor) of the perfect-sync key,
  against 24 % and 0 % for the histogram method, 15 % and 0 % for Kalman on
  pilots, and 0 % for batch re-sync.
- Kalman on pilots: 25–121 ps up to 100 km (stable), 3–10× below batch
  re-sync (244–323 ps), which loses lock at 125 km (stable) or from 75 km
  (poor).

**Fig. 15 — Analytical model of the tracker.**
(a) RMS gate error from the steady-state Riccati solution (lines) against
simulation (markers), for Kalman tracking on pilots (solid, circles and
squares) and on key clicks (dashed, stars): the same formula with the gap
between pilots replaced by the mean gap between processed key clicks. Pilots:
31.7 vs 32.1 ps at 25 km and 117 vs 121 ps at 100 km (stable oscillator);
67 vs 68 ps and 286 vs 323 ps (poor). Key clicks: 12.9 vs 13.1 ps at 25 km
and 23.3 vs 24.2 ps at 100 km (stable); 49.5 vs 51.3 ps at 100 km (poor).
Agreement is within 1-9 % up to 125 km for key clicks, and the simulation is
23-27 % above the theory at 150 km. (b) Probability of losing lock within
1 s for the pilot tracker. Theory places the 50 % point at 132 km (stable)
and 90 km (poor); simulation shows 3 % at 125 km and 76 % at 150 km
(stable) and 41 % at 100 km and 100 % at 125 km (poor). No lock loss is
modelled for key clicks (none was observed up to 125 km, Fig. 14).
(c) Design rule: minimum pilot overhead for < 1 % lock loss per second
against distance for three oscillator qualities. With a stable oscillator
1 % pilots suffice up to about 120 km; a poor oscillator needs 3.2 % at
100 km.

**Fig. 16 — Fairness checks on the baselines.**
(a) The batch baseline's batch size is swept (8–256 clicks) with the poor
oscillator. Its best setting (64 clicks: 207 ps at 25 km; 16 clicks: 1.3 ns at
100 km) is still 3× (25 km) and 4× (100 km) worse than Kalman pilot tracking
(69 ps and 287 ps). (b) Key rate against the classical reference's timing
error. A classical reference better than about 200 ps RMS matches QCS
tracking (≥ 99 % of perfect sync); at 0.5 ns it gives 83–88 % and at 1 ns
56–67 %. The benefit of QCS is removing the separate timing link and its
attack surface at equal performance, not beating a high-quality classical
reference. (c) The histogram duration of the Millet-style baseline is swept
(30 µs–10 ms) on the same key clicks, poor oscillator. Its best duration
(300 µs: 80 ps at 25 km, 206 ps at 100 km) is still 3× (25 km) and 4×
(100 km) worse than data-aided Kalman tracking (28 ps and 51 ps). Short
histograms are too noisy at long range; long ones let the oscillator wander
off between corrections.

**Table — `table_operating_points.md`.**
Overhead, median and mean gate timing error (the mean includes blocks that
lost lock), capture, QBER, key rate and acceptance at 25, 50, 75 and 100 km
for each strategy.

**Table — `table_statistics.md`.**
Points, blocks per point, slots per block, total simulated pulse slots and
median relative 95 % CI for every figure.
