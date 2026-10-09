describe_indicator('ATR Trailing Stop + EMA Filter', 'price');

// ATR Trailing Stop settings
const myAtrTab = input.tab('ATR Trailing Stop');
const myAtrLen = myAtrTab.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMult = myAtrTab.number('ATR Multiplier', 2.0, { min: 0.1, max: 20, step: 0.1 });

// Trend filter settings
const myTrendTab = input.tab('Trend Filter');
const myEmaLen = myTrendTab.number('EMA Length', 200, { min: 1, max: 500 });

const myAtrVal = atr(high, low, close, myAtrLen);
const myEmaVal = ema(close, myEmaLen);

const myLongStop = sub(close, mult(myAtrVal, myAtrMult));
const myShortStop = add(close, mult(myAtrVal, myAtrMult));

// Sequential recursive state (trail / upTrend) must be computed
// in a plain loop, since it depends on its own previous value
// and on another variable's previous value at the same time.
// This mirrors the Pine `var float trail` / `var bool upTrend` logic.
const myTrail = series_of(null);
const myUpTrend = series_of(true);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myIndex === 0 || myTrail[myIndex - 1] === null || isNaN(myLongStop[myIndex - 1])) {
		myTrail[myIndex] = myLongStop[myIndex];
		myUpTrend[myIndex] = true;
	}
	else {
		const myPrevTrail = myTrail[myIndex - 1];
		const myPrevUpTrend = myUpTrend[myIndex - 1];

		if (myPrevUpTrend) {
			myTrail[myIndex] = close[myIndex] < myPrevTrail
				? myShortStop[myIndex]
				: Math.max(myPrevTrail, myLongStop[myIndex]);
		}
		else {
			myTrail[myIndex] = close[myIndex] > myPrevTrail
				? myLongStop[myIndex]
				: Math.min(myPrevTrail, myShortStop[myIndex]);
		}

		myUpTrend[myIndex] = close[myIndex] >= myTrail[myIndex];
	}
}

// Trend filter conditions
const myEmaLong = for_every(close, myEmaVal, (_close, _ema) => _close > _ema);
const myEmaShort = for_every(close, myEmaVal, (_close, _ema) => _close < _ema);

// Flip detection
const myFlipToLong = series_of(false);
const myFlipToShort = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	myFlipToLong[myIndex] = myUpTrend[myIndex] && !myUpTrend[myIndex - 1];
	myFlipToShort[myIndex] = !myUpTrend[myIndex] && myUpTrend[myIndex - 1];
}

// Position state simulation, to reproduce
// `strategy.position_size <= 0` / `>= 0` behavior.
// This is a simplified single-position-at-a-time model: starts flat,
// goes long on a long signal, goes short on a short signal.
const myLongCond = series_of(false);
const myShortCond = series_of(false);
let myPositionSize = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myIsLong = myFlipToLong[myIndex] && myEmaLong[myIndex] && myPositionSize <= 0;
	const myIsShort = myFlipToShort[myIndex] && myEmaShort[myIndex] && myPositionSize >= 0;

	myLongCond[myIndex] = myIsLong;
	myShortCond[myIndex] = myIsShort;

	if (myIsLong) {
		myPositionSize = 1;
	}
	else if (myIsShort) {
		myPositionSize = -1;
	}
}

// Visuals
const myTrailColor = for_every(myUpTrend, _up => _up ? 'green' : 'red');
paint(myTrail, { name: 'ATRTrailingStop', color: myTrailColor, thickness: 2 });
paint(myEmaVal, { name: 'EMATrendFilter', color: '#4472C4', thickness: 1 });

const myLongMarks = for_every(myLongCond, low, (_cond, _low) => _cond ? _low : null);
const myShortMarks = for_every(myShortCond, high, (_cond, _high) => _cond ? _high : null);

paint(myLongMarks, { name: 'LongSignal', style: 'labels_below', color: 'green' });
paint(myShortMarks, { name: 'ShortSignal', style: 'labels_above', color: 'red' });

// Signals for scanners / alerts / strategy tester
register_signal(myLongCond, 'Long Entry Signal');
register_signal(myShortCond, 'Short Entry Signal');
register_signal(myUpTrend, 'ATR Trend Is Up');