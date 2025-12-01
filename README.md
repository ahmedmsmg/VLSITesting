# ATPG for Single Stuck-At Faults

This repository provides a graduate-level Automatic Test Pattern Generation (ATPG) tool implementing three algorithms for single stuck-at faults:

- **D-Algorithm**
- **PODEM**
- **SAT-based ATPG** (CNF + internal DPLL solver)

The tool operates on ISCAS-style `.ckt` netlists that describe combinational logic using familiar gate primitives.

## Usage

Generate tests from the command line:

```bash
python atpg.py <path/to/netlist.ckt> --algo D      # run D-Algorithm
python atpg.py <path/to/netlist.ckt> --algo PODEM  # run PODEM
python atpg.py <path/to/netlist.ckt> --algo SAT    # run SAT-based ATPG
python atpg.py <path/to/netlist.ckt> --algo ALL    # run all algorithms
```

Output is reported per fault in the following style:

```
Fault a-sa0:    test = 1011
Fault b-sa1:    no test found
```

All primary inputs are listed in the order given by the netlist. Each fault is attempted for both stuck-at-0 and stuck-at-1 values across every signal.

## Netlist format

The parser accepts ISCAS-style gate descriptions:

```
INPUT(a)
INPUT(b)
OUTPUT(f)
f = AND(a, b)
g = OR(a, b)
```

Supported gate types: `AND`, `OR`, `NAND`, `NOR`, `XOR`, `XNOR`, `INV`/`NOT`, and `BUF`.

Comments may follow a `$` character and are ignored.

A ready-to-run benchmark is included at `examples/c17.ckt`.

## Project structure

- `atpg.py` – CLI driver
- `ckt_parser.py` – parses `.ckt` files
- `circuit.py` – circuit representation and five-valued simulation
- `logic5.py` – five-valued algebra (`0`, `1`, `X`, `D`, `D'`)
- `fault.py` – fault data structure
- `d_algorithm.py` – D-Algorithm ATPG
- `podem.py` – PODEM ATPG
- `sat_atpg.py` – SAT-based ATPG with CNF builder and DPLL solver
- `examples/` – sample circuits
