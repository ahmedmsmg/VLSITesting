"""SVA-like assertion primitives for Python-based verification.

Models two core SVA constructs:

- :class:`ImmediateAssertion` — checks a condition on a single transaction
  (analogous to SVA immediate assertions).
- :class:`ConcurrentAssertion` — checks an antecedent → consequent pattern
  over a sliding window of transaction history (analogous to concurrent SVA
  ``property`` with ``|->`` implication).
- :class:`PropertySequence` — composes assertions into named sequences for
  reuse.

All assertion results are accumulated so the report phase can summarize them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


Transaction = Dict[str, Any]


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class AssertionResult:
    """The outcome of one assertion evaluation."""
    name: str
    passed: bool
    message: str = ""
    transaction: Optional[Transaction] = None

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        msg = f"[{status}] {self.name}"
        if self.message:
            msg += f": {self.message}"
        return msg


# ── Base assertion ────────────────────────────────────────────────────────────

class Assertion:
    """Base class for all assertions."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.results: List[AssertionResult] = []

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    def report(self) -> str:
        total = len(self.results)
        return (
            f"Assertion '{self.name}': "
            f"{self.pass_count}/{total} passed, {self.fail_count} failed"
        )


# ── Immediate assertion ───────────────────────────────────────────────────────

class ImmediateAssertion(Assertion):
    """Evaluates a Boolean condition on a single transaction immediately.

    Analogous to SystemVerilog immediate assertions::

        assert (condition) else $error("message");

    Args:
        name:      Assertion identifier.
        condition: Callable that takes a :data:`Transaction` and returns bool.
        message:   Optional failure message template.
    """

    def __init__(
        self,
        name: str,
        condition: Callable[[Transaction], bool],
        message: str = "",
    ) -> None:
        super().__init__(name)
        self.condition = condition
        self.message = message

    def check(self, txn: Transaction) -> AssertionResult:
        """Evaluate the condition against *txn* and record the result."""
        try:
            passed = bool(self.condition(txn))
        except Exception as exc:
            passed = False
            result = AssertionResult(
                name=self.name,
                passed=False,
                message=f"Exception: {exc}",
                transaction=txn,
            )
            self.results.append(result)
            return result

        result = AssertionResult(
            name=self.name,
            passed=passed,
            message="" if passed else self.message,
            transaction=txn,
        )
        self.results.append(result)
        return result


# ── Concurrent assertion ──────────────────────────────────────────────────────

class ConcurrentAssertion(Assertion):
    """Checks an antecedent → consequent pattern across a history window.

    Analogous to SVA concurrent properties::

        property p;
            @(posedge clk) antecedent |-> consequent;
        endproperty

    When the antecedent matches in the current transaction, the consequent
    is checked in the *same* transaction (zero-delay implication, ``|->``)
    or in a future one (multi-cycle — use ``history_depth > 1`` and index
    ``history[-1]`` for the antecedent, ``history[0]`` for the consequent).

    Args:
        name:        Assertion identifier.
        antecedent:  Callable(txn) → bool — triggering condition.
        consequent:  Callable(txn) → bool — must hold when antecedent fires.
        history_depth: Number of past transactions to keep (default 1 = same
                     transaction for both antecedent and consequent).
    """

    def __init__(
        self,
        name: str,
        antecedent: Callable[[Transaction], bool],
        consequent: Callable[[Transaction], bool],
        history_depth: int = 1,
    ) -> None:
        super().__init__(name)
        self.antecedent = antecedent
        self.consequent = consequent
        self.history_depth = history_depth
        self._history: List[Transaction] = []

    def check(self, txn: Transaction) -> Optional[AssertionResult]:
        """Feed *txn* into the assertion window.

        Returns an :class:`AssertionResult` only when the antecedent fires;
        returns ``None`` otherwise (no assertion to evaluate yet).
        """
        self._history.append(txn)
        if len(self._history) > self.history_depth:
            self._history.pop(0)

        if len(self._history) < self.history_depth:
            return None  # window not yet full

        # Antecedent evaluated on the oldest transaction in the window.
        trigger_txn = self._history[0]
        if not self.antecedent(trigger_txn):
            return None  # antecedent did not fire

        # Consequent evaluated on the newest transaction (current).
        try:
            passed = bool(self.consequent(txn))
        except Exception as exc:
            result = AssertionResult(
                name=self.name,
                passed=False,
                message=f"Exception in consequent: {exc}",
                transaction=txn,
            )
            self.results.append(result)
            return result

        result = AssertionResult(
            name=self.name,
            passed=passed,
            message="" if passed else "Consequent not satisfied after antecedent",
            transaction=txn,
        )
        self.results.append(result)
        return result


# ── Property sequence (composite) ────────────────────────────────────────────

class PropertySequence:
    """A named collection of assertions evaluated as a unit.

    Use this to bundle related assertions and drive them all from a single
    :meth:`check` call.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._assertions: List[Assertion] = []

    def add(self, assertion: Assertion) -> "PropertySequence":
        self._assertions.append(assertion)
        return self

    def check(self, txn: Transaction) -> List[AssertionResult]:
        """Run all assertions against *txn* and return their results."""
        results: List[AssertionResult] = []
        for assertion in self._assertions:
            if isinstance(assertion, ImmediateAssertion):
                results.append(assertion.check(txn))
            elif isinstance(assertion, ConcurrentAssertion):
                r = assertion.check(txn)
                if r is not None:
                    results.append(r)
        return results

    def report(self) -> str:
        lines = [f"PropertySequence '{self.name}':"]
        for a in self._assertions:
            lines.append("  " + a.report())
        return "\n".join(lines)
