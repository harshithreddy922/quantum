Operating points (decoy-state BB84, key block 10^10 slots, sync simulated over 10^8-slot segments, W = 2 ns, sigma = 0.35 ns, offset 4 ns, drift 20 ppm).

| distance_km | strategy | sync_overhead_pct | gate_rms_error_ps | timing_capture_pct | qber_pct | secret_key_rate_bits_per_slot | blocks_accepted_pct |
|---|---|---|---|---|---|---|---|
| 25 | Classical reference | 0.0 | 349.6 | 93.04 | 2.03 | 1.244e-02 | 100.0 |
| 25 | QCS (preamble only) | 0.0 | 2284309.1 | 0.14 | 32.31 | 7.946e-06 | 2.0 |
| 25 | QCS, batch re-sync (prior-art style) | 1.0 | 244.9 | 97.93 | 2.03 | 1.300e-02 | 100.0 |
| 25 | QCS (preamble + pilot tracking) | 1.0 | 32.1 | 99.56 | 2.03 | 1.323e-02 | 100.0 |
| 25 | Perfect synchronization | 0.0 | 0.0 | 99.57 | 2.03 | 1.337e-02 | 100.0 |
| 50 | Classical reference | 0.0 | 411.5 | 89.34 | 2.14 | 3.466e-03 | 100.0 |
| 50 | QCS (preamble only) | 0.01 | 722959.3 | 0.31 | 31.64 | 1.674e-06 | 1.0 |
| 50 | QCS, batch re-sync (prior-art style) | 1.01 | 316646.9 | 96.9 | 2.54 | 3.741e-03 | 99.0 |
| 50 | QCS (preamble + pilot tracking) | 1.01 | 49.6 | 99.53 | 2.1 | 3.849e-03 | 100.0 |
| 50 | Perfect synchronization | 0.0 | 0.0 | 99.57 | 2.1 | 3.889e-03 | 100.0 |
| 75 | Classical reference | 0.0 | 402.3 | 88.42 | 2.43 | 9.420e-04 | 99.0 |
| 75 | QCS (preamble only) | 0.03 | 271435.1 | 1.13 | 31.44 | 7.306e-07 | 2.0 |
| 75 | QCS, batch re-sync (prior-art style) | 1.03 | 259.9 | 97.68 | 2.3 | 1.045e-03 | 100.0 |
| 75 | QCS (preamble + pilot tracking) | 1.03 | 76.0 | 99.48 | 2.3 | 1.068e-03 | 100.0 |
| 75 | Perfect synchronization | 0.0 | 0.0 | 99.57 | 2.3 | 1.081e-03 | 100.0 |
| 100 | Classical reference | 0.0 | 356.2 | 91.77 | 3.05 | 2.092e-04 | 99.0 |
| 100 | QCS (preamble only) | 0.11 | 100717.0 | 2.91 | 28.56 | 0.000e+00 | 0.0 |
| 100 | QCS, batch re-sync (prior-art style) | 1.11 | 323.4 | 96.21 | 2.96 | 2.223e-04 | 100.0 |
| 100 | QCS (preamble + pilot tracking) | 1.11 | 120.1 | 99.31 | 2.93 | 2.337e-04 | 100.0 |
| 100 | Perfect synchronization | 0.0 | 0.0 | 99.57 | 2.93 | 2.383e-04 | 100.0 |
