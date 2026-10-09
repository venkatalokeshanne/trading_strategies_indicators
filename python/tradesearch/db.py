"""
Storage. SQLite by default (``TRADESEARCH_DB`` for another SQLAlchemy URL, e.g. Postgres).

Tables mirror TradeSearcher's objects: Symbol, Strategy, Backtest (metrics as indexed
columns for search plus the full JSON), and the heavy parts — trades and curves — as JSON
blobs on BacktestDetail so search queries stay light.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint, create_engine, select)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

DEFAULT_URL = "sqlite:///" + str(Path(__file__).resolve().parents[1] / "tradesearch.db")


class Base(DeclarativeBase):
    pass


class Symbol(Base):
    __tablename__ = "symbols"
    id: Mapped[int] = mapped_column(primary_key=True)
    tickerid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    exchange: Mapped[str] = mapped_column(String(32))
    type: Mapped[str] = mapped_column(String(16), index=True)        # crypto|stock|forex|futures|index
    description: Mapped[str] = mapped_column(String(256), default="")
    currency: Mapped[str] = mapped_column(String(16), default="USD")
    base_currency: Mapped[str] = mapped_column(String(16), default="")
    provider: Mapped[str] = mapped_column(String(32), default="")
    provider_symbol: Mapped[str] = mapped_column(String(64), default="")


class Strategy(Base):
    __tablename__ = "strategies"
    id: Mapped[int] = mapped_column(primary_key=True)
    tv_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)   # TradingView script id
    name: Mapped[str] = mapped_column(String(256), index=True)
    author: Mapped[str] = mapped_column(String(128), default="")
    tradingview_url: Mapped[str] = mapped_column(String(512), default="")
    module: Mapped[str] = mapped_column(String(256))                 # python import path
    pine_path: Mapped[str] = mapped_column(String(512), default="")
    licence: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    strategy_type: Mapped[str] = mapped_column(String(16), default="")  # intraday|swing|longTerm
    main_type: Mapped[str] = mapped_column(String(32), default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    indicators: Mapped[list] = mapped_column(JSON, default=list)
    entry_criteria: Mapped[list] = mapped_column(JSON, default=list)
    exit_criteria: Mapped[list] = mapped_column(JSON, default=list)
    parameters: Mapped[list] = mapped_column(JSON, default=list)
    repainting: Mapped[dict] = mapped_column(JSON, default=dict)
    conversion_status: Mapped[str] = mapped_column(String(32), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Backtest(Base):
    __tablename__ = "backtests"
    __table_args__ = (UniqueConstraint("strategy_id", "symbol_id", "timeframe", "params_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id"), index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    params_key: Mapped[str] = mapped_column(String(256), default="")
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    strategy_type: Mapped[str] = mapped_column(String(16), index=True, default="")
    bars: Mapped[int] = mapped_column(Integer, default=0)
    period_from: Mapped[int] = mapped_column(BigInteger, nullable=True)       # ms
    period_to: Mapped[int] = mapped_column(BigInteger, nullable=True)
    latest_trade_time: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True)
    # searchable metrics
    net_profit_percent: Mapped[float] = mapped_column(Float, nullable=True, index=True)
    profit_factor: Mapped[float] = mapped_column(Float, nullable=True, index=True)
    sharpe: Mapped[float] = mapped_column(Float, nullable=True, index=True)
    sortino: Mapped[float] = mapped_column(Float, nullable=True)
    max_drawdown_percent: Mapped[float] = mapped_column(Float, nullable=True, index=True)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    percent_profitable: Mapped[float] = mapped_column(Float, nullable=True, index=True)
    risk_reward: Mapped[float] = mapped_column(Float, nullable=True, index=True)
    avg_trade_percent: Mapped[float] = mapped_column(Float, nullable=True)
    buy_hold_percent: Mapped[float] = mapped_column(Float, nullable=True)
    p_value: Mapped[float] = mapped_column(Float, nullable=True)
    robust_score: Mapped[float] = mapped_column(Float, nullable=True, index=True)
    score_consistency: Mapped[float] = mapped_column(Float, nullable=True)
    score_backtests: Mapped[float] = mapped_column(Float, nullable=True)
    score_edge: Mapped[float] = mapped_column(Float, nullable=True)
    score_practicality: Mapped[float] = mapped_column(Float, nullable=True)
    quality_gate_pass: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    gate_reasons: Mapped[list] = mapped_column(JSON, default=list)
    flags: Mapped[list] = mapped_column(JSON, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    strategy: Mapped[Strategy] = relationship()
    symbol: Mapped[Symbol] = relationship()
    detail: Mapped["BacktestDetail"] = relationship(back_populates="backtest", uselist=False,
                                                    cascade="all, delete-orphan")


class BacktestDetail(Base):
    __tablename__ = "backtest_details"
    backtest_id: Mapped[int] = mapped_column(ForeignKey("backtests.id"), primary_key=True)
    trades: Mapped[list] = mapped_column(JSON, default=list)
    equity_curve: Mapped[dict] = mapped_column(JSON, default=dict)     # time, equity, drawdownPercent, buyHold
    monthly_returns: Mapped[list] = mapped_column(JSON, default=list)
    backtest: Mapped[Backtest] = relationship(back_populates="detail")


def engine(url: str | None = None):
    url = url or os.environ.get("TRADESEARCH_DB", DEFAULT_URL)
    eng = create_engine(url, future=True, json_serializer=lambda o: json.dumps(o, default=_jdefault))
    Base.metadata.create_all(eng)
    return eng


def _jdefault(o):
    return str(o)


def clean(o):
    """JSON-safe copy: nan/inf → None, numpy scalars → Python numbers, tuples → lists."""
    import math
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        try:
            o = o.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return o


def get_or_create_symbol(s: Session, ref) -> Symbol:
    row = s.scalar(select(Symbol).where(Symbol.tickerid == ref.tickerid))
    if row is None:
        row = Symbol(tickerid=ref.tickerid, ticker=ref.ticker, exchange=ref.exchange, type=ref.type,
                     description=ref.description, currency=ref.currency, base_currency=ref.base_currency,
                     provider=ref.provider, provider_symbol=ref.provider_symbol)
        s.add(row)
        s.flush()
    return row
