Operating points (N = 10^8 slots per block, W = 2 ns, sigma = 0.35 ns, offset 4 ns, drift 20 ppm).

| distance_km | strategy | sync_overhead_pct | gate_rms_error_ps | timing_capture_pct | qber_pct | secret_key_rate_bits_per_slot | blocks_accepted_pct |
|---|---|---|---|---|---|---|---|
| 25 | Classical reference | 0.0 | 386.4 | 89.67 | 2.01 | 5.077e-02 | 100.0 |
| 25 | QCS (preamble only) | 0.0 | 4182281.3 | 0.1 | 26.73 | 3.211e-05 | 4.0 |
| 25 | QCS, batch re-sync (prior-art style) | 1.0 | 243.9 | 97.95 | 2.01 | 5.502e-02 | 100.0 |
| 25 | QCS (preamble + pilot tracking) | 1.0 | 24.3 | 99.56 | 2.01 | 5.594e-02 | 100.0 |
| 25 | Perfect synchronization | 0.0 | 0.0 | 99.57 | 2.01 | 5.649e-02 | 100.0 |
| 50 | Classical reference | 0.0 | 409.4 | 90.17 | 2.06 | 1.556e-02 | 100.0 |
| 50 | QCS (preamble only) | 0.01 | 1400162.9 | 0.09 | 28.82 | 2.866e-07 | 2.0 |
| 50 | QCS, batch re-sync (prior-art style) | 1.01 | 245.9 | 97.91 | 2.03 | 1.676e-02 | 100.0 |
| 50 | QCS (preamble + pilot tracking) | 1.01 | 37.7 | 99.55 | 2.03 | 1.705e-02 | 100.0 |
| 50 | Perfect synchronization | 0.0 | 0.0 | 99.57 | 2.03 | 1.725e-02 | 100.0 |
| 100 | Classical reference | 0.0 | 370.6 | 92.0 | 2.36 | 1.273e-03 | 100.0 |
| 100 | QCS (preamble only) | 0.05 | 179825.5 | 1.93 | 26.62 | 2.094e-06 | 6.0 |
| 100 | QCS, batch re-sync (prior-art style) | 1.05 | 269.6 | 97.47 | 2.33 | 1.343e-03 | 100.0 |
| 100 | QCS (preamble + pilot tracking) | 1.05 | 91.2 | 99.43 | 2.31 | 1.383e-03 | 100.0 |
| 100 | Perfect synchronization | 0.0 | 0.0 | 99.57 | 2.32 | 1.403e-03 | 100.0 |
| 150 | Classical reference | 0.0 | 408.7 | 88.38 | 5.73 | 1.489e-05 | 82.0 |
| 150 | QCS (preamble only) | 0.53 | 70012.8 | 5.09 | 31.48 | 0.000e+00 | 0.0 |
| 150 | QCS, batch re-sync (prior-art style) | 1.53 | 2543975.6 | 55.91 | 8.22 | 2.382e-07 | 3.0 |
| 150 | QCS (preamble + pilot tracking) | 1.53 | 4111.1 | 93.38 | 5.54 | 1.647e-05 | 93.0 |
| 150 | Perfect synchronization | 0.0 | 0.0 | 99.57 | 5.04 | 2.246e-05 | 100.0 |
