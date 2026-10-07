# Research Methodology for Publication

## Proposed Contribution

This project should be framed as a simulation-based study of **Quantum Clock
Synchronization assisted BB84 QKD**. The novelty is not plain BB84, because
BB84 with QBER and intercept-resend attacks is already well studied. The
publishable contribution is the combined evaluation of BB84 security and
timing-layer reliability under practical impairments:

- clock offset
- clock drift
- timing jitter
- detector gate width
- detector efficiency
- dark-count probability
- fiber/channel attenuation
- channel noise
- partial intercept-resend attacks
- finite sifted-key availability
- privacy-amplification budget

The central research claim should be:

> QCS-assisted BB84 improves photon detection and final key availability under
> timing impairments while preserving QBER-based eavesdropping detection and
> privacy amplification behavior.

## Baselines

Every result should compare against at least one baseline:

- BB84 without QCS
- BB84 with QCS
- BB84 with no Eve
- BB84 with partial Eve
- ideal channel
- noisy channel

This avoids presenting isolated simulation curves and makes the work easier to
defend during review.

## Publication Graphs

The upgraded graph generator creates the following paper-ready figures in
`research_outputs/`:

1. `noise_vs_qber.png`  
   Channel noise versus QBER, comparing no Eve and 20% Eve.

2. `attack_vs_qber.png`  
   Eve interception probability versus QBER, comparing ideal and noisy channels.

3. `detector_window_vs_timing_capture.png`  
   Detector window size versus timing-window capture rate, comparing without QCS
   and with QCS. This graph isolates the synchronization contribution before
   physical channel loss is applied.

4. `detector_window_timing_vs_end_to_end.png`  
   Timing capture versus end-to-end detection. This separates QCS alignment from
   channel attenuation and detector inefficiency.

5. `clock_offset_vs_timing_capture.png`  
   Clock offset versus timing-window capture rate, comparing without QCS and
   with QCS.

6. `clock_drift_vs_timing_capture.png`  
   Clock drift versus timing-window capture rate, comparing without QCS and
   with QCS.

7. `timing_jitter_vs_timing_capture.png`  
   Timing jitter versus timing-window capture rate, comparing without QCS and
   with QCS.

8. `raw_qubits_vs_final_key.png`  
   Raw transmitted qubits versus final secure key length, comparing without QCS
   and with QCS.

9. `eve_vs_sifted_key_rate.png`  
   Eve interception probability versus sifted key rate.

10. `eve_vs_acceptance_probability.png`  
   Eve interception probability versus key acceptance probability under the 11%
   QBER threshold.

11. `distance_vs_secret_key_rate.png`  
    Fiber distance versus final secret key rate under attenuation.

12. `privacy_amplification_budget.png`  
    Eve interception probability versus final key length after reconciliation
    leakage and privacy amplification.

Each figure has a matching CSV file so the paper can report numerical values
and reviewers can inspect the data.

## Metrics

The research simulation computes:

- detection rate
- timing-window capture rate
- sifted key rate
- QBER
- corrected error count
- reconciliation leakage estimate
- estimated Eve information
- final key length
- final secret key rate
- acceptance probability

The final key length is modeled conservatively as:

```text
final_bits = sifted_bits
             - reconciliation_leak
             - estimated_eve_information
             - security_margin
```

where reconciliation leakage is estimated using a binary-entropy term. This is
more suitable for a paper than directly copying Alice's key into Bob's key.

## Recommended Experimental Setting

For draft figures:

```bash
python generate_graphs.py
```

For stronger final paper results, increase `DEFAULT_TRIALS` in
`generate_graphs.py` from `50` to `100` or more. Use the CSV files for tables
and confidence reporting.

## Important Limitation to State

This is a simulation study, not an experimental optical QKD implementation. The
paper should explicitly state that detector efficiency, dark counts, attenuation,
and timing impairments are modeled statistically. Avoid claiming hardware-level
security unless the model is later validated on physical equipment.

## Suggested Paper Title

**Performance Analysis of Quantum Clock Synchronization Assisted BB84 Quantum
Key Distribution under Timing Jitter, Clock Drift, Channel Noise, and Partial
Intercept-Resend Attacks**

