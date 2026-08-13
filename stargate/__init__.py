"""The workshop package.

This grows over the course of session 1. By the end of notebook 05 it holds a
working (if naive) agent over the declassified corpus; session 2 adds a SQL
agent, a team, and the evaluation machinery.

Nothing here imports heavy dependencies at module level — importing
`stargate` must stay fast and must not require API keys, so that the test
suite and `scripts/check.py` can run offline.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
