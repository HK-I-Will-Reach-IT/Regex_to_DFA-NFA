"""
Thompson's construction core.
Converts a postfix token list into a raw NFA fragment.
Nothing in this file knows about NFA simplification or DFA construction.
"""

from .regex_parser import to_postfix

_state_counter = 0


def _new_state() -> str:
    global _state_counter
    s = f"q{_state_counter}"
    _state_counter += 1
    return s


def reset_counter():
    global _state_counter
    _state_counter = 0


def add_trans(transitions, frm, sym, to):
    transitions.setdefault(frm, {}).setdefault(sym, [])
    if to not in transitions[frm][sym]:
        transitions[frm][sym].append(to)


def fragment(start, accept, states, transitions, symbols=None):
    return {
        "start":       start,
        "accept":      accept,
        "states":      states,
        "transitions": transitions,
        "symbols":     symbols or set(),
    }


# ── Primitive builders ────────────────────────────────────────

def literal(ch):
    s0, s1 = _new_state(), _new_state()
    trans = {}
    add_trans(trans, s0, ch, s1)
    return fragment(s0, s1, {s0, s1}, trans, {ch})


def concat(a, b):
    trans = {**a["transitions"]}
    for state, paths in b["transitions"].items():
        actual = a["accept"] if state == b["start"] else state
        for sym, targets in paths.items():
            for tgt in targets:
                real_tgt = a["accept"] if tgt == b["start"] else tgt
                add_trans(trans, actual, sym, real_tgt)
    states = (a["states"] | b["states"]) - {b["start"]}
    return fragment(a["start"], b["accept"], states, trans, a["symbols"] | b["symbols"])


def union(a, b):
    s0, s1 = _new_state(), _new_state()
    trans = {**a["transitions"], **b["transitions"]}
    add_trans(trans, s0, "ε", a["start"])
    add_trans(trans, s0, "ε", b["start"])
    add_trans(trans, a["accept"], "ε", s1)
    add_trans(trans, b["accept"], "ε", s1)
    states = a["states"] | b["states"] | {s0, s1}
    return fragment(s0, s1, states, trans, a["symbols"] | b["symbols"])


def kleene(a):
    s0, s1 = _new_state(), _new_state()
    trans = {**a["transitions"]}
    add_trans(trans, s0, "ε", a["start"])
    add_trans(trans, s0, "ε", s1)
    add_trans(trans, a["accept"], "ε", a["start"])
    add_trans(trans, a["accept"], "ε", s1)
    states = a["states"] | {s0, s1}
    return fragment(s0, s1, states, trans, a["symbols"])


def one_or_more(a):
    return concat(a, kleene(copy_fragment(a)))


def zero_or_one(a):
    s0, s1 = _new_state(), _new_state()
    trans = {**a["transitions"]}
    add_trans(trans, s0, "ε", a["start"])
    add_trans(trans, s0, "ε", s1)
    add_trans(trans, a["accept"], "ε", s1)
    states = a["states"] | {s0, s1}
    return fragment(s0, s1, states, trans, a["symbols"])


def copy_fragment(frag):
    mapping = {s: _new_state() for s in frag["states"]}
    trans = {}
    for state, paths in frag["transitions"].items():
        for sym, targets in paths.items():
            for tgt in targets:
                add_trans(trans, mapping[state], sym, mapping[tgt])
    return fragment(
        mapping[frag["start"]],
        mapping[frag["accept"]],
        set(mapping.values()),
        trans,
        frag["symbols"].copy(),
    )


def expand_class(tok):
    inner = tok[1:-1]
    chars = set()
    i = 0
    while i < len(inner):
        if i + 2 < len(inner) and inner[i + 1] == "-":
            for c in range(ord(inner[i]), ord(inner[i + 2]) + 1):
                chars.add(chr(c))
            i += 3
        else:
            chars.add(inner[i])
            i += 1
    return chars


# ── Main entry: regex → raw fragment ─────────────────────────

def build_fragment(regex: str):
    """
    Parse regex and return a raw Thompson fragment dict.
    Caller is responsible for serialization and any further processing.
    """
    reset_counter()
    postfix = to_postfix(regex)
    stack   = []

    for tok in postfix:
        if tok == ".":
            b, a = stack.pop(), stack.pop()
            stack.append(concat(a, b))
        elif tok == "|":
            b, a = stack.pop(), stack.pop()
            stack.append(union(a, b))
        elif tok == "*":
            stack.append(kleene(stack.pop()))
        elif tok == "+":
            stack.append(one_or_more(stack.pop()))
        elif tok == "?":
            stack.append(zero_or_one(stack.pop()))
        elif tok.startswith("[") and tok.endswith("]"):
            chars = expand_class(tok)
            frags = [literal(c) for c in sorted(chars)]
            base  = frags[0]
            for f in frags[1:]:
                base = union(base, f)
            stack.append(base)
        elif tok.startswith("\\") and len(tok) == 2:
            stack.append(literal(tok[1]))
        else:
            stack.append(literal(tok))

    if not stack:
        raise ValueError("Empty regex")
    return stack.pop()


def serialize_fragment(frag) -> dict:
    """
    Convert a raw fragment into the standard automaton dict format
    (states, alphabet, transitions, start_state, accept_states).
    """
    states_list = sorted(frag["states"])
    alphabet    = sorted(frag["symbols"])
    transitions = {}
    for s in states_list:
        transitions[s] = {}
        for sym, tgts in frag["transitions"].get(s, {}).items():
            transitions[s][sym] = sorted(tgts)
    return {
        "states":        states_list,
        "alphabet":      alphabet,
        "transitions":   transitions,
        "start_state":   frag["start"],
        "accept_states": [frag["accept"]],
    }