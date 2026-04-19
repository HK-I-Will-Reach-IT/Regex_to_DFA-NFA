"""
DFA builder.
Pipeline: regex → Thompson fragment → serialize → subset construction
          → reachability prune → Hopcroft minimization.
Imports from thompson.py only. Knows nothing about NFA simplification.
"""

from collections import deque
from backend.services.thompson_dfa import build_fragment, serialize_fragment


# ── ε-closure & move ─────────────────────────────────────────

def _epsilon_closure(states, transitions):
    closure = set(states)
    queue   = deque(states)
    while queue:
        s = queue.popleft()
        for nxt in transitions.get(s, {}).get("ε", []):
            if nxt not in closure:
                closure.add(nxt)
                queue.append(nxt)
    return frozenset(closure)


def _move(states, symbol, transitions):
    result = set()
    for s in states:
        for t in transitions.get(s, {}).get(symbol, []):
            result.add(t)
    return frozenset(result)


# ── Subset construction ───────────────────────────────────────

def _subset_construction(nfa: dict) -> dict:
    """
    Standard subset construction.
    Transition values are plain strings (single DFA target) at this stage.
    """
    trans    = nfa["transitions"]
    alphabet = sorted({
        sym for paths in trans.values()
        for sym in paths if sym != "ε"
    })
    accept_set = set(nfa["accept_states"])

    start_closure = _epsilon_closure([nfa["start_state"]], trans)

    dfa_states = {}   # frozenset → label
    dfa_trans  = {}   # label    → {sym → label}
    dfa_accept = set()
    counter    = [0]

    def name_of(fs):
        if fs not in dfa_states:
            dfa_states[fs] = f"D{counter[0]}"
            counter[0] += 1
        return dfa_states[fs]

    name_of(start_closure)
    queue   = deque([start_closure])
    visited = {start_closure}

    while queue:
        current  = queue.popleft()
        cur_name = name_of(current)
        dfa_trans[cur_name] = {}

        for sym in alphabet:
            moved = _move(current, sym, trans)
            if not moved:
                continue
            closure   = _epsilon_closure(moved, trans)
            next_name = name_of(closure)
            dfa_trans[cur_name][sym] = next_name   # plain string
            if closure not in visited:
                visited.add(closure)
                queue.append(closure)

        if current & accept_set:
            dfa_accept.add(cur_name)

    return {
        "states":        list(dfa_states.values()),
        "alphabet":      alphabet,
        "transitions":   dfa_trans,                # str → {sym → str}
        "start_state":   name_of(start_closure),
        "accept_states": list(dfa_accept),
    }


# ── Reachability pruning ──────────────────────────────────────

def _prune_reachable(dfa: dict) -> dict:
    reachable = set()
    queue     = deque([dfa["start_state"]])
    while queue:
        s = queue.popleft()
        if s in reachable:
            continue
        reachable.add(s)
        for nxt in dfa["transitions"].get(s, {}).values():
            if nxt not in reachable:
                queue.append(nxt)

    new_trans = {
        s: {sym: nxt for sym, nxt in paths.items() if nxt in reachable}
        for s, paths in dfa["transitions"].items()
        if s in reachable
    }
    return {
        "states":        [s for s in dfa["states"] if s in reachable],
        "alphabet":      dfa["alphabet"],
        "transitions":   new_trans,
        "start_state":   dfa["start_state"],
        "accept_states": [s for s in dfa["accept_states"] if s in reachable],
    }


# ── Hopcroft minimization ─────────────────────────────────────

def _relabel(states, accept, trans, start, alphabet, prefix="S") -> dict:
    """Rename states to S0, S1, ... and serialize targets as lists."""
    label      = {s: f"{prefix}{i}" for i, s in enumerate(sorted(states))}
    new_start  = label[start]
    new_accept = sorted({label[s] for s in accept if s in label})
    new_states = sorted(label.values())
    serial     = {}
    for s in states:
        ls = label[s]
        serial[ls] = {}
        for sym, nxt in trans.get(s, {}).items():
            if nxt in label:
                serial[ls][sym] = [label[nxt]]   # list format, consistent with NFA
    for ls in new_states:
        serial.setdefault(ls, {})
    return {
        "states":        new_states,
        "alphabet":      alphabet,
        "transitions":   serial,
        "start_state":   new_start,
        "accept_states": new_accept,
    }


def _minimize(dfa: dict) -> dict:
    alphabet   = dfa["alphabet"]
    states     = set(dfa["states"])
    accept     = set(dfa["accept_states"])
    non_accept = states - accept
    trans      = dfa["transitions"]   # str → {sym → str}

    # Initial partition
    P = [p for p in [frozenset(accept), frozenset(non_accept)] if p]

    # Only one partition class → nothing to split, just relabel
    if len(P) == 1:
        return _relabel(states, accept, trans, dfa["start_state"], alphabet)

    W = list(P)

    while W:
        A = W.pop()
        for sym in alphabet:
            X = frozenset(s for s in states if trans.get(s, {}).get(sym) in A)
            if not X:
                continue
            new_P = []
            for Y in P:
                inter = Y & X
                diff  = Y - X
                if inter and diff:
                    new_P.extend([inter, diff])
                    if Y in W:
                        W.remove(Y)
                        W.extend([inter, diff])
                    else:
                        W.append(inter if len(inter) <= len(diff) else diff)
                else:
                    new_P.append(Y)
            P = new_P

    # Map each state to its group's representative
    rep = {}
    for group in P:
        r = min(group)
        for s in group:
            rep[s] = r

    # Build minimized transitions (one representative per group)
    min_trans = {}
    for s in states:
        r = rep[s]
        min_trans.setdefault(r, {})
        for sym, nxt in trans.get(s, {}).items():
            min_trans[r][sym] = rep[nxt]

    min_states = set(rep.values())
    min_accept = {rep[s] for s in accept}
    min_start  = rep[dfa["start_state"]]

    return _relabel(min_states, min_accept, min_trans, min_start, alphabet)


# ── Public entry point ────────────────────────────────────────

def build_dfa(regex: str) -> dict:
    """
    regex → minimal DFA.
    Steps: Thompson → serialize → subset construction
           → prune unreachable → Hopcroft minimization.
    Completely independent of nfa_builder.py.
    """
    frag   = build_fragment(regex)
    nfa    = serialize_fragment(frag)
    raw    = _subset_construction(nfa)
    pruned = _prune_reachable(raw)
    return _minimize(pruned)