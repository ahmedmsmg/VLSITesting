# Ahmed Ghoneim

# VLSI Testing — UVM-Based ATPG, DFT & Formal Verification Framework

A production-grade silicon verification framework covering three Intel tracks in a single Python toolkit:

| Track | Capability |
|-------|-----------|
| **CPU/GPU Design Verification** | UVM-aligned testbench (agents, monitors, scoreboards, SVA assertions, constrained random, functional coverage) |
| **DFT Design** | D-Algorithm, PODEM, and SAT-based ATPG engines with five-valued fault injection |
| **Formal Verification** | Z3/PySAT formal verification — combinational equivalence checking, property checking, bounded model checking |

Delivers **provably complete fault coverage** on all benchmark circuits and demonstrates verification methodology depth across silicon hardware engineering disciplines.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Requires Python 3.10+.

---

## Quick Start

### ATPG (Interactive)
```bash
python atpg.py
# [0] load .ckt   [1] fault collapse   [3] simulate
# [4] D-Algorithm  [5] PODEM           [6] SAT ATPG
```

### ATPG (Batch)
```bash
python atpg.py examples/t4_3.ckt --algo ALL
```

### Regression Flow (all circuits, all algorithms, coverage report)
```bash
python run_regression.py --prove --html reports/coverage.html
```

### Demos
```bash
python examples/demo_formal.py      # CEC, property checking, BMC
python examples/demo_uvm.py         # UVM env, constrained random, assertions, coverage
python examples/demo_regression.py  # Full regression with provable completeness
```

### Tests
```bash
python -m pytest tests/ -v          # 246 tests across all tracks
```

---

## Architecture

### Core Layer
- **`logic5.py`** — Roth five-valued algebra: `{0, 1, X, D, D'}`. Foundation for all simulation.
- **`circuit.py`** — `Circuit` + `Gate` + `FlipFlop` data model. `imply()` for forward simulation, `evaluate_vector()` for test execution.
- **`ckt_parser.py`** — ISCAS-style `.ckt` parser (two syntax variants; encoding-tolerant).
- **`fault.py`** — Stuck-at `Fault(node, stuck_at)` dataclass and fault collapsing.

### Track 2 — DFT / ATPG (`d_algorithm.py`, `podem.py`, `sat_atpg.py`)
All three engines share the same interface: `algo(circuit, fault) → Optional[Dict[str, str]]`.

- **D-Algorithm** — D-frontier / J-frontier backtracking search.
- **PODEM** — Path-oriented search with `x_path_exists()` pruning.
- **SAT** — Dual good/faulty circuit Z3 encoding; most reliable for complex circuits.

### Track 3 — Formal Verification (`formal/`)
Built on a shared `CircuitEncoder` that Z3-encodes any `Circuit`:

| Module | Purpose |
|--------|---------|
| `formal/encoder.py` | `CircuitEncoder` — shared Z3 Boolean encoding |
| `formal/equivalence.py` | `EquivalenceChecker` — CEC with counterexample extraction |
| `formal/property_check.py` | `PropertyChecker` + `Property` — prove Boolean invariants |
| `formal/bmc.py` | `BoundedModelChecker` — k-step unrolling for sequential circuits |
| `formal/pysat_backend.py` | `PySATEncoder` — Tseitin CNF encoding alternative |

### Track 1 — UVM-Aligned Verification (`uvm/`)

| Module | UVM Analogue |
|--------|-------------|
| `uvm/base.py` | `UVMComponent`, `UVMPhase` — component hierarchy, 6-phase lifecycle |
| `uvm/sequence.py` | `UVMSequenceItem`, `CircuitVector`, `RandomVectorSequence` — constrained random |
| `uvm/agent.py` | `UVMAgent` = `UVMDriver` + `UVMMonitor` |
| `uvm/scoreboard.py` | `UVMScoreboard` — runtime equivalence vs reference model |
| `uvm/coverage.py` | `CoverPoint`, `CoverCross`, `CoverGroup` — functional coverage |
| `uvm/assertions.py` | `ImmediateAssertion`, `ConcurrentAssertion` — SVA-like property checking |
| `uvm/env.py` | `UVMEnv` — top-level environment wiring all components |

### Regression & Coverage (`regression/`)
- **`regression/runner.py`** — discovers `.ckt` files, runs all algorithms on all faults.
- **`regression/coverage.py`** — `FaultCoverageAnalyzer` with `prove_completeness()` via SAT.
- **`regression/report.py`** — text / HTML / JSON coverage reports.
- **`run_regression.py`** — CLI entry point with `--prove`, `--html`, `--json` flags.

---

## Results

Running `python run_regression.py --prove` on all benchmark circuits:

```
OVERALL  126/126 detectable faults covered  (100.0%)
```

All five ISCAS benchmark circuits achieve 100% fault coverage with both D-Algorithm and SAT ATPG, confirmed provably complete via SAT-based redundancy proofs.

---

## File Overview

```
atpg.py              Interactive CLI driver (Tracks 2)
circuit.py           Core circuit model (Gate, FlipFlop, Circuit)
ckt_parser.py        ISCAS .ckt parser
logic5.py            Five-valued logic primitives
fault.py             Stuck-at fault model
d_algorithm.py       D-Algorithm ATPG
podem.py             PODEM ATPG
sat_atpg.py          SAT-based ATPG (Z3)
formal/              Track 3: formal verification
uvm/                 Track 1: UVM-aligned verification
regression/          Cross-cutting regression & coverage
run_regression.py    Regression entry point
tests/               246 pytest tests
examples/            .ckt netlists + demo scripts
requirements.txt     z3-solver, python-sat, pytest
```
