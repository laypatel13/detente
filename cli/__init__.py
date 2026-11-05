"""Detente in your terminal: `detente --help`.

This folder is the `detente` command. It ships as the `detente` package with the laptop side of the
engine (`pilot/`), and the only part of the tower it needs, the code reader in backend/contracts.py.
"""


def main() -> None:
    from .app import app

    app(prog_name="detente")
