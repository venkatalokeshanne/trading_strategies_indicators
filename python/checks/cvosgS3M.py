"""Independent check — CryptoRSI (cvosgS3M): hourly 24/7 bars plus a synthetic daily BTC series served through the data provider. Preset Original: long (1 % of equity) when SMA10(RSI20) > 60 and the daily BTC close is above its
daily EMA50 (request.security, lookahead off: a day's value shows from its last hour on, earlier hours see the previous day); a long closes at the next open when the close crosses under WMA50. Entry and close queued on the same bar
run in that order (entry, then close). Pyramiding 0."""
import numpy as np

from indep import bars, compare, np_ema, np_rsi, np_sma, np_wma, np_cross_under, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "cvosgS3M"


def check():
    ndays = 1800
    df = bars(ndays * 24, seed=207, freq="1h")
    btc = bars(ndays, seed=208, freq="D")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid = np.arange(n) // 24
    last_of = (np.arange(n) % 24) == 23
    bc = btc["close"].to_numpy()
    mc = np_security_lookahead_off(bc, pid, last_of)
    me = np_security_lookahead_off(np_ema(bc, 50), pid, last_of)
    fr = np_sma(np_rsi(c, 20), 10)
    xu = np_cross_under(c, np_wma(c, 50))
    with np.errstate(invalid="ignore"):
        buy = (mc > me) & (fr > 60)

    def orders(i, pos):
        return ([("entry", 1)] if buy[i] else []) + ([("close", 1)] if xu[i] else [])

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("BINANCE:ETHUSD", "crypto", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", data_provider=lambda s, tf: btc), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
