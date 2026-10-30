"""Event flags: one known FOMC day and one known earnings day (AAPL reported after the close on 2024-02-01)."""
import pandas as pd

from src.features import events as ev

DAYS = pd.DatetimeIndex(pd.bdate_range("2024-01-29", "2024-03-29"))


def test_market_flags():
    f = ev.market_flags(DAYS)
    assert list(f.index[f["fomc"] == 1]) == [pd.Timestamp("2024-01-31"), pd.Timestamp("2024-03-20")]
    assert list(f.index[f["opex"] == 1]) == [pd.Timestamp("2024-02-16"), pd.Timestamp("2024-03-15")]
    assert list(f.index[f["month_end"] == 1]) == [pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-29"), pd.Timestamp("2024-03-28")]   # 03-29 is Good Friday


def test_earnings_after_close_flags_the_next_session(monkeypatch):
    monkeypatch.setattr(ev, "earnings", lambda cfg, s: [dict(date="2024-02-01", time="After Hours")])
    f = ev.symbol_flags({}, "AAPL", DAYS)
    assert f.loc["2024-02-01"].tolist() == [1, 1, 0]       # earn_day, earn_tonight, earn_reaction
    assert f.loc["2024-02-02"].tolist() == [0, 0, 1]
    assert f.drop(pd.to_datetime(["2024-02-01", "2024-02-02"])).sum().sum() == 0


def test_unknown_earnings_source_is_nan_not_zero(monkeypatch):
    monkeypatch.setattr(ev, "earnings", lambda cfg, s: None)
    assert ev.symbol_flags({}, "XYZ", DAYS).isna().all().all()


def test_fed_page_parser_skips_minutes_dates_and_handles_abbreviated_months():
    html = ("<h4>2023 FOMC Meetings</h4> Jan/Feb 31-1 Statement: PDF Minutes: (Released February 22, 2023) "
            "March 21-22* Statement: PDF Minutes: (Released April 12, 2023) <h4>2022 FOMC Meetings</h4> January 25-26 Statement:")
    assert ev.parse_fomc(html) == ["2022-01-26", "2023-02-01", "2023-03-22"]
