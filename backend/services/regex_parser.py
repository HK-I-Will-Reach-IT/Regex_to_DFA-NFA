"""
Converts a regex string into a postfix expression using the shunting-yard
algorithm. Supported operators: * (Kleene star), + (one-or-more),
? (zero-or-one), | (alternation), . (explicit concatenation).
Character classes, escape sequences, and grouping via () are supported.
"""

PRECEDENCE = {"*": 3, "+": 3, "?": 3, ".": 2, "|": 1}
LEFT_ASSOC = {"*", "+", "?", ".", "|"}


def add_concat(regex: str) -> str:
    """Insert explicit '.' concatenation operators where implied."""
    output = []
    binary_ops = {"|", "."}
    postfix_unary = {"*", "+", "?"}

    i = 0
    tokens = _tokenize(regex)
    for idx, tok in enumerate(tokens):
        output.append(tok)
        if idx + 1 < len(tokens):
            nxt = tokens[idx + 1]
            left_ok = tok not in binary_ops and tok != "("
            right_ok = nxt not in binary_ops and nxt not in postfix_unary and nxt != ")"
            if left_ok and right_ok:
                output.append(".")
    return output


def _tokenize(regex: str):
    tokens = []
    i = 0
    while i < len(regex):
        ch = regex[i]
        if ch == "\\":
            if i + 1 < len(regex):
                tokens.append(regex[i : i + 2])
                i += 2
            else:
                raise ValueError("Trailing backslash in regex")
        elif ch == "[":
            j = i + 1
            while j < len(regex) and regex[j] != "]":
                j += 1
            if j >= len(regex):
                raise ValueError("Unclosed character class '['")
            tokens.append(regex[i : j + 1])
            i = j + 1
        else:
            tokens.append(ch)
            i += 1
    return tokens


def to_postfix(regex: str) -> list:
    """Return postfix token list from infix regex string."""
    tokens = add_concat(regex)
    output = []
    stack = []

    for tok in tokens:
        if tok == "(":
            stack.append(tok)
        elif tok == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if not stack:
                raise ValueError("Mismatched parentheses")
            stack.pop()
        elif tok in PRECEDENCE:
            while (
                stack
                and stack[-1] != "("
                and stack[-1] in PRECEDENCE
                and PRECEDENCE[stack[-1]] >= PRECEDENCE[tok]
                and tok in LEFT_ASSOC
            ):
                output.append(stack.pop())
            stack.append(tok)
        else:
            output.append(tok)

    while stack:
        top = stack.pop()
        if top in ("(", ")"):
            raise ValueError("Mismatched parentheses")
        output.append(top)

    return output