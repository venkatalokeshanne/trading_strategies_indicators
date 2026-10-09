// This indicator reproduces the "Silver Surfer" CISD + MTF alignment +
// FVG momentum entry logic from the supplied Pine Script.
// NOTE: TrendSpider custom indicators cannot place real orders or manage
// a strategy equity curve, so strategy.entry/strategy.exit are approximated:
// we expose the raw entry conditions (MTF aligned + FVG + optional BOS) as
// scanning/alert signals, and visualize FVG shapes + MTF alignment background.
// The strategy.position_size == 0 gating (one trade at a time) is simulated
// with a simple local position tracker purely for visualization purposes.
describe_indicator('Silver Surfer CISD', 'price');

const myHighTF = input.text('Trend TF (H1)', '60');
const myRRRatio = input.number('Risk-Reward Ratio', 1.5, { min: 0.1, max: 10 });
const myUseBOS = input.boolean('Require BOS Filter?', false);

// Replicates the Pine f_cisd() stateful function.
// Returns a numeric state series: 1 = Bullish, -1 = Bearish, 0 = Neutral.
function computeCisdState(myOpenArr, myHighArr, myLowArr, myCloseArr) {
	const myLength = myOpenArr.length;
	// fixed: "new Array(...)" is not allowed by the engine, use Array(...) instead
	const myStateArr = Array(myLength).fill(0);
	let myBullT = null;
	let myBearT = null;
	let myState = 0;

	for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
		const myIsInside = myIndex > 0 &&
			myHighArr[myIndex] < myHighArr[myIndex - 1] &&
			myLowArr[myIndex] > myLowArr[myIndex - 1];

		if (myBullT !== null && myIndex > 0 &&
			myCloseArr[myIndex] > myBullT && myCloseArr[myIndex - 1] <= myBullT) {
			myState = 1;
		}
		if (myBearT !== null && myIndex > 0 &&
			myCloseArr[myIndex] < myBearT && myCloseArr[myIndex - 1] >= myBearT) {
			myState = -1;
		}

		if (myCloseArr[myIndex] < myOpenArr[myIndex] && !myIsInside) {
			myBullT = myOpenArr[myIndex];
		}
		if (myCloseArr[myIndex] > myOpenArr[myIndex] && !myIsInside) {
			myBearT = myOpenArr[myIndex];
		}

		myStateArr[myIndex] = myState;
	}

	return myStateArr;
}

// Current (lower) timeframe CISD state
const myStateL = computeCisdState(open, high, low, close);

// Higher timeframe CISD state, fetched non-repainting
const myHigherData = await request.history(current.ticker, myHighTF);
assert(!myHigherData.error, `Error fetching higher TF data: "${myHigherData.error}"`);

const myStateHRaw = computeCisdState(myHigherData.open, myHigherData.high, myHigherData.low, myHigherData.close);

// Land the H1 state onto the current chart's timestamps without lookahead:
// each H1 value becomes visible starting from the first current-chart
// candle whose time is >= that H1 bar's time, then held constant forward.
const myStateHLanded = land_points_onto_series(myHigherData.time, myStateHRaw, time, 'ge');
const myStateH = interpolate_sparse_series(myStateHLanded, 'constant');

const myAlignedBull = for_every(myStateH, myStateL, (_h, _l) => _h === 1 && _l === 1);
const myAlignedBear = for_every(myStateH, myStateL, (_h, _l) => _h === -1 && _l === -1);

// BOS filter: high above prior 10-bar highest (shifted by 1), low below prior 10-bar lowest
const myHighest10Prev = shift(highest(high, 10), 1);
const myLowest10Prev = shift(lowest(low, 10), 1);
const myBosBull = for_every(high, myHighest10Prev, (_h, _hh) => _hh !== null && _h > _hh);
const myBosBear = for_every(low, myLowest10Prev, (_l, _ll) => _ll !== null && _l < _ll);

// FVG filter: current low above high 2 bars ago, or current high below low 2 bars ago
const myHigh2 = shift(high, 2);
const myLow2 = shift(low, 2);
const myFvgBull = for_every(low, myHigh2, (_l, _h2) => _h2 !== null && _l > _h2);
const myFvgBear = for_every(high, myLow2, (_h, _l2) => _l2 !== null && _h < _l2);

// Raw entry conditions (approximation of strategy.entry gating)
const myLongEntryRaw = for_every(myAlignedBull, myBosBull, myFvgBull,
	(_ab, _bb, _fb) => _ab && (!myUseBOS || _bb) && _fb);
const myShortEntryRaw = for_every(myAlignedBear, myBosBear, myFvgBear,
	(_ab, _bb, _fb) => _ab && (!myUseBOS || _bb) && _fb);

// Simulate "one position at a time" like strategy.position_size == 0
const myAtrValue = atr(high, low, close, 14);
let myPositionState = 0; // 0 flat, 1 long, -1 short
// fixed: "new Array(...)" is not allowed by the engine, use Array(...) instead
const myLongSignal = Array(close.length).fill(false);
const myShortSignal = Array(close.length).fill(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPositionState === 0) {
		if (myLongEntryRaw[myIndex]) {
			myLongSignal[myIndex] = true;
			myPositionState = 1;
		}
		else if (myShortEntryRaw[myIndex]) {
			myShortSignal[myIndex] = true;
			myPositionState = -1;
		}
	}
	else {
		const mySlDist = (myAtrValue[myIndex] || 0) * 1.5;

		if (myPositionState === 1) {
			const myStopHit = close[myIndex] <= close[myIndex] - mySlDist;
			const myLimitHit = close[myIndex] >= close[myIndex] + (mySlDist * myRRRatio);
			if (myStopHit || myLimitHit) {
				myPositionState = 0;
			}
		}
		else if (myPositionState === -1) {
			const myStopHit = close[myIndex] >= close[myIndex] + mySlDist;
			const myLimitHit = close[myIndex] <= close[myIndex] - (mySlDist * myRRRatio);
			if (myStopHit || myLimitHit) {
				myPositionState = 0;
			}
		}
	}
}

// FVG shapes
const myFvgBullMarks = for_every(myFvgBull, _b => _b ? constants.icons.triangle_up : null);
const myFvgBearMarks = for_every(myFvgBear, _b => _b ? constants.icons.triangle_down : null);

paint(myFvgBullMarks, { name: 'FVG Bull', style: 'labels_below', color: 'teal' });
paint(myFvgBearMarks, { name: 'FVG Bear', style: 'labels_above', color: 'orange' });

// MTF alignment background coloring (approximation of bgcolor)
const myBgColors = for_every(myAlignedBull, myAlignedBear, (_ab, _as) => {
	if (_ab) return 'rgba(0,128,0,0.1)';
	if (_as) return 'rgba(255,0,0,0.1)';
	return null;
});
color_candles(myBgColors);

// Register signals for scanning / alerts / backtesting
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');
register_signal(myAlignedBull, 'MTF Aligned Bullish');
register_signal(myAlignedBear, 'MTF Aligned Bearish');