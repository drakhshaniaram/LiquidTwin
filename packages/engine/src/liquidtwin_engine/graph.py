"""Directed multigraph of a terminal. Every element gives a forward arc and, unless one-way, a reverse arc.

Pumps always get a reverse arc so routing can explain ONE_WAY_PUMP instead of silently missing it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .document import Terminal


@dataclass(frozen=True)
class Arc:
    element_id: str
    u: str
    v: str
    reversed: bool


@dataclass
class TerminalGraph:
    terminal: Terminal
    arcs: list[Arc] = field(default_factory=list)
    out: dict[str, list[Arc]] = field(default_factory=dict)


def build_graph(t: Terminal) -> TerminalGraph:
    g = TerminalGraph(terminal=t)
    for el in t.elements.values():  # elements are already in stable natural-id order
        pairs = [(el.from_node, el.to_node, False)]
        if el.bidirectional or el.type == "PUMP":
            pairs.append((el.to_node, el.from_node, True))
        for u, v, rev in pairs:
            arc = Arc(el.id, u, v, rev)
            g.arcs.append(arc)
            g.out.setdefault(u, []).append(arc)
    return g
