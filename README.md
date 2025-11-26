# VLSI Testing Toolkit

This repository implements a small interactive Automatic Test Pattern Generation (ATPG) tool for single stuck-at faults. The tool reads gate-level netlists, performs a basic fault-collapsing pass, simulates faults, and can exhaustively search for test vectors that detect faults using three menu options styled after D-Algorithm, PODEM, and SAT-based flows.

## Running the tool

The entry point is `atpg.py`. Start the interactive menu with:

```bash
python atpg.py
```

You can pre-load a netlist using the optional flag:

```bash
python atpg.py --netlist examples/c17.net
```

The menu provides the following actions:

- **[0] Read the input net-list** – load a netlist file.
- **[1] Perform fault collapsing** – create fault classes for every line (stuck-at-0 and stuck-at-1).
- **[2] List fault classes** – print the generated fault classes.
- **[3] Simulate** – evaluate a test vector with optional faults to see if they are detected.
- **[4]/[5]/[6] Generate tests** – exhaustively enumerate primary input vectors to find detecting tests; results are grouped by fault and a list of undetectable faults is shown.
- **[7] Exit** – quit the program.

## Netlist format

The parser expects a simple gate-level format where each line either lists a single signal name (used to declare primary inputs/outputs) or defines a gate using the syntax:

```
<output> <gate_type> <input1> <input2> [...]
```

Comments can be added after a `$` character. Supported gate types include `and`, `nand`, `or`, `nor`, `xor`, `xnor`, `not`/`inv`, and `buf`.

An example netlist is available at `examples/c17.net`.
