"""Compatibility shim for rich library, falling back cleanly to standard terminal print."""

import re

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

    class Console:
        def print(self, *args, **kwargs):
            text = " ".join(str(a) for a in args)
            cleaned = re.sub(r'\[/?[a-zA-Z0-9_ #]+\]', '', text)
            print(cleaned)

    class Table:
        def __init__(self, title=""):
            self.title = title
            self.columns = []
            self.rows = []

        def add_column(self, title, *args, **kwargs):
            self.columns.append(title)

        def add_row(self, *row, **kwargs):
            self.rows.append(row)

    class Panel:
        @classmethod
        def fit(cls, content):
            return f"\n{'='*60}\n{content}\n{'='*60}\n"
