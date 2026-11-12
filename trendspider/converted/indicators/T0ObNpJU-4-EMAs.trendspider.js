/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 4 EMAs
 * Author       : gaurabpoudel1
 * Source URL   : https://www.tradingview.com/script/T0ObNpJU-4-EMAs
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : 4 EMAs_TV
 *
 * The Pine original, in words: four EMAs (10, 20, 50, 200) of the close.
 *
 * Deviations from the original: colour inputs not exposed (fixed colours); EMA warm-up follows TrendSpider's ema().
 *   Trend signals added for scanning.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('4 EMAs_TV', 'price');

// Lengths for the four EMAs, matching the Pine script inputs
const myLen1 = input.number('EMA 1', 10, { min: 1, max: 1000 });
const myLen2 = input.number('EMA 2', 20, { min: 1, max: 1000 });
const myLen3 = input.number('EMA 3', 50, { min: 1, max: 1000 });
const myLen4 = input.number('EMA 4', 200, { min: 1, max: 1000 });

const myEma1 = ema(close, myLen1);
const myEma2 = ema(close, myLen2);
const myEma3 = ema(close, myLen3);
const myEma4 = ema(close, myLen4);

paint(myEma1, { name: 'EMA 1', color: '#000000', thickness: 1 });
paint(myEma2, { name: 'EMA 2', color: '#FF0000', thickness: 1 });
paint(myEma3, { name: 'EMA 3', color: '#4E483E', thickness: 1 });
paint(myEma4, { name: 'EMA 4', color: '#4E483E', thickness: 1 });

// Signals for scanning/alerting/strategy use: crossovers between
// consecutive EMAs, which is the closest mapping of "signal bars"
// available for a plain multi-EMA plot script.
const mySignalFastOverMedium = for_every(myEma1, myEma2, (_a, _b) => _a !== null && _b !== null && _a > _b);
const mySignalMediumOverSlow = for_every(myEma2, myEma3, (_a, _b) => _a !== null && _b !== null && _a > _b);
const mySignalSlowOverLong = for_every(myEma3, myEma4, (_a, _b) => _a !== null && _b !== null && _a > _b);

register_signal(mySignalFastOverMedium, 'EMA1 above EMA2');
register_signal(mySignalMediumOverSlow, 'EMA2 above EMA3');
register_signal(mySignalSlowOverLong, 'EMA3 above EMA4');
