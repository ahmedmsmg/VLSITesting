# VLSI Testing ATPG Toolkit

This repository implements a graduate-level Automatic Test Pattern Generation (ATPG) tool for single stuck-at faults. The tool offers three classic algorithms—D-Algorithm, PODEM, and SAT-based ATPG—built atop a five-valued logic simulator.

## Features
- Five-valued logic engine (0, 1, X, D, D').
- ISCAS-style `.ckt` parser supporting AND, OR, NAND, NOR, XOR, XNOR, INV/NOT, and BUF.
- Circuit data structure with topological ordering and fault injection.
- D-Algorithm and PODEM search (no exhaustive enumeration).
- SAT-based ATPG using PySAT with good/faulty duplication and output-difference constraints.

## Dependencies
## You must use a Virtual Environment in Order to be able to pip/download and compile z3-solver
    - python -m venv .venv
    - source .venv/bin/activate
    - pip install z3-solver
    - pip install python-sat
    - Python 3.10+

## Usage
Interactive menu:

```
python atpg.py
# then choose:
# [0] load .ckt   [1] collapse   [2] list classes
# [3] simulate     [4] D-Alg     [5] PODEM
# [6] SAT ATPG     [7] exit
```

Output format:
```
Algorithm PODEM results:
Fault 1gat-sa0: test = 1X011
Fault 1gat-sa1: no test found
...
Detected 9/12 faults
```

## File Overview
- `logic5.py` – five-valued logic primitives.
- `ckt_parser.py` – ISCAS `.ckt` parser.
- `circuit.py` – circuit data structure and simulation.
- `d_algorithm.py` – D-Algorithm ATPG.
- `podem.py` – PODEM ATPG.
- `sat_atpg.py` – SAT-based ATPG with z3-solver- I tried PySAT first but wasn't working.
- `fault.py` – stuck-at fault definition.


