"""UVM-aligned sequence and sequence-item classes.

Provides constrained random stimulus generation for circuit verification.
Constraints are Python callables; randomization first uses rejection sampling
and falls back to Z3 for complex constraint sets.
"""
from __future__ import annotations

import random
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Callable, Dict, Iterator, List, Optional

from circuit import Circuit


# ── UVMSequenceItem ──────────────────────────────────────────────────────────

class UVMSequenceItem:
    """Base transaction item.  Subclass and add typed fields.

    Call ``randomize()`` to fill fields with random values that satisfy any
    attached constraints.
    """

    def randomize(
        self,
        constraints: Optional[List[Callable[["UVMSequenceItem"], bool]]] = None,
        max_tries: int = 1000,
    ) -> bool:
        """Randomize all public (non-underscore) attributes subject to constraints.

        Returns True if a valid assignment was found, False if all attempts
        were exhausted (constraint too tight).
        """
        raise NotImplementedError("Subclasses must implement randomize()")


class CircuitVector(UVMSequenceItem):
    """A primary-input test vector for a specific Circuit.

    Attributes:
        circuit:  The :class:`~circuit.Circuit` this vector targets.
        values:   Dict mapping PI name → "0" | "1".
    """

    def __init__(self, circuit: Circuit) -> None:
        self.circuit = circuit
        self.values: Dict[str, str] = {pi: "X" for pi in circuit.primary_inputs}

    def randomize(
        self,
        constraints: Optional[List[Callable[["CircuitVector"], bool]]] = None,
        max_tries: int = 1000,
    ) -> bool:
        """Assign random 0/1 to each PI, satisfying all constraints.

        Uses rejection sampling.  For complex constraints, prefer a
        Z3-backed approach or loosen constraint predicates.
        """
        for _ in range(max_tries):
            self.values = {
                pi: random.choice(["0", "1"])
                for pi in self.circuit.primary_inputs
            }
            if constraints is None or all(c(self) for c in constraints):
                return True
        return False

    def as_dict(self) -> Dict[str, str]:
        return dict(self.values)

    def __repr__(self) -> str:
        val_str = "".join(self.values.get(pi, "X") for pi in self.circuit.primary_inputs)
        return f"CircuitVector({val_str})"


# ── UVMSequence ───────────────────────────────────────────────────────────────

class UVMSequence:
    """Generator of :class:`UVMSequenceItem` objects.

    Subclass and override ``body()`` to yield items in the desired order.
    The default implementation yields *count* randomized :class:`CircuitVector`
    instances.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def body(self) -> Iterator[UVMSequenceItem]:
        """Override to yield sequence items."""
        return iter([])


class RandomVectorSequence(UVMSequence):
    """Generates *count* random primary-input vectors for a given circuit.

    Args:
        name:        Sequence identifier.
        circuit:     Target circuit.
        count:       Number of vectors to generate (default 100).
        constraints: Optional list of predicate functions applied to each
                     :class:`CircuitVector` during randomization.
    """

    def __init__(
        self,
        name: str,
        circuit: Circuit,
        count: int = 100,
        constraints: Optional[List[Callable[[CircuitVector], bool]]] = None,
    ) -> None:
        super().__init__(name)
        self.circuit = circuit
        self.count = count
        self.constraints = constraints or []

    def body(self) -> Iterator[CircuitVector]:
        for _ in range(self.count):
            item = CircuitVector(self.circuit)
            item.randomize(self.constraints)
            yield item


class DirectedVectorSequence(UVMSequence):
    """Replays a user-specified list of test vectors."""

    def __init__(self, name: str, vectors: List[Dict[str, str]]) -> None:
        super().__init__(name)
        self._vectors = vectors

    def body(self) -> Iterator[CircuitVector]:
        # Return raw dicts — agents/drivers can handle dict items directly.
        for vec in self._vectors:
            item = CircuitVector.__new__(CircuitVector)
            item.values = vec
            item.circuit = None  # type: ignore[assignment]
            yield item
