/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Institutional MACD Zone Crossover Strategy [v6]
 * Author       : houston2019
 * Source URL   : https://www.tradingview.com/script/4DwKFAo7-CAPITAL-MANTRAS
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : CAPITAL MANTRAS MACD_TV
 *
 * Deviations from the original: Reviewed AI draft; marker text replaced by triangle markers on the MACD line; zero
 *   line not dashed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('CAPITAL MANTRAS MACD_TV', 'lower');
const myFastLength = input.number('MACD Fast', 12, { min: 1, max: 200 });
const mySlowLength = input.number('MACD Slow', 26, { min: 1, max: 200 });
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
paint(myMacdLine, { name: 'MACD Line', color: '#2962FF', thickness: 2 });
paint(mySignalLine, { name: 'Signal Line', color: '#FF9800', thickness: 2 });
paint(horizontal_line(0), { name: 'Zero Line', color: 'gray' });
const myMark = (_flags, _icon) => _flags.map((_f, _i) => _f ? myMacdLine[_i] : null);
paint(myMark(myVolBuy), { name: 'VB Mark', style: 'dotted', marker: 'triangle', color: 'green' });
paint(myMark(myRegBuy), { name: 'B Mark', style: 'dotted', marker: 'triangle', color: 'lime' });
paint(myMark(myVolSell), { name: 'VS Mark', style: 'dotted', marker: 'triangle-down', color: 'maroon' });
paint(myMark(myRegSell), { name: 'S Mark', style: 'dotted', marker: 'triangle-down', color: 'red' });
register_signal(myVolBuy, 'Volume Buy Signal');
register_signal(myRegBuy, 'Regular Buy Signal');
register_signal(myVolSell, 'Volume Sell Signal');
register_signal(myRegSell, 'Regular Sell Signal');
