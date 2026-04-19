"""
NFA builder.
Pipeline: regex → Thompson fragment → serialize → prune → simplify.
Imports from thompson_nfa.py only.

Fix: passthrough elimination now checks both outgoing AND incoming
real transitions before removing a state, preventing states like
the `a*` loop state from being incorrectly deleted.
"""

from collections import deque
from services.thompson_nfa import build_fragment, serialize_fragment


# ── Reachability pruning ──────────────────────────────────────

def _prune(nfa: dict) -> dict:
    """Remove states not reachable from start_state."""
    reachable = set()
    q = deque([nfa["start_state"]])
    while q:
        s = q.popleft()
        if s in reachable:
            continue
        reachable.add(s)
        for targets in nfa["transitions"].get(s, {}).values():
            for t in targets:
                if t not in reachable:
                    q.append(t)

    new_trans = {}
    for s, paths in nfa["transitions"].items():
        if s not in reachable:
            continue
        new_trans[s] = {}
        for sym, tgts in paths.items():
            kept = [t for t in tgts if t in reachable]
            if kept:
                new_trans[s][sym] = kept

    return {
        "states":        sorted(s for s in nfa["states"] if s in reachable),
        "alphabet":      nfa["alphabet"],
        "transitions":   new_trans,
        "start_state":   nfa["start_state"],
        "accept_states": [s for s in nfa["accept_states"] if s in reachable],
    }


# ── Compute which states are real-transition targets ──────────

def _real_targets(trans: dict) -> set:
    """
    Return the set of all states that are the destination of at least
    one real (non-ε) transition anywhere in the automaton.
    These states have semantic meaning and must not be eliminated.
    """
    targets = set()
    for paths in trans.values():
        for sym, tgts in paths.items():
            if sym != "ε":
                targets.update(tgts)
    return targets


# ── Passthrough check ─────────────────────────────────────────

def _is_passthrough(state, trans, start, accepts, real_target_set) -> bool:
    """
    A state is an ε-passthrough — safe to eliminate — only when ALL of:
      1. Not the start state
      2. Not an accept state
      3. Has no real (non-ε) outgoing transitions
      4. Is NOT the target of any real transition from another state
         (if it were, removing it would sever a real edge's destination)
    """
    if state == start or state in accepts:
        return False
    # Has real outgoing transitions → semantically meaningful, keep it
    has_real_out = any(
        sym != "ε" and tgts
        for sym, tgts in trans.get(state, {}).items()
    )
    if has_real_out:
        return False
    # Is a real-transition target → something real points here, keep it
    if state in real_target_set:
        return False
    return True


# ── ε-passthrough elimination ─────────────────────────────────

def _simplify(nfa: dict) -> dict:
    """
    Eliminate ε-passthrough states iteratively.

    Only removes states that are pure ε-relays with no semantic role:
    - no real outgoing transitions
    - not targeted by any real transition
    - not start, not accept

    For each eliminated state T:
      Every predecessor that had an ε-edge to T gets that edge
      replaced with direct ε-edges to T's own ε-successors.
    """
    start   = nfa["start_state"]
    accepts = set(nfa["accept_states"])

    # Deep-copy transitions
    trans = {}
    for s, paths in nfa["transitions"].items():
        trans[s] = {sym: list(tgts) for sym, tgts in paths.items()}

    states = set(nfa["states"])
    for s in states:
        trans.setdefault(s, {})

    changed = True
    while changed:
        changed = False

        # Recompute real targets on every iteration (state set changes)
        rt = _real_targets(trans)

        target = next(
            (s for s in sorted(states)
             if _is_passthrough(s, trans, start, accepts, rt)),
            None
        )
        if target is None:
            break

        eps_successors = [
            t for t in trans.get(target, {}).get("ε", [])
            if t != target
        ]

        # Rewire predecessors
        for src in sorted(states):
            if src == target:
                continue
            eps_out = trans.get(src, {}).get("ε", [])
            if target not in eps_out:
                continue
            new_eps = [t for t in eps_out if t != target]
            for succ in eps_successors:
                if succ not in new_eps:
                    new_eps.append(succ)
            if new_eps:
                trans[src]["ε"] = new_eps
            else:
                trans[src].pop("ε", None)

        states.discard(target)
        trans.pop(target, None)
        changed = True

    # Safety: start and accepts must always survive
    states.add(start)
    states.update(accepts)
    for s in states:
        trans.setdefault(s, {})

    # Remove dangling references to deleted states
    clean_trans = {}
    for s in states:
        clean_trans[s] = {}
        for sym, tgts in trans.get(s, {}).items():
            kept = [t for t in tgts if t in states]
            if kept:
                clean_trans[s][sym] = kept

    # Recompute alphabet from surviving transitions
    alphabet = sorted({
        sym for paths in clean_trans.values()
        for sym in paths if sym != "ε"
    })

    result = {
        "states":        sorted(states),
        "alphabet":      alphabet,
        "transitions":   clean_trans,
        "start_state":   start,
        "accept_states": sorted(accepts & states),
    }
    return _prune(result)


# ── Public entry point ────────────────────────────────────────

def build_nfa(regex: str) -> dict:
    """
    regex → simplified ε-NFA.
    Steps:
      1. Thompson's construction (via thompson_nfa.py)
      2. Serialize fragment to standard dict format
      3. Prune unreachable states
      4. Eliminate safe ε-passthrough states
      5. Final reachability prune
    """
    frag   = build_fragment(regex)
    raw    = serialize_fragment(frag)
    pruned = _prune(raw)
    return _simplify(pruned)