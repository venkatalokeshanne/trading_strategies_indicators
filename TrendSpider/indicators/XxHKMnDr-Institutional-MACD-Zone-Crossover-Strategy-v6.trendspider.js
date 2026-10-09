/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Institutional MACD Zone Crossover Strategy [v6]
 * Author       : houston2019
 * Source URL   : https://www.tradingview.com/script/XxHKMnDr-Institutional-MACD-Zone-Crossover-Strategy-v6
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Institutional MACD Zone Crossover_TV
 *
 * Deviations from the original: Reviewed AI draft; label text VB/B/VS/S replaced by triangle icons; null-guarded
 *   crossovers; ema-based MACD.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Institutional MACD Zone Crossover_TV', 'price');
const myFastLength = input.number('MACD Fast', 12, { min: 1, max: 200 });
const mySlowLength = input.number('MACD Slow', 26, { min: 1, max: 500 });
const mySignalLength = input.number('MACD Signal', 9, { min: 1, max: 200 });
const myMacdLine = sub(ema(close, myFastLength), ema(close, mySlowLength));
const mySignalLine = ema(myMacdLine, mySignalLength);
const myVolSma = sma(volume, 20);
const myPrevMacd = shift(myMacdLine, 1);
const myPrevSignal = shift(mySignalLine, 1);
const myNn = (_a) => _a !== null && _a !== undefined;
const myPositiveCrossover = for_every(myMacdLine, mySignalLine, myPrevMacd, myPrevSignal,
	(_m, _s, _pm, _ps) => myNn(_m) && myNn(_s) && myNn(_pm) && myNn(_ps) && _pm <= _ps && _m > _s && _m > 0);
const myNegativeCrossunder = for_every(myMacdLine, mySignalLine, myPrevMacd, myPrevSignal,
	(_m, _s, _pm, _ps) => myNn(_m) && myNn(_s) && myNn(_pm) && myNn(_ps) && _pm >= _ps && _m < _s && _m < 0);
const myVolOk = for_every(volume, myVolSma, (_v, _a) => myNn(_a) && _v > _a);
const myVolBuy = for_every(myPositiveCrossover, myVolOk, (_c, _v) => _c && _v);
const myRegBuy = for_every(myPositiveCrossover, myVolOk, (_c, _v) => _c && !_v);
const myVolSell = for_every(myNegativeCrossunder, myVolOk, (_c, _v) => _c && _v);
const myRegSell = for_every(myNegativeCrossunder, myVolOk, (_c, _v) => _c && !_v);
const myMark = (_flags, _icon) => _flags.map(_f => _f ? _icon : null);
paint(myMark(myVolBuy, constants.icons.triangle_up), { name: 'VB Mark', style: 'labels_below', color: '#2ecc71' });
paint(myMark(myRegBuy, constants.icons.triangle_up), { name: 'B Mark', style: 'labels_below', color: '#c6f542' });
paint(myMark(myVolSell, constants.icons.triangle_down), { name: 'VS Mark', style: 'labels_above', color: '#800000' });
paint(myMark(myRegSell, constants.icons.triangle_down), { name: 'S Mark', style: 'labels_above', color: '#ff4136' });
register_signal(myVolBuy, 'Volume BUY (VB)');
register_signal(myRegBuy, 'BUY (B)');
register_signal(myVolSell, 'Volume SELL (VS)');
register_signal(myRegSell, 'SELL (S)');
