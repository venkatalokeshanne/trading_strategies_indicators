/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : BB vs EMA 9 Gap Signals
 * Author       : jaspreet4264
 * Source URL   : https://www.tradingview.com/script/6tCtEfuw-BB-vs-EMA-9-Gap-Signals
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : BB vs EMA 9 Gap Signals_TV
 *
 * The Pine original, in words: EMA 9 and Bollinger Bands (20, 2); BUY when price touches the lower band and the EMA
 *   is nearer the upper band, SELL the opposite.
 *
 * Deviations from the original: band width uses TrendSpider's stdev() (Pine ta.stdev is the population deviation)
 *   [VERIFY].
 * Not carried over: alertconditions — use the Buy/Sell signals.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('BB vs EMA 9 Gap Signals_TV', 'price');

// ───── Inputs ─────
const myEmaLength = input.number('EMA Length', 9, { min: 1, max: 500 });
const myBbLength = input.number('BB Length', 20, { min: 1, max: 500 });
const myBbMult = input.number('BB Std Dev', 2.0, { min: 0.1, max: 10 });

// ───── EMA ─────
const myEma9 = ema(close, myEmaLength);

// ───── Bollinger Bands ─────
const myBbBasis = sma(close, myBbLength);
const myBbDev = mult(stdev(close, myBbLength), myBbMult);

const myUpperBB = add(myBbBasis, myBbDev);
const myLowerBB = sub(myBbBasis, myBbDev);

// ───── Distance Calculations ─────
// X = distance between Upper BB and EMA
const myX = sub(myUpperBB, myEma9);
// Y = distance between EMA and Lower BB
const myY = sub(myEma9, myLowerBB);

// ───── BB Touch / Cross ─────
const myTouchedLowerBB = for_every(low, myLowerBB, (_l, _lb) => _lb !== null && _l <= _lb);
const myTouchedUpperBB = for_every(high, myUpperBB, (_h, _ub) => _ub !== null && _h >= _ub);

// ───── BUY / SELL conditions ─────
const myBuySignal = for_every(myY, myX, myTouchedLowerBB, (_y, _x, _touch) => _y > _x && _touch);
const mySellSignal = for_every(myX, myY, myTouchedUpperBB, (_x, _y, _touch) => _x > _y && _touch);

// ───── Plot EMA and Bollinger Bands ─────
paint(myEma9, { name: 'EMA 9', color: 'orange', thickness: 2 });

const myUpperPlot = paint(myUpperBB, { name: 'Upper BB', color: 'blue' });
const myLowerPlot = paint(myLowerBB, { name: 'Lower BB', color: 'blue' });
paint(myBbBasis, { name: 'BB Basis', color: 'gray' });

fill(myUpperPlot, myLowerPlot, 'blue', 0.1);

// ───── Buy / Sell markers ─────
const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? 'BUY' : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? 'SELL' : null);

paint(myBuyMarks, { name: 'BUY', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'SELL', style: 'labels_above', color: 'red' });

// ───── Signals for scanner/alerts/strategy ─────
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
