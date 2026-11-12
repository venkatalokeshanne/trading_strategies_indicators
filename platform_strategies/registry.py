"""
Strategy registry singleton.

Importing/calling discover_strategies() triggers discovery of every
strategy folder under app/strategies/ — so adding a new strategy is
"create one folder containing a strategy.py that registers itself,"
with no edits needed here or anywhere else.
"""

from app.core.registry import Registry, discover_package
from app.domain.interfaces.strategy import Strategy

strategy_registry: Registry[Strategy] = Registry(kind="strategy")


def get_strategy(name: str) -> Strategy:
    cls = strategy_registry.get(name)
    return cls()


def list_strategies() -> list[dict]:
    """Return metadata for every registered strategy (for the API/UI Strategy Library)."""
    result = []
    for name, cls in strategy_registry.all().items():
        meta = cls().metadata
        result.append(
            {
                "name": meta.name,
                "display_name": meta.display_name,
                "description": meta.description,
                "category": meta.category,
                "indicators_used": meta.indicators_used,
                "default_params": meta.default_params,
                "entry_conditions": meta.entry_conditions,
                "exit_conditions": meta.exit_conditions,
                "live_caution": meta.live_caution,
            }
        )
    return sorted(result, key=lambda x: x["name"])


def discover_strategies() -> None:
    discover_package("app.strategies")
