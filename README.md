# QCS-Assisted BB84 QKD Simulation

Simulation study of BB84 quantum key distribution with qubit-based clock
synchronization (QCS). Bob recovers Alice's clock from single-photon sync
pulses on the quantum channel. The study models fibre loss, gate-width-
dependent dark counts, clock offset, drift and wander, timing jitter,
intercept-resend and time-shift attacks, and composable finite-key privacy
amplification.

## Contents

- `main.py` — interactive, Qiskit-based walk-through of one BB84 run (didactic).
- `bb84/` — protocol modules:
  - `qcs_tracking.py` — photon-limited acquisition (drift search) and Kalman tracking.
  - `security.py` — finite-key length, Shor–Preskill rate, PLOB bound, Wilson intervals.
  - `timing_attacks.py` — detector-mismatch time-shift model and QCS timing monitor.
  - `qcs_synchronization.py` — simplified sync demo used by `main.py`.
- `research_simulation.py` — Monte Carlo research model (timing, physical and protocol layers).
- `generate_graphs.py` — generates the 13 paper figures, CSVs and the operating-point table.
- `tests/` — checks of the model against closed-form results.
- `research_outputs/` — generated figures (PDF and PNG), CSVs and `FIGURES.md` captions.
- `research_outputs/panels/` — each panel of the multi-panel figures as its own larger image
  (e.g. `fig05_timing_impairments_a.png`), for papers or slides that need single graphs.
- `RESEARCH_METHODOLOGY.md` — model, assumptions, statistics, limitations and references.

## Setup

```bash
python -m venv .venv
pip install -r requirements.txt
```

## Run

```bash
python main.py                          # interactive BB84 walk-through
python -m pytest -q tests               # validate the research model
python generate_graphs.py --quick       # draft figures (~1 min)
python generate_graphs.py               # full-fidelity paper figures
```
