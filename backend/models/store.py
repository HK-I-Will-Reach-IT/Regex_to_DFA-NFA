"""In-memory JSON store (list of dicts)."""


class Store:
    _data: list = []   # class-level so it persists across service instantiations

    def save(self, record: dict):
        Store._data.append(record)

    def all(self) -> list:
        return list(Store._data)

    def clear(self):
        Store._data.clear()