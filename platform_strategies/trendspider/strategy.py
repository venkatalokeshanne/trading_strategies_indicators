"""
The 75 TrendSpider strategies, as QIS strategies.

Design: ONE interpreter plus 75 data files (models/*.json, extracted
straight out of TrendSpider's own Angular model by
trendspider-automation/scripts/extract_all_strategy_rules.py), rather
than 75 hand-written Python files. Hand-writing them would guarantee
drift between what TrendSpider ran and what QIS runs, and re-extracting
would mean re-writing; here a re-extraction is a drop-in file swap.

TIMEFRAME IS DYNAMIC. Every one of the 75 was verified single-timeframe
(no cross-timeframe references anywhere in the extracted trees), and
TrendSpider itself recomputed each strategy on whatever chart interval
was selected -- which is why "8/21 EMA Cross Long Daily" produces ~1
cross per 45 bars on 5m, 15m, 1H AND Daily alike. So the timeframe
baked into the model is treated purely as a DEFAULT: these strategies
run on whatever bars they are handed. Indicator periods stay fixed; only
the bars change.

Execution parity: TrendSpider strategies carry priceSource "open",
meaning a signal confirmed at a bar's close fills at the NEXT bar's
open. `recommended_execution()` returns an ExecutionConfig carrying that
plus the model's own stop-loss / take-profit / trailing-stop /
"exit after N candles" settings, so a caller can reproduce TrendSpider's
execution rather than QIS's defaults.

Strategies whose conditions this interpreter cannot yet reproduce
exactly are still registered, but declare themselves unsupported and
raise on run() -- deliberately loud, because a strategy that silently
skips a condition it did not understand would produce a plausible and
completely wrong backtest.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from app.indicators.trendspider_store._runtime.indicator import StoreScriptError

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.strategies.evaluator_errors import StrategyUnsupported
from app.strategies.registry import strategy_registry
from app.strategies.trendspider.evaluator import (
    UnsupportedCondition,
    evaluate_signal_tree,
)
from app.strategies.trendspider.indicator_map import UnsupportedIndicator

MODELS_DIR = Path(__file__).parent / "models"

# TrendSpider timeframe code -> minutes, for reporting the model's own
# default only. Nothing here constrains what a run may use.
_TF_MINUTES = {"D": 1440, "W": 10080, "M": 43200}


def _slug(name: str) -> str:
    """Stable QIS strategy name from a TrendSpider title."""
    text = name.replace("�", "-")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return f"ts_{text}"


def _default_timeframe(model: dict) -> str:
    raw = (model.get("_backtestOptions") or {}).get("timeFrame")
    if raw in _TF_MINUTES:
        return {"D": "1day", "W": "1week", "M": "1month"}[raw]
    try:
        return f"{int(raw)}min"
    except (TypeError, ValueError):
        return "1day"


def _risk_settings(model: dict) -> dict[str, Any]:
    """The model's exit conditions that are execution settings, not bar
    conditions: stop loss, take profit, trailing stop, time stop."""
    settings: dict[str, Any] = {}
    for condition in ((model.get("exitCondition") or {}).get("conditions") or []):
        kind = condition.get("type")
        value = condition.get("value")
        is_pct = (condition.get("distanceType") == "percentage")
        if kind == "stop_loss" and is_pct and value:
            settings["stop_loss_pct"] = float(value) / 100.0
        elif kind == "take_profit" and is_pct and value:
            settings["take_profit_pct"] = float(value) / 100.0
        elif kind == "trailing_stop" and is_pct and value:
            settings["trailing_stop_pct"] = float(value) / 100.0
        elif kind == "x_candles_passed" and value:
            settings["max_holding_bars"] = int(value)
    return settings


@lru_cache(maxsize=1)
def load_models() -> dict[str, dict]:
    """slug -> extracted TrendSpider model."""
    models: dict[str, dict] = {}
    for path in sorted(MODELS_DIR.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        model = record.get("model")
        if not model:
            continue
        models[_slug(record["name"])] = {"name": record["name"], **model}
    return models


class TrendSpiderStrategy(Strategy):
    """Interprets one extracted TrendSpider model. Subclasses (generated
    below) only differ by which model they carry."""

    MODEL: dict = {}
    SLUG: str = ""

    # --- metadata ---------------------------------------------------------
    @property
    def metadata(self) -> StrategyMetadata:
        model = self.MODEL
        direction = (model.get("_backtestOptions") or {}).get("strategyDirection", "long")
        risk = _risk_settings(model)
        supported, reason = self.support_status()

        exits = [f"{k.replace('_', ' ')}: {v}" for k, v in risk.items()]
        if self._has_script_exit():
            exits.append("Rule-based exit conditions (see the strategy's exit tree)")

        return StrategyMetadata(
            name=self.SLUG,
            display_name=model.get("name", self.SLUG),
            description=(
                f"Ported from TrendSpider. Authored on "
                f"{_default_timeframe(model)}, but runs on any timeframe. "
                + ("" if supported else f"UNSUPPORTED: {reason}")
            ),
            category="trendspider",
            indicators_used=sorted(self._indicator_types()),
            default_params={
                "direction": direction,
                # Reported so callers can reproduce the original run; not
                # a constraint -- the strategy runs on whatever bars it gets.
                "source_timeframe": _default_timeframe(model),
            },
            entry_conditions=[self._describe(model.get("enterCondition"))],
            exit_conditions=exits or ["No exit conditions in the source strategy"],
            live_caution=None if supported else f"Not runnable: {reason}",
        )

    # --- support ----------------------------------------------------------
    def _indicator_types(self) -> set[str]:
        found: set[str] = set()

        def walk(node):
            if isinstance(node, dict):
                definition = node.get("definition") or {}
                if definition.get("indicatorType"):
                    found.add(definition["indicatorType"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(self.MODEL.get("enterCondition"))
        walk(self.MODEL.get("exitCondition"))
        return found

    def _has_script_exit(self) -> bool:
        return any(
            c.get("type") == "script"
            for c in ((self.MODEL.get("exitCondition") or {}).get("conditions") or [])
        )

    def support_status(self) -> tuple[bool, str]:
        """Can this model be reproduced exactly? Checked by dry-running the
        trees over a tiny synthetic frame, so an unmapped indicator or
        operator is caught up-front rather than mid-backtest."""
        probe = pd.DataFrame(
            {
                "open": [1.0] * 260, "high": [1.0] * 260,
                "low": [1.0] * 260, "close": [1.0] * 260, "volume": [1.0] * 260,
            },
            index=pd.date_range("2024-01-02 09:30", periods=260, freq="1min"),
        )
        try:
            evaluate_signal_tree(self.MODEL.get("enterCondition"), probe)
            evaluate_signal_tree(self.MODEL.get("exitCondition"), probe)
        except (UnsupportedIndicator, UnsupportedCondition, KeyError) as exc:
            return False, str(exc)
        except StoreScriptError:
            # A TrendSpider script refusing this probe's bars (its own
            # timeframe assert) is runtime behavior, not a missing mapping.
            pass
        except Exception as exc:  # noqa: BLE001 - report, never mask
            return False, f"{type(exc).__name__}: {exc}"
        return True, ""

    def _describe(self, tree: dict | None) -> str:
        if not tree:
            return "No entry conditions"
        parts: list[str] = []

        def walk(block):
            for condition in block.get("conditions") or []:
                # Same null-operand quirk the evaluator guards against:
                # TrendSpider stores an unset second operand as a literal
                # null inside the array.
                operands = [o for o in (condition.get("operands") or []) if isinstance(o, dict)]
                names = [
                    (o.get("definition") or {}).get("titleShort")
                    or (o.get("definition") or {}).get("title")
                    or str((o.get("definition") or {}).get("value", "?"))
                    for o in operands
                ]
                op = (condition.get("operator") or {}).get("title", "?")
                parts.append(f"{names[0] if names else '?'} {op} "
                             f"{names[1] if len(names) > 1 else ''}".strip())
            for sub in block.get("subBlocks") or []:
                walk(sub.get("script") if "script" in sub else sub)

        for entry in tree.get("conditions") or []:
            if entry.get("type") == "script":
                walk(entry.get("script") or {})
        return "; ".join(parts) if parts else "No bar conditions"

    # --- execution parity -------------------------------------------------
    def recommended_execution(self, **overrides):
        """An ExecutionConfig that reproduces TrendSpider's own execution
        for this strategy: next-bar-open fills, this model's stop/target/
        trailing/time-stop, its extended-hours setting, and its cost of
        trade (0% on every strategy checked, so no slippage by default)."""
        from app.strategies.execution import ExecutionConfig

        options = self.MODEL.get("_backtestOptions") or {}
        cost = (options.get("costOfTrade") or {}).get("value", 0) or 0
        chart = options.get("chartTypeDefinition") or {}
        config = {
            "fill_at": "next_open",
            "slippage_pct": float(cost) / 100.0,
            "commission_per_trade": 0.0,
            # TrendSpider holds overnight unless a rule exits; it does not
            # flatten at the session close the way QIS defaults to.
            "force_close_at_session_end": False,
            "include_extended_hours": bool(chart.get("extendedSessionEnabled", False)),
            **_risk_settings(self.MODEL),
            **overrides,
        }
        return ExecutionConfig(**config)

    # --- Strategy contract ------------------------------------------------
    def _guard(self) -> None:
        supported, reason = self.support_status()
        if not supported:
            raise StrategyUnsupported(
                f"{self.SLUG!r} cannot be reproduced exactly: {reason}"
            )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        # Indicators are resolved lazily while walking the condition tree
        # (each operand names its own indicator + parameters), so there is
        # no fixed set of columns to attach up front.
        return df.copy()

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self._guard()
        p = self.validate_params(params)
        signal = evaluate_signal_tree(self.MODEL.get("enterCondition"), df)
        direction = (
            TradeDirection.SHORT
            if str(p.get("direction", "long")).lower() == "short"
            else TradeDirection.LONG
        )
        entries = pd.Series(None, index=df.index, dtype=object)
        entries[signal] = direction
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self._guard()
        return evaluate_signal_tree(self.MODEL.get("exitCondition"), df)


def _register_all() -> None:
    """Generate and register one Strategy subclass per extracted model."""
    for slug, model in load_models().items():
        if slug in strategy_registry.all():
            continue
        cls = type(
            f"TrendSpider_{slug}",
            (TrendSpiderStrategy,),
            {"MODEL": model, "SLUG": slug, "__doc__": f"TrendSpider strategy: {model['name']}"},
        )
        strategy_registry.register(slug)(cls)


_register_all()
