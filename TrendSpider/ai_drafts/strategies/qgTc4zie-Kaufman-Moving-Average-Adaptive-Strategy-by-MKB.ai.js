describe_indicator('KAMA by MKB', 'price');

// ─── Inputs ───────────────────────────────────────────────────────────
const myLength = input.number('KAMA Length', 21, { min: 1, max: 500 });
const myPriceSource = input.select('Source', 'close', constants.price_source_options);
const mySrc = market[myPriceSource];

const myFastEnd = input.number('Fast End', 0.666, { min: 0, max: 1, step: 0.001 });
const mySlowEnd = input.number('Slow End', 0.0645, { min: 0, max: 1, step: 0.0001 });

const myStdevLength = input.number('Std Dev Length', 20, { min: 1, max: 500 });
const myStdevMultiplier = input.number('Std Dev Multiplier', 0.5, { min: -10, max: 10, step: 0.1 });

const myShowSignalLabels = input.boolean('Show AL/SAT Labels', false);
const myShowStdBand = input.boolean('Show KAMA Plus Std Dev Band', true);

// ─── KAMA computation ─────────────────────────────────────────────────
// xvnoise = |src - src[1]|
const myXvnoise = for_every(mySrc, shift(mySrc, 1), (_s, _sp) => Math.abs(_s - (_sp ?? _s)));

// signal = |src - src[length]|
const mySrcShiftedByLength = shift(mySrc, myLength);
const mySignal = for_every(mySrc, mySrcShiftedByLength, (_s, _sl) => Math.abs(_s - (_sl ?? _s)));

// noise = sum(xvnoise, length)
const myNoise = sum(myXvnoise, myLength);

// efRatio = noise != 0 ? signal / noise : 0
const myEfRatio = for_every(mySignal, myNoise, (_sig, _n) => (_n !== 0 ? _sig / _n : 0));

// smooth = (efRatio * (fastEnd - slowEnd) + slowEnd) ^ 2
const mySmooth = for_every(myEfRatio, _e => Math.pow(_e * (myFastEnd - mySlowEnd) + mySlowEnd, 2));

// kama recursive: kama := nz(kama[1]) + smooth * (src - nz(kama[1]))
const myKama = for_every(mySrc, mySmooth, (_s, _sm, _prev, _i) => {
	const myPrevKama = _i === 0 ? 0 : (_prev ?? 0);
	return myPrevKama + _sm * (_s - myPrevKama);
});

// ─── Std Dev band ─────────────────────────────────────────────────────
const myStdev = stdev(mySrc, myStdevLength);
const myUpperBand = add(myKama, mult(myStdev, myStdevMultiplier));

// ─── Crossover / Crossunder detection ─────────────────────────────────
const mySrcPrev = shift(mySrc, 1);
const myKamaPrev = shift(myKama, 1);
const myUpperBandPrev = shift(myUpperBand, 1);

// buySignal = crossover(src, upperBand)
const myBuySignalRaw = for_every(mySrc, mySrcPrev, myUpperBand, myUpperBandPrev, (_s, _sp, _ub, _ubp) => {
	if (_sp === null || _ubp === null) return false;
	return _s > _ub && _sp <= _ubp;
});

// sellSignal = crossunder(src, kama)
const mySellSignalRaw = for_every(mySrc, mySrcPrev, myKama, myKamaPrev, (_s, _sp, _k, _kp) => {
	if (_sp === null || _kp === null) return false;
	return _s < _k && _sp >= _kp;
});

// ─── Simulate strategy.position_size to find "real" signals ──────────
// Pine's strategy.position_size tracks an open/closed state sequentially.
// We reproduce that sequential state machine here since it cannot be
// expressed via plain vectorized math.
const myRealBuySignal = series_of(false);
const myRealSellSignal = series_of(false);
let myPositionOpen = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myIsBuy = myBuySignalRaw[myIndex] && !myPositionOpen;
	const myIsSell = mySellSignalRaw[myIndex] && myPositionOpen;

	myRealBuySignal[myIndex] = myIsBuy;
	myRealSellSignal[myIndex] = myIsSell;

	if (myIsBuy) {
		myPositionOpen = true;
	}
	if (myIsSell) {
		myPositionOpen = false;
	}
}

// ─── Painting ──────────────────────────────────────────────────────────
paint(myKama, { name: 'KAMA', color: '#2962FF', thickness: 2 });

// Conditional std dev band: paint null series when hidden, to keep paint() count constant
paint(myShowStdBand ? myUpperBand : constants.empty_series, { name: 'KAMA Plus StdDev', color: '#FF9800', thickness: 1 });

// Shapes/labels for buy and sell, conditional on showSignalLabels
const myBuyLabelSeries = for_every(myRealBuySignal, low, (_b, _l) => (myShowSignalLabels && _b ? _l : null));
const mySellLabelSeries = for_every(myRealSellSignal, high, (_s, _h) => (myShowSignalLabels && _s ? _h : null));

paint(myBuyLabelSeries, { name: 'AL Signal', style: 'labels_below', color: 'green' });
paint(mySellLabelSeries, { name: 'SAT Signal', style: 'labels_above', color: 'red' });

// ─── Signals for scanners / alerts / strategy tester ──────────────────
register_signal(myRealBuySignal, 'Buy Signal');
register_signal(myRealSellSignal, 'Sell Signal');