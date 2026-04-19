import uuid
from datetime import datetime


class AutomataResult:
    def __init__(self, regex, mode, states, alphabet, transitions, start_state, accept_states):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.regex = regex
        self.mode = mode
        self.states = states
        self.alphabet = alphabet
        self.transitions = transitions
        self.start_state = start_state
        self.accept_states = accept_states

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "regex": self.regex,
            "mode": self.mode,
            "states": self.states,
            "alphabet": self.alphabet,
            "transitions": self.transitions,
            "start_state": self.start_state,
            "accept_states": self.accept_states,
        }