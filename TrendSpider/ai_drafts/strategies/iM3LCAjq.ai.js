describe_indicator('XAU Tanner Vol Funnel V6', 'lower');

// ==================== Inputs ====================
const myTab = input.tab('Settings');
const myBBGroup = myTab.group('Bollinger Bands');
const myBBLength = myBBGroup.number('BB Length', 25, { min: 1, max: 500 });
const myBBMult = myBBGroup.number('BB Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });

const myRsiGroup = myTab.group('RSI');
const myRsiLength = myRsiGroup.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiFilter = myRsiGroup.number('RSI Strength Filter', 55, { min: 1, max: 99 });

const myVolGroup = myTab.group('Volatility Funnel');
const myAtrLength = myVolGroup.number('ATR Length', 14, { min: 1, max: 200 });
// Shortened input name (was too long and triggered a platform error)
const myVolThreshold = myVolGroup.number('Vol Threshold', 1.2, { min: 0.1, max: 10, step: 0.1 });

const myExitGroup = myTab.group('Take Profit / Stop Loss');
const myTpPct = myExitGroup.number('Take Profit %', 2.5, { min: 0.01, max: 100, step: 0.01 });
const mySlPct = myExitGroup.number('Stop Loss %', 1.2, { min: 0.01, max: 100, step: 0.01 });

// ==================== Core calculations ====================
// Bollinger Bands: basis = sma(close, length), bands = basis +/- mult*stdev(close, length)
const myBasis = sma(close, myBBLength);
const myStdev = stdev(close, myBBLength);
const myUpper = add(myBasis, mult(myStdev, myBBMult));
const myLower = sub(myBasis, mult(myStdev, myBBMult));

const myRsi = rsi(close, myRsiLength);

// ATR and its SMA(50), used to detect whether volatility is "awake"
const myAtr = atr(high, low, close, myAtrLength);
const myAtrSma = sma(myAtr, 50);

// Volatility funnel readiness: current ATR must not be in a "dead" state
const myVolReady = for_every(myAtr, myAtrSma, (_a, _s) => _a > (_s * 0.8));

// Cross-under-upper band, using previous candle's close/upper to avoid repainting
// (mirrors Pine's close[1] > upper[1] and close < upper)
const myPrevClose = shift(close, 1);
const myPrevUpper = shift(myUpper, 1);
const myCrossUnderUpper = for_every(myPrevClose, myPrevUpper, close, myUpper, (_pc, _pu, _c, _u) => _pc > _pu && _c < _u);

// Long signal: cross under upper band + RSI strength filter + volatility ready
const mySignalLong = for_every(myCrossUnderUpper, myRsi, myVolReady, (_cross, _r, _vr) => _cross && _r > myRsiFilter && _vr);

// ==================== Position / Exit simulation ====================
// We simulate a single-position (long-only) state machine to reproduce
// Pine's strategy.entry/strategy.exit behavior: enters on signal when flat,
// exits on fixed take-profit or stop-loss percentages from entry price.
const myEntrySignal = series_of(false);
const myExitSignal = series_of(false);
let myInPosition = false;
let myEntryPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (!myInPosition) {
		if (mySignalLong[myIndex]) {
			myInPosition = true;
			myEntryPrice = close[myIndex];
			myEntrySignal[myIndex] = true;
		}
	}
	else {
		const myTpLevel = myEntryPrice * (1 + myTpPct / 100);
		const mySlLevel = myEntryPrice * (1 - mySlPct / 100);

		if (high[myIndex] >= myTpLevel || low[myIndex] <= mySlLevel) {
			myInPosition = false;
			myEntryPrice = null;
			myExitSignal[myIndex] = true;
		}
	}
}

// ==================== Painting ====================
paint(myUpper, { name: 'Upper Band', color: '#ef5350', thickness: 1, forceUsePriceAxis: true });
paint(myLower, { name: 'Lower Band', color: '#26a69a', thickness: 1, forceUsePriceAxis: true });

const myVolReadyLine = for_every(myVolReady, _vr => _vr ? 1 : 0);
paint(myVolReadyLine, { name: 'Volatility Ready', style: 'column', color: '#4da3ff' });

const myEntryMarks = for_every(myEntrySignal, close, (_e, _c) => _e ? _c : null);
const myExitMarks = for_every(myExitSignal, close, (_e, _c) => _e ? _c : null);

paint(myEntryMarks, { name: 'Long Entry', style: 'labels_below', color: '#26a69a', thickness: 3, forceUsePriceAxis: true });
paint(myExitMarks, { name: 'Long Exit', style: 'labels_above', color: '#ef5350', thickness: 3, forceUsePriceAxis: true });

// ==================== Signals for Scanner/Alerts/Backtest ====================
// Renamed signal names so they no longer collide with the names used by
// the paint() calls above (names must be unique across the whole script).
register_signal(mySignalLong, 'Funnel Long Signal');
register_signal(myEntrySignal, 'Long Entry Signal');
register_signal(myExitSignal, 'Long Exit Signal');
register_signal(myVolReady, 'Volatility Ready Signal');