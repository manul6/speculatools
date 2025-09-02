from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, Tuple, Optional


class InvertibleTool(Protocol):
    """
    Contract for tools that can be inverted (rolled back).

    Tools implement two operations:
    - apply: performs the side-effecting action, returns a result dict with at least {"status": ...}
    - invert: reverses the effect of the prior apply given the same args/context.

    """

    name: str
    invertible: bool

    def apply(self, args: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def invert(self, args: Dict[str, Any]) -> None:
        ...


@dataclass
class AppliedStep:
    tool: InvertibleTool
    args: Dict[str, Any]
    result: Dict[str, Any]


class SpeculativeExecutor:
    """
    Executes a sequence of tool calls speculatively.

    - If every tool in the speculative window is invertible, it will apply them eagerly.
    - If a non-invertible tool appears, the speculative window is limited to at most one step.
    - On error of any step, previously applied steps in the window are inverted in reverse order.

    Returns (results, error_at) where:
      - results: list of (tool.name, result) for steps that ran
      - error_at: index of failing step or None on full success
    """

    def __init__(self) -> None:
        self.history: List[AppliedStep] = []

    def run_plan(
        self,
        plan: List[Tuple[InvertibleTool, Dict[str, Any]]],
    ) -> Tuple[List[Tuple[str, Dict[str, Any]]], Optional[int]]:
        self.history.clear()
        results: List[Tuple[str, Dict[str, Any]]] = []

        
        max_window = len(plan)
        if any(not tool.invertible for tool, _ in plan):
            
            max_window = 1

        for idx, (tool, args) in enumerate(plan):
            result = tool.apply(args)
            results.append((tool.name, result))

            if result.get("status") != "success":
                for step in reversed(self.history):
                    try:
                        step.tool.invert(step.args)
                    except Exception:
                        pass
                return results, idx

            if tool.invertible:
                self.history.append(AppliedStep(tool=tool, args=args, result=result))

            if idx + 1 >= max_window:
                break

        return results, None


class CounterTool:
    """A simple invertible tool that records how many times it's applied/inverted."""

    def __init__(self, name: str, invertible: bool = True, should_fail: bool = False):
        self.name = name
        self.invertible = invertible
        self.should_fail = should_fail
        self.applied: int = 0
        self.inverted: int = 0
        self.calls: List[Dict[str, Any]] = []

    def apply(self, args: Dict[str, Any]) -> Dict[str, Any]:
        self.applied += 1
        self.calls.append(args)
        if self.should_fail:
            return {"status": "error", "tool": self.name, "args": dict(args)}
        return {"status": "success", "tool": self.name, "args": dict(args)}

    def invert(self, args: Dict[str, Any]) -> None:
        if not self.invertible:
            raise RuntimeError(f"Tool {self.name} not invertible")
        self.inverted += 1


class CopyTool(CounterTool):
    """
    A mock copy tool working over an in-memory filesystem, to illustrate invertibility.
    """

    def __init__(self, fs: Dict[str, str], name: str = "copy", invertible: bool = True, should_fail: bool = False):
        super().__init__(name=name, invertible=invertible, should_fail=should_fail)
        self.fs = fs
        self._undo_stack: List[Tuple[str, Optional[str]]] = []

    def apply(self, args: Dict[str, Any]) -> Dict[str, Any]:
        res = super().apply(args)
        if res["status"] != "success":
            return res
        src = args["from"]
        dst = args["to"]
        prev = self.fs.get(dst)
        self._undo_stack.append((dst, prev))
        self.fs[dst] = self.fs.get(src, "")
        return res

    def invert(self, args: Dict[str, Any]) -> None:
        super().invert(args)
        if not self._undo_stack:
            return
        dst, prev = self._undo_stack.pop()
        if prev is None:
            self.fs.pop(dst, None)
        else:
            self.fs[dst] = prev

