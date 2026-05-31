from __future__ import annotations

from source import constants


# read a .sql file from commands/
def load_sql(name: str) -> str:
    path = constants.COMMANDS / name
    if not path.exists():
        raise FileNotFoundError(f"SQL File Not Found: {path}")
    return path.read_text()
