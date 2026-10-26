Operating points (decoy-state BB84, key block 10^10 slots, sync simulated over 10^8-slot segments, W = 2 ns, sigma = 0.35 ns, offset 4 ns, drift 20 ppm). The histogram method uses the best of several histogram durations at each distance. Medians are typical blocks; means include blocks that lost lock.

| distance_km | strategy | sync_overhead_pct | gate_rms_median_ps | gate_rms_mean_ps | timing_capture_pct | qber_pct | secret_key_rate_bits_per_slot | blocks_accepted_pct |
|---|---|---|---|---|---|---|---|---|
| 25 | Classical reference | 0.0 | 313.9 | 349.6 | 93.04 | 2.03 | 1.244e-02 | 100.0 |
| 25 | QCS (preamble only) | 0.0 | 2007353.3 | 2284309.1 | 0.14 | 32.31 | 7.946e-06 | 2.0 |
| 25 | QCS, batch re-sync (prior-art style) | 1.0 | 245.3 | 244.9 | 97.93 | 2.03 | 1.300e-02 | 100.0 |
| 25 | QCS, histogram re-sync on key clicks (Millet-style) | 0.0 | 39.0 | 39.5 | 99.54 | 2.03 | 1.337e-02 | 100.0 |
| 25 | QCS (preamble + pilot tracking) | 1.0 | 32.0 | 32.1 | 99.56 | 2.03 | 1.323e-02 | 100.0 |
| 25 | QCS, Kalman tracking on key clicks (no pilots) | 0.0 | 13.1 | 13.1 | 99.57 | 2.03 | 1.337e-02 | 100.0 |
| 25 | Perfect synchronization | 0.0 | 0.0 | 0.0 | 99.57 | 2.03 | 1.337e-02 | 100.0 |
| 50 | Classical reference | 0.0 | 356.6 | 411.5 | 89.34 | 2.14 | 3.466e-03 | 100.0 |
| 50 | QCS (preamble only) | 0.01 | 666651.8 | 722959.3 | 0.31 | 31.64 | 1.674e-06 | 1.0 |
| 50 | QCS, batch re-sync (prior-art style) | 1.01 | 247.3 | 316646.9 | 96.9 | 2.54 | 3.741e-03 | 99.0 |
| 50 | QCS, histogram re-sync on key clicks (Millet-style) | 0.01 | 41.0 | 41.2 | 99.54 | 2.1 | 3.889e-03 | 100.0 |
| 50 | QCS (preamble + pilot tracking) | 1.01 | 49.5 | 49.6 | 99.53 | 2.1 | 3.849e-03 | 100.0 |
| 50 | QCS, Kalman tracking on key clicks (no pilots) | 0.01 | 13.1 | 13.2 | 99.57 | 2.1 | 3.890e-03 | 100.0 |
| 50 | Perfect synchronization | 0.0 | 0.0 | 0.0 | 99.57 | 2.1 | 3.889e-03 | 100.0 |
| 75 | Classical reference | 0.0 | 307.7 | 402.3 | 88.42 | 2.43 | 9.420e-04 | 99.0 |
| 75 | QCS (preamble only) | 0.03 | 242181.6 | 271435.1 | 1.13 | 31.44 | 7.306e-07 | 2.0 |
| 75 | QCS, batch re-sync (prior-art style) | 1.03 | 257.9 | 259.9 | 97.68 | 2.3 | 1.045e-03 | 100.0 |
| 75 | QCS, histogram re-sync on key clicks (Millet-style) | 0.03 | 54.9 | 55.2 | 99.52 | 2.3 | 1.080e-03 | 100.0 |
| 75 | QCS (preamble + pilot tracking) | 1.03 | 76.2 | 76.0 | 99.48 | 2.3 | 1.068e-03 | 100.0 |
| 75 | QCS, Kalman tracking on key clicks (no pilots) | 0.03 | 15.6 | 15.5 | 99.57 | 2.3 | 1.081e-03 | 100.0 |
| 75 | Perfect synchronization | 0.0 | 0.0 | 0.0 | 99.57 | 2.3 | 1.081e-03 | 100.0 |
| 100 | Classical reference | 0.0 | 284.0 | 356.2 | 91.77 | 3.05 | 2.092e-04 | 99.0 |
| 100 | QCS (preamble only) | 0.11 | 84677.9 | 100717.0 | 2.91 | 28.56 | 0.000e+00 | 0.0 |
| 100 | QCS, batch re-sync (prior-art style) | 1.11 | 316.0 | 323.4 | 96.21 | 2.96 | 2.223e-04 | 100.0 |
| 100 | QCS, histogram re-sync on key clicks (Millet-style) | 0.11 | 108.3 | 420250.9 | 96.35 | 4.32 | 2.297e-04 | 97.0 |
| 100 | QCS (preamble + pilot tracking) | 1.11 | 119.5 | 120.1 | 99.31 | 2.93 | 2.337e-04 | 100.0 |
| 100 | QCS, Kalman tracking on key clicks (no pilots) | 0.11 | 24.3 | 24.3 | 99.56 | 2.93 | 2.381e-04 | 100.0 |
| 100 | Perfect synchronization | 0.0 | 0.0 | 0.0 | 99.57 | 2.93 | 2.383e-04 | 100.0 |
