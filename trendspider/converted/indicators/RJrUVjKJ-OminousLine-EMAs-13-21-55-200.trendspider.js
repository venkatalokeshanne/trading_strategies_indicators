/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : OminousLine EMAs (13/21/55/200)
 * Author       : OminousLine
 * Source URL   : https://www.tradingview.com/script/RJrUVjKJ-OminousLine-EMAs-13-21-55-200
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : OminousLine EMAs 13 21 55 200_TV
 *
 * Deviations from the original: Colour and width inputs not available; TrendSpider ema seeding differs slightly from
 *   Pine early on.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('OminousLine EMAs 13 21 55 200_TV', 'price');
const myTab13 = input.tab('EMA 13');
const myEma13Length = myTab13.number('Length', 13, { min: 1, max: 1000 });
const myShow13 = myTab13.boolean('Show EMA 13', true);
const myTab21 = input.tab('EMA 21');
const myEma21Length = myTab21.number('Length', 21, { min: 1, max: 1000 });
const myShow21 = myTab21.boolean('Show EMA 21', true);
const myTab55 = input.tab('EMA 55');
const myEma55Length = myTab55.number('Length', 55, { min: 1, max: 1000 });
const myShow55 = myTab55.boolean('Show EMA 55', true);
const myTab200 = input.tab('EMA 200');
const myEma200Length = myTab200.number('Length', 200, { min: 1, max: 1000 });
const myShow200 = myTab200.boolean('Show EMA 200', true);
const myEma13 = ema(close, myEma13Length);
const myEma21 = ema(close, myEma21Length);
const myEma55 = ema(close, myEma55Length);
const myEma200 = ema(close, myEma200Length);
const myGate = (_s, _show) => for_every(_s, _v => _show ? _v : null);
paint(myGate(myEma13, myShow13), { name: 'EMA 13', color: '#FF6D00', thickness: 2 });
paint(myGate(myEma21, myShow21), { name: 'EMA 21', color: '#00E5FF', thickness: 2 });
paint(myGate(myEma55, myShow55), { name: 'EMA 55', color: '#FFD740', thickness: 2 });
paint(myGate(myEma200, myShow200), { name: 'EMA 200', color: '#B388FF', thickness: 3 });
const myPrevA = shift(myEma13, 1);
const myPrevB = shift(myEma21, 1);
register_signal(for_every(myEma13, myEma21, myPrevA, myPrevB, (_a, _b, _pa, _pb) => _a !== null && _b !== null && _pa !== null && _pb !== null && _pa <= _pb && _a > _b), 'EMA13 Cross Above EMA21');
register_signal(for_every(myEma13, myEma21, myPrevA, myPrevB, (_a, _b, _pa, _pb) => _a !== null && _b !== null && _pa !== null && _pb !== null && _pa >= _pb && _a < _b), 'EMA13 Cross Below EMA21');
register_signal(for_every(close, myEma200, (_c, _e) => _e !== null && _c > _e), 'Close Above EMA200');
register_signal(for_every(close, myEma200, (_c, _e) => _e !== null && _c < _e), 'Close Below EMA200');
