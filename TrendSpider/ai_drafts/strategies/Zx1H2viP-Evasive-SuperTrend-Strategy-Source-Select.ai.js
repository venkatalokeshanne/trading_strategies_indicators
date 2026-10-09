describe_indicator('Evasive SuperTrend Strategy', 'price');

// --- Inputs grouped like the original Pine groups ---
const stGroup = input.group('Supertrend Settings');
const myLength = stGroup.number('ATR Length', 10, { min: 1 });
const myMultiplier = stGroup.number('Base Multiplier', 3.0, { min: 0.1, step: 0.1 });
const mySourceName = stGroup.select('Source', 'hl2', constants.price_source_options);

const noiseGroup = input.group('Noise Avoidance Logic');
const myThreshold = noiseGroup.number('Noise Threshold (xATR)', 1.0, { min: 0.0, step: 0.1 });
const myAlpha = noiseGroup.number('Expansion Alpha (xATR)', 0.5, { min: 0.0, step: 0.1 });

const mySource = market[mySourceName];

// Pre-compute ATR and base bands (built-in functions must be called outside loops)
const myAtr = atr(high, low, close, myLength);
const myUpperBase = add(mySource, mult(myAtr, myMultiplier));
const myLowerBase = sub(mySource, mult(myAtr, myMultiplier));

// --- Recursive state machine (trend / st_line depend on their own previous values) ---
// This mirrors the Pine `var` state variables exactly, so a loop is required here.
// No indicator functions are called inside this loop, only arithmetic on precomputed series.
const myStLine = series_of(null);
const myTrend = series_of(1);
const myIsNoisy = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevTrend = myIndex === 0 ? 1 : myTrend[myIndex - 1];
	const myPrevLineRaw = myIndex === 0 ? null : myStLine[myIndex - 1];
	const myPrevLine = myPrevLineRaw === null
		? (myPrevTrend === 1 ? myLowerBase[myIndex] : myUpperBase[myIndex])
		: myPrevLineRaw;

	const myNoisy = Math.abs(close[myIndex] - myPrevLine) < (myAtr[myIndex] * myThreshold);
	myIsNoisy[myIndex] = myNoisy;

	let myCurrentTrend = myPrevTrend;
	let myCurrentLine;

	if (myPrevTrend === 1) {
		myCurrentLine = myNoisy
			? myPrevLine - (myAtr[myIndex] * myAlpha)
			: Math.max(myLowerBase[myIndex], myPrevLine);

		if (close[myIndex] < myCurrentLine) {
			myCurrentTrend = -1;
			myCurrentLine = myUpperBase[myIndex];
		}
	}
	else {
		myCurrentLine = myNoisy
			? myPrevLine + (myAtr[myIndex] * myAlpha)
			: Math.min(myUpperBase[myIndex], myPrevLine);

		if (close[myIndex] > myCurrentLine) {
			myCurrentTrend = 1;
			myCurrentLine = myLowerBase[myIndex];
		}
	}

	myTrend[myIndex] = myCurrentTrend;
	myStLine[myIndex] = myCurrentLine;
}

// --- Visuals: solid band when not noisy, dotted band when noisy ---
const mySolidBand = for_every(myStLine, myIsNoisy, (_myLine, _myNoisy) => _myNoisy ? null : _myLine);
const myDottedBand = for_every(myStLine, myIsNoisy, (_myLine, _myNoisy) => _myNoisy ? _myLine : null);

const myTrendColor = myTrend.map(_myT => _myT === 1 ? 'teal' : 'maroon');

paint(mySolidBand, { name: 'SolidBand', color: myTrendColor, thickness: 2, style: 'line' });
paint(myDottedBand, { name: 'DottedBand', color: myTrendColor, thickness: 2, style: 'dotted' });

// --- Strategy signals: trend flip up = Long entry, trend flip down = Short entry ---
const myTrendChangeUp = for_every(myTrend, (_myT, _myPrev, _myIndex) => _myIndex > 0 && _myT === 1 && myTrend[_myIndex - 1] === -1);
const myTrendChangeDown = for_every(myTrend, (_myT, _myPrev, _myIndex) => _myIndex > 0 && _myT === -1 && myTrend[_myIndex - 1] === 1);

register_signal(myTrendChangeUp, 'Long Entry');
register_signal(myTrendChangeDown, 'Short Entry');