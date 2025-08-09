from __future__ import annotations
import os, sys
import pytest
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
from speculatools_langchain.invertible import (
    SpeculativeExecutor,
    CounterTool,
    CopyTool,
)


def test_all_invertible_all_success_rolls_no_undo():
    exec = SpeculativeExecutor()
    t1 = CounterTool("one", invertible=True)
    t2 = CounterTool("two", invertible=True)
    t3 = CounterTool("three", invertible=True)

    results, err = exec.run_plan([(t1, {}), (t2, {}), (t3, {})])

    assert err is None
    assert [name for name, _ in results] == ["one", "two", "three"]
    assert (t1.applied, t2.applied, t3.applied) == (1, 1, 1)
    assert (t1.inverted, t2.inverted, t3.inverted) == (0, 0, 0)


def test_invert_on_failure_middle_step():
    exec = SpeculativeExecutor()
    t1 = CounterTool("one", invertible=True)
    t2 = CounterTool("two", invertible=True, should_fail=True)
    t3 = CounterTool("three", invertible=True)

    results, err = exec.run_plan([(t1, {}), (t2, {}), (t3, {})])

    assert err == 1  # failure at t2
    assert [name for name, _ in results] == ["one", "two"]
    assert (t1.applied, t2.applied, t3.applied) == (1, 1, 0)
    assert (t1.inverted, t2.inverted, t3.inverted) == (1, 0, 0)


def test_non_invertible_limits_window():
    exec = SpeculativeExecutor()
    t1 = CounterTool("one", invertible=True)
    t2 = CounterTool("two", invertible=False)
    t3 = CounterTool("three", invertible=True)

    results, err = exec.run_plan([(t1, {}), (t2, {}), (t3, {})])

    assert err is None
    assert [name for name, _ in results] == ["one"]
    assert (t1.applied, t2.applied, t3.applied) == (1, 0, 0)


def test_copy_tool_inverts_filesystem():
    fs = {"/a.txt": "AAA"}
    copy = CopyTool(fs, invertible=True)

    exec = SpeculativeExecutor()
    results, err = exec.run_plan([(copy, {"from": "/a.txt", "to": "/b.txt"})])

    assert err is None
    assert fs["/b.txt"] == "AAA"

    copy.should_fail = True
    results2, err2 = exec.run_plan([(copy, {"from": "/a.txt", "to": "/c.txt"})])
    assert err2 == 0
    assert "/c.txt" not in fs

