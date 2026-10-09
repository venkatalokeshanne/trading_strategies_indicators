"""
Pine drawing objects: line, box, label, linefill, polyline, table.

They matter beyond looks: scripts read them back (``box.get_top`` for mitigation,
``line.get_price`` for breakouts), and Pine deletes the OLDEST objects once a script exceeds
its ``max_lines_count`` / ``max_boxes_count`` / ``max_labels_count`` (default 50, max 500).
Each object is a plain record; the script's ``Drawings`` registry enforces the limits and is
returned with the run's outputs for a frontend to render.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .core import NA, fl


@dataclass(eq=False)
class Line:
    x1: float
    y1: float
    x2: float
    y2: float
    xloc: str = "bar_index"
    extend: str = "none"
    color: Any = None
    style: str = "solid"
    width: int = 1
    deleted: bool = False

    def get_price(self, x: Any) -> float:
        """Price of the (extended) line at bar ``x`` — Pine's line.get_price."""
        x = fl(x)
        if self.x2 == self.x1:
            return self.y1
        return self.y1 + (self.y2 - self.y1) * (x - self.x1) / (self.x2 - self.x1)


@dataclass(eq=False)
class Box:
    left: float
    top: float
    right: float
    bottom: float
    xloc: str = "bar_index"
    extend: str = "none"
    border_color: Any = None
    bgcolor: Any = None
    text: str = ""
    deleted: bool = False


@dataclass(eq=False)
class Label:
    x: float
    y: float
    text: str = ""
    xloc: str = "bar_index"
    yloc: str = "price"
    color: Any = None
    style: str = "label_down"
    textcolor: Any = None
    size: str = "normal"
    tooltip: str = ""
    deleted: bool = False


@dataclass(eq=False)
class Linefill:
    line1: Line
    line2: Line
    color: Any = None
    deleted: bool = False


@dataclass(eq=False)
class Polyline:
    points: list
    closed: bool = False
    deleted: bool = False


@dataclass(eq=False)
class Table:
    position: str
    columns: int
    rows: int
    cells: dict = field(default_factory=dict)
    deleted: bool = False

    def cell(self, column: int, row: int, text: str = "", **kw: Any) -> None:
        self.cells[(int(column), int(row))] = {"text": str(text), **kw}

    def cell_set_text(self, column: int, row: int, text: str) -> None:
        self.cells.setdefault((int(column), int(row)), {})["text"] = str(text)

    def clear(self, *a: Any) -> None:
        self.cells.clear()


class Drawings:
    """Per-run registry with Pine's max-count garbage collection (oldest first)."""

    def __init__(self, max_lines: int = 50, max_boxes: int = 50, max_labels: int = 50,
                 max_polylines: int = 50) -> None:
        self.limits = {"line": max_lines, "box": max_boxes, "label": max_labels, "polyline": max_polylines}
        self.live: dict[str, list] = {"line": [], "box": [], "label": [], "polyline": [], "linefill": [], "table": []}

    def _add(self, kind: str, obj: Any) -> Any:
        lst = self.live[kind]
        lst.append(obj)
        lim = self.limits.get(kind)
        while lim is not None and len(lst) > lim:
            old = lst.pop(0)
            old.deleted = True
        return obj

    def delete(self, obj: Any) -> None:
        if obj is None or (isinstance(obj, float) and math.isnan(obj)):
            return
        obj.deleted = True
        for lst in self.live.values():
            if obj in lst:
                lst.remove(obj)

    # constructors — Pine's names
    def line_new(self, x1, y1, x2, y2, xloc="bar_index", extend="none", color=None, style="solid", width=1):
        return self._add("line", Line(fl(x1), fl(y1), fl(x2), fl(y2), xloc, extend, color, style, int(width)))

    def box_new(self, left, top, right, bottom, border_color=None, bgcolor=None, xloc="bar_index",
                extend="none", text="", **kw):
        return self._add("box", Box(fl(left), fl(top), fl(right), fl(bottom), xloc, extend, border_color,
                                    bgcolor, str(text)))

    def label_new(self, x, y, text="", xloc="bar_index", yloc="price", color=None, style="label_down",
                  textcolor=None, size="normal", tooltip="", **kw):
        return self._add("label", Label(fl(x), fl(y), str(text), xloc, yloc, color, style, textcolor, size, tooltip))

    def linefill_new(self, line1, line2, color=None):
        return self._add("linefill", Linefill(line1, line2, color))

    def polyline_new(self, points, closed=False, **kw):
        return self._add("polyline", Polyline(list(points), closed))

    def table_new(self, position, columns, rows, **kw):
        return self._add("table", Table(position, int(columns), int(rows)))

    def all(self, kind: str) -> list:
        return list(self.live[kind])

    def export(self) -> dict:
        def row(o):
            d = {k: v for k, v in o.__dict__.items() if k != "deleted"}
            if isinstance(o, Linefill):
                d = {"color": o.color}
            if isinstance(o, Table):
                d["cells"] = [{"column": c, "row": r, **v} for (c, r), v in o.cells.items()]
            return d
        return {k: [row(o) for o in v] for k, v in self.live.items()}
