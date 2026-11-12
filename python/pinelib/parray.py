"""
Pine ``array.*`` over Python lists, with Pine's semantics where they differ from Python:
  * out-of-range indices are runtime ERRORS in Pine (Python would wrap negatives) — v6 allows
    negative indices counting from the end, v5 does not;
  * statistics ignore na; ``array.sort`` is numeric; ``array.max(id, nth)`` exists.
"""

from __future__ import annotations

import math
import statistics
from typing import Any

from .core import NA, fl

NEGATIVE_INDEX_OK = True        # set False for v5 scripts that must error on negatives


def new(size: int = 0, initial_value: Any = NA) -> list:
    return [initial_value] * int(size)


new_float = new_int = new_bool = new_string = new_line = new_box = new_label = new
from_ = lambda *values: list(values)  # noqa: E731  (Pine array.from)


def _ix(a: list, i: Any) -> int:
    k = int(fl(i))
    if k < 0:
        if not NEGATIVE_INDEX_OK or -k > len(a):
            raise IndexError(f"array index {k} out of bounds, size {len(a)}")
        return len(a) + k
    if k >= len(a):
        raise IndexError(f"array index {k} out of bounds, size {len(a)}")
    return k


def get(a: list, i: Any) -> Any: return a[_ix(a, i)]
def set(a: list, i: Any, v: Any) -> None: a[_ix(a, i)] = v  # noqa: A001
def size(a: list) -> int: return len(a)
def push(a: list, v: Any) -> None: a.append(v)
def unshift(a: list, v: Any) -> None: a.insert(0, v)
def insert(a: list, i: Any, v: Any) -> None: a.insert(int(fl(i)), v)
def clear(a: list) -> None: a.clear()
def copy(a: list) -> list: return list(a)
def concat(a: list, b: list) -> list:
    a.extend(b)
    return a
def reverse(a: list) -> None: a.reverse()
def includes(a: list, v: Any) -> bool: return v in a
def indexof(a: list, v: Any) -> int: return a.index(v) if v in a else -1
def lastindexof(a: list, v: Any) -> int: return len(a) - 1 - a[::-1].index(v) if v in a else -1
def first(a: list) -> Any: return get(a, 0)
def last(a: list) -> Any: return get(a, len(a) - 1)
def slice(a: list, start: Any, end: Any) -> list: return a[int(fl(start)):int(fl(end))]  # noqa: A001
def fill(a: list, v: Any, index_from: int = 0, index_to: int | None = None) -> None:
    for k in range(int(index_from), len(a) if index_to is None else int(index_to)):
        a[k] = v


def pop(a: list) -> Any:
    if not a:
        raise IndexError("array.pop on an empty array")
    return a.pop()


def shift(a: list) -> Any:
    if not a:
        raise IndexError("array.shift on an empty array")
    return a.pop(0)


def remove(a: list, i: Any) -> Any:
    return a.pop(_ix(a, i))


def _vals(a: list) -> list[float]:
    return [fl(x) for x in a if x is not None and fl(x) == fl(x)]


def sum(a: list) -> float:  # noqa: A001
    v = _vals(a)
    return math.fsum(v) if v else NA


def avg(a: list) -> float:
    v = _vals(a)
    return math.fsum(v) / len(v) if v else NA


def max(a: list, nth: int = 0) -> float:  # noqa: A001
    v = sorted(_vals(a), reverse=True)
    return v[int(nth)] if len(v) > int(nth) else NA


def min(a: list, nth: int = 0) -> float:  # noqa: A001
    v = sorted(_vals(a))
    return v[int(nth)] if len(v) > int(nth) else NA


def range_(a: list) -> float:
    v = _vals(a)
    return _bmax(v) - _bmin(v) if v else NA


def _bmax(v):
    m = v[0]
    for x in v[1:]:
        if x > m:
            m = x
    return m


def _bmin(v):
    m = v[0]
    for x in v[1:]:
        if x < m:
            m = x
    return m


def median(a: list) -> float:
    v = _vals(a)
    return statistics.median(v) if v else NA


def mode(a: list) -> float:
    v = _vals(a)
    if not v:
        return NA
    counts: dict = {}
    for x in v:
        counts[x] = counts.get(x, 0) + 1
    top = _bmax(list(counts.values()))
    return _bmin([k for k, c in counts.items() if c == top])


def stdev(a: list, biased: bool = True) -> float:
    v = _vals(a)
    if len(v) < (1 if biased else 2):
        return NA
    return statistics.pstdev(v) if biased else statistics.stdev(v)


def variance(a: list, biased: bool = True) -> float:
    v = _vals(a)
    if len(v) < (1 if biased else 2):
        return NA
    return statistics.pvariance(v) if biased else statistics.variance(v)


def sort(a: list, order: str = "ascending") -> None:
    a.sort(key=lambda x: (fl(x) != fl(x), fl(x)), reverse=(order == "descending"))


def sort_indices(a: list, order: str = "ascending") -> list[int]:
    idx = list(range(len(a)))
    idx.sort(key=lambda k: fl(a[k]), reverse=(order == "descending"))
    return idx


def percentrank(a: list, i: Any) -> float:
    v = fl(get(a, i))
    vals = _vals(a)
    return 100.0 * __import__("builtins").sum(1 for x in vals if x <= v) / len(vals) if vals else NA


def join(a: list, separator: str = ",") -> str:
    return separator.join(str(x) for x in a)
