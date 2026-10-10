describe_indicator('Price and Volume Thrust', 'price');

// ─────────────────────────────────────────────
// INPUTS
// ─────────────────────────────────────────────
const myArrowOffset = input.number('Dot Offset %', 1.0, { min: 0.1, max: 10.0, step: 0.1 });
const myKLength = input.number('K Length', 14, { min: 1, max: 100 });
const myKSmoothing = input.number('K Smoothing', 3, { min: 1, max: 50 });
const myDSmoothing = input.number('D Smoothing', 3, { min: 1, max: 50 });
const myObLevel = input.number('Overbought', 75, { min: 50, max: 100 });
const myOsLevel = input.number('Oversold', 25, { min: 0, max: 50 });

// ─────────────────────────────────────────────
// SLOW STOCHASTIC CALCULATION
// Pine's ta.stoch(close, high, low, kLength) is the raw %K,
// here computed via the built-in stochastic() function.
// slowK = sma(fastK, kSmoothing). dSmoothing is kept as an
// input for parity with the original script, even though %D
// itself is not used in any signal condition in the Pine code.
// ─────────────────────────────────────────────
const myFastK = stochastic(close, high, low, myKLength);
const mySlowK = sma(myFastK, myKSmoothing);
const mySlowD = sma(mySlowK, myDSmoothing);

// ─────────────────────────────────────────────
// STOCHASTIC FILTER
// ─────────────────────────────────────────────
const myStochFilter = for_every(mySlowK, _k => (_k >= myObLevel || _k <= myOsLevel));

// ─────────────────────────────────────────────
// CONDITIONS
// prevHigh/prevLow/prevVolume are shifted series ("[1]" in Pine)
// ─────────────────────────────────────────────
const myPrevHigh = shift(high, 1);
const myPrevLow = shift(low, 1);
const myPrevVolume = shift(volume, 1);

const myBullSignal = for_every(high, myPrevHigh, volume, myPrevVolume, close, open, myStochFilter,
	(_h, _ph, _v, _pv, _c, _o, _f) => (_h > _ph && _v > _pv && _c > _o && _f));

const myBearSignal = for_every(low, myPrevLow, volume, myPrevVolume, close, open, myStochFilter,
	(_l, _pl, _v, _pv, _c, _o, _f) => (_l < _pl && _v > _pv && _c < _o && _f));

// ─────────────────────────────────────────────
// DOT PLACEMENT
// candleRange / offsetPoints / bullDotY / bearDotY, as per Pine
// Fix: "div()" and "mult()" require their FIRST argument to be a
// series. myArrowOffset is a plain number (an input), not a
// series, so "div(myArrowOffset, 100)" threw "first argument is
// not a series". Since myArrowOffset/100 is just a constant
// ratio, we compute it with plain JS division and pass it as the
// (numeric) second argument to mult() instead.
// ─────────────────────────────────────────────
const myCandleRange = sub(high, low);
const myOffsetPoints = mult(myCandleRange, myArrowOffset / 100);

const myBullDotY = for_every(low, myOffsetPoints, myBullSignal, (_l, _off, _sig) => _sig ? (_l - _off) : null);
const myBearDotY = for_every(high, myOffsetPoints, myBearSignal, (_h, _off, _sig) => _sig ? (_h + _off) : null);

// ─────────────────────────────────────────────
// DOTS
// TrendSpider does not support multiple selectable dot sizes
// (Tiny/Small/Normal/Large/Huge) like Pine's plotchar size
// parameter, nor a "dot" character marker tied to size options.
// We reproduce the visual behavior with two single lines
// (bull/bear) using labels_below / labels_above styles, which
// is the closest supported equivalent. Thickness can be
// adjusted by the user via the platform's built-in line
// controls to emulate dot size.
// ─────────────────────────────────────────────
paint(myBullDotY, { name: 'Bull Dot', style: 'labels_below', color: 'blue', thickness: 6 });
paint(myBearDotY, { name: 'Bear Dot', style: 'labels_above', color: 'fuchsia', thickness: 6 });

// ─────────────────────────────────────────────
// SIGNALS (for Scanner / Alerts / Strategy Tester)
// ─────────────────────────────────────────────
register_signal(myBullSignal, 'Bullish Price and Volume Thrust');
register_signal(myBearSignal, 'Bearish Price and Volume Thrust');