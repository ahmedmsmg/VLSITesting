# Ahmed Ghoneim And Samir Ahmed

# VLSI Testing ATPG Toolkit
This project implements a graduate-level Automatic Test Pattern Generation (ATPG) tool for single stuck-at faults. The tool offers three classic algorithms—D-Algorithm, PODEM, and SAT-based ATPG—built atop a five-valued logic simulator.

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

## How to load a .ckt file
Press 0 then type "examples/filename.ckt" or move your own tests into the root or example files and insert the location.

## How to simulate faults on a circuit [3]
Select an option: 3
"Enter test vector for PIs ['1gat', '2gat', '3gat', '4gat', '5gat', '6gat']:"

Here you would type a vector input, for example.. 101010

"Enter faults (e.g., a-sa0,b-sa1) or leave blank:"

Here you would type the faults simulated, for example.. 1gat-sa0,6gat-sa1

Output:"
Fault 1gat-sa0 not observable at outputs: {'16gat': '1'}
Fault 6gat-sa1 not observable at outputs: {'16gat': '1'}
"


## File Overview
- `logic5.py` – five-valued logic primitives.
- `ckt_parser.py` – ISCAS `.ckt` parser.
- `circuit.py` – circuit data structure and simulation.
- `d_algorithm.py` – D-Algorithm ATPG.
- `podem.py` – PODEM ATPG.
- `sat_atpg.py` – SAT-based ATPG with z3-solver- I tried PySAT first but wasn't working.
- `fault.py` – stuck-at fault definition.


