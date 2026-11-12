/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 200MA Uptrend Screener
 * Author       : LeaderLab
 * Source URL   : https://www.tradingview.com/script/exVdVRAr
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : 200MA Uptrend Screener_TV
 *
 * The Pine original, in words: 1 when the 200 SMA is above its value `lookback` bars ago,
 * else 0.
 *
 * Deviations from the original: none. (Fixed from the AI draft: comparing with a null
 * early value read as 0 in JavaScript and gave false 'uptrend' bars; Pine's na is false.)
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('200MA Uptrend Screener_TV', 'lower');

const myLookback = input.number('Lookback Days', 20, { min: 1, max: 500 });

const myMa200 = sma(close, 200);
const myMa200Up = for_every(myMa200, shift(myMa200, myLookback),
    (_cur, _prev) => _cur !== null && _prev !== null && _cur > _prev);
const myScanner = for_every(myMa200Up, _up => _up ? 1 : 0);

paint(myScanner, { name: 'Scanner', color: '#2962FF', thickness: 1 });
register_signal(myMa200Up, 'MA200 Uptrend');
