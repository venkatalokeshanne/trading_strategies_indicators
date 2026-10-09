describe_indicator('FVG Short Signal (ES 5m)', 'lower');

// NOTE: TrendSpider Custom JS indicators cannot place broker-style
// orders, manage open positions, or track strategy.position_size,
// strategy.entry/exit like Pine Script strategies do. This script
// reproduces the exact entry signal logic, the ATR based target and
// stop VALUES (so you can see them), and exposes a scannable signal.
// The actual trade management (one position at a time, TP/SL exits)
// must be implemented via TrendSpider's Strategy Tester using this
// signal as the entry trigger; it is not something a Custom JS
// indicator can execute on its own.

const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 200 });
const myMinAtr = input.number('Minimum ATR Filter', 2, { min: 0, max: 100 });
const myStopMultiplier = input.number('Stop Multiplier', 1.5, { min: 0.1, max: 10 });

const myAtr = atr(high, low, close, myAtrLength);

// Round down to nearest 0.5, exactly like roundDownToHalf(x) in Pine
const myTarget = for_every(myAtr, _atr => Math.floor(_atr / 0.5) * 0.5);
const myStop = mult(myTarget, myStopMultiplier);

// FVG bullish gap check: high[2] < low (current low), i.e. the high
// two candles ago is below the current low.
const myHigh2CandlesAgo = shift(high, 2);
const myFvgBull = for_every(myHigh2CandlesAgo, low, (_h2, _l) => _h2 < _l);

// Third candle (current candle) must be red
const myThirdRed = for_every(close, open, (_c, _o) => _c < _o);

// ATR filter
const myValidAtr = for_every(myAtr, _atr => _atr >= myMinAtr);

// Combined entry condition, exactly mirroring enter_short in Pine
const myEnterShort = for_every(myFvgBull, myThirdRed, myValidAtr, (_fvg, _red, _validAtr) => _fvg && _red && _validAtr);

// Plot the Target and Stop distances for sanity, on price axis since
// this is a lower indicator but these values make more sense as
// price-distance context lines
paint(myTarget, { name: 'Target', color: '#26A69A', thickness: 2 });
paint(myStop, { name: 'Stop', color: '#EF5350', thickness: 2 });

// Shape marker reproducing plotshape(enter_short, ..., location=abovebar)
const myEnterShortMarker = for_every(myEnterShort, _enter => _enter ? constants.icons.triangle_down : null);
paint(myEnterShortMarker, { name: 'Short Signal', style: 'labels_above', color: 'red' });

// Expose the entry condition as a scannable / alertable / backtestable signal
register_signal(myEnterShort, 'Short Entry Signal');