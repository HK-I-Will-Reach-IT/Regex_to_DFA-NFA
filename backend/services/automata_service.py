from services.nfa_builder import build_nfa
from services.dfa_builder import build_dfa
from models.automata_model import AutomataResult
from models.store import Store


class AutomataService:
    def __init__(self):
        self._store = Store()

    def generate(self, regex: str, mode: str) -> dict:
        if mode == "dfa":
            automaton = build_dfa(regex)
        else:
            automaton = build_nfa(regex)

        result = AutomataResult(
            regex=regex,
            mode=mode,
            states=automaton["states"],
            alphabet=automaton["alphabet"],
            transitions=automaton["transitions"],
            start_state=automaton["start_state"],
            accept_states=automaton["accept_states"],
        )
        self._store.save(result.to_dict())
        return result.to_dict()

    def history(self) -> list:
        return self._store.all()

    def clear_history(self):
        self._store.clear()