describe_indicator('Basic CRT', 'price');

// NOTE: Pine's "confirmed" (barstate.isconfirmed) check has no direct
// equivalent in this engine - historical candles are always "confirmed".
// The input is kept for parity but has no functional effect here.
// NOTE: Pine line styles "arrow_right" and "dashed" are not supported
// by paint(); they are approximated with "line" and "dotted".

const myCrtTab = input.tab('CRT');

const myColorRow = myCrtTab.row();
const myBullColor = myColorRow.color('Bull CRT Color', 'green');
const myBearColor = myColorRow.color('Bear CRT Color', 'red');

const mySweepRow = myCrtTab.row();
const myShowSweep = mySweepRow.boolean('Show Sweep Lines', true);
const mySweepStyle = mySweepRow.select('Sweep Style', 'line', ['line', 'dotted']);

const myDrawRow = myCrtTab.row();
const myShowDraw = myDrawRow.boolean('Show Draw Lines', true);
const myDrawStyle = myDrawRow.select('Draw Style', 'line', ['line', 'dotted']);

const myConfirmed = myCrtTab.boolean('Confirmed (no effect, kept for parity)', true);

const myTfTab = input.tab('Timeframes');
const myTfFilterActive = myTfTab.boolean('Timeframe Filter', true);
const myTfMin = myTfTab.number('Minimal Timeframe (minutes)', 1, { min: 1, max: 100000 });
const myTfMax = myTfTab.number('Maximal Timeframe (minutes)', 15, { min: 1, max: 100000 });

// Converts the current chart resolution string into minutes, so it can
// be compared against the user defined min/max timeframe filter.
function myResolutionToMinutes(_res) {
	if (!isNaN(Number(_res))) {
		return Number(_res);
	}
	if (_res === 'D') {
		return 1440;
	}
	if (_res === 'W') {
		return 10080;
	}
	if (_res === 'M') {
		return 43200;
	}
	return 1440;
}

const myCurrentTfMinutes = myResolutionToMinutes(current.resolution);
const myTfFilterPasses = !myTfFilterActive || (myCurrentTfMinutes >= myTfMin && myCurrentTfMinutes <= myTfMax);

const myBullCrt = series_of(false);
const myBearCrt = series_of(false);
const mySweepLevel = series_of(null);
const myDrawLevel = series_of(null);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myIsBull = close[myIndex] > close[myIndex - 1] && low[myIndex] < low[myIndex - 1] && high[myIndex] < high[myIndex - 1] && myTfFilterPasses;
	const myIsBear = close[myIndex] < close[myIndex - 1] && low[myIndex] > low[myIndex - 1] && high[myIndex] > high[myIndex - 1] && myTfFilterPasses;

	myBullCrt[myIndex] = myIsBull;
	myBearCrt[myIndex] = myIsBear;

	if (myIsBull) {
		if (myShowSweep) {
			// bull: sweep is the low segment
			mySweepLevel[myIndex - 1] = low[myIndex - 1];
			mySweepLevel[myIndex] = low[myIndex - 1];
		}
		if (myShowDraw) {
			// bull: draw is the high segment
			myDrawLevel[myIndex - 1] = high[myIndex - 1];
			myDrawLevel[myIndex] = high[myIndex - 1];
		}
	}
	else if (myIsBear) {
		if (myShowDraw) {
			// bear: draw is the low segment
			myDrawLevel[myIndex - 1] = low[myIndex - 1];
			myDrawLevel[myIndex] = low[myIndex - 1];
		}
		if (myShowSweep) {
			// bear: sweep is the high segment
			mySweepLevel[myIndex - 1] = high[myIndex - 1];
			mySweepLevel[myIndex] = high[myIndex - 1];
		}
	}
}

const myCandleColors = for_every(myBullCrt, myBearCrt, (_bull, _bear) => _bull ? myBullColor : (_bear ? myBearColor : null));
color_candles(myCandleColors);

paint(mySweepLevel, { name: 'Sweep', style: mySweepStyle, color: 'black', thickness: 2 });
paint(myDrawLevel, { name: 'Draw', style: myDrawStyle, color: 'black', thickness: 2 });

register_signal(myBullCrt, 'Bullish CRT');
register_signal(myBearCrt, 'Bearish CRT');