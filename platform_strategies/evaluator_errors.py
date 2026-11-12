"""Shared strategy-level error types.

Kept outside any one strategy package so both the ported TrendSpider
interpreter and the API layer can refer to the same exception without
importing each other.
"""


class StrategyUnsupported(Exception):
    """A strategy exists and is registered, but cannot be run faithfully.

    Raised rather than degrading to a partial interpretation: a backtest
    that silently ignored a condition it did not understand would look
    perfectly plausible and be wrong.
    """
