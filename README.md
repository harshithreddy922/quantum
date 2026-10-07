# QCS-Assisted BB84 QKD Simulation

This project simulates BB84 quantum key distribution with Quantum Clock Synchronization (QCS), channel noise, timing impairments, detector behavior, QBER-based acceptance, error correction, privacy amplification, and intercept-resend eavesdropping.

## Contents

- `main.py` - interactive BB84 simulation flow.
- `bb84/` - BB84 and QCS simulation modules.
- `research_simulation.py` - reusable simulation model for research sweeps.
- `generate_graphs.py` - generates publication-oriented CSV and PNG outputs.
- `research_outputs/` - generated graph data and figures.
- `RESEARCH_METHODOLOGY.md` - framing, metrics, baselines, and publication notes.

## Setup

```bash
python -m venv .venv
pip install -r requirements.txt
```

## Run

Run the interactive BB84 simulation:

```bash
python main.py
```

Generate the research graphs:

```bash
python generate_graphs.py
```

The generated graphs and CSV files are written to `research_outputs/`.
