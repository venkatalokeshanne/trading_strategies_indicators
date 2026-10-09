describe_indicator('Heikin Ashi No Wick Reversal Signal MTF', 'price');

// Timeframe used to compute the Heikin Ashi "no wick" signals
const mySignalTF = input.select('Signal Timeframe', '5', constants.time_frames);

// Fetch Heikin Ashi candles for the selected timeframe
const myHaData = await request.history(current.ticker, mySignalTF, { chart_type: 'heikinashi' });
assert(!myHaData.error, 'Error fetching Heikin Ashi data: ' + myHaData.error);

const myHaOpen = myHaData.open;
const myHaHigh = myHaData.high;
const myHaLow = myHaData.low;
const myHaClose = myHaData.close;
const myHaTime = myHaData.time;

// Sequential state machine replicating the Pine Script "var" memory logic.
// This must be computed with a loop since each candle depends on the
// previous candle's state (not expressible via built-in series functions).
// Avoid "new Array(...)" (prohibited); build via Array.from instead.
const myLongSignalSeries = Array.from({ length: myHaTime.length }, () => false);
const myShortSignalSeries = Array.from({ length: myHaTime.length }, () => false);

let myWaitingBullNoWick = false;
let myWaitingBearNoWick = false;

for (let myIndex = 1; myIndex < myHaTime.length; myIndex += 1) {
	const myBull = myHaClose[myIndex] > myHaOpen[myIndex];
	const myBear = myHaClose[myIndex] < myHaOpen[myIndex];
	const myPrevBull = myHaClose[myIndex - 1] > myHaOpen[myIndex - 1];
	const myPrevBear = myHaClose[myIndex - 1] < myHaOpen[myIndex - 1];
	const myNoBottomWick = myHaLow[myIndex] === myHaOpen[myIndex];
	const myNoTopWick = myHaHigh[myIndex] === myHaOpen[myIndex];
	const myNewBullSequence = myBull && myPrevBear;
	const myNewBearSequence = myBear && myPrevBull;

	if (myNewBullSequence) {
		myWaitingBullNoWick = true;
		myWaitingBearNoWick = false;
	}
	if (myNewBearSequence) {
		myWaitingBearNoWick = true;
		myWaitingBullNoWick = false;
	}

	const myLongSignal = myWaitingBullNoWick && myBull && myNoBottomWick;
	const myShortSignal = myWaitingBearNoWick && myBear && myNoTopWick;

	if (myLongSignal) {
		myWaitingBullNoWick = false;
	}
	if (myShortSignal) {
		myWaitingBearNoWick = false;
	}

	myLongSignalSeries[myIndex] = myLongSignal;
	myShortSignalSeries[myIndex] = myShortSignal;
}

// Land the signal timeframe results onto the current chart's candles.
// "eq" requires an exact timestamp match (both series derive from the
// same exchange calendar, so bar start times line up for valid HTF/LTF pairs).
const myLongLanded = land_points_onto_series(myHaTime, myLongSignalSeries, time, 'eq');
const myShortLanded = land_points_onto_series(myHaTime, myShortSignalSeries, time, 'eq');

const myLongMarksFinal = low.map((_lowValue, _i) => myLongLanded[_i] === true ? _lowValue : null);
const myShortMarksFinal = high.map((_highValue, _i) => myShortLanded[_i] === true ? _highValue : null);

paint(myLongMarksFinal, { name: 'LongSignal', style: 'labels_below', color: 'green' });
paint(myShortMarksFinal, { name: 'ShortSignal', style: 'labels_above', color: 'red' });

const myLongSignalBool = myLongLanded.map(_v => _v === true);
const myShortSignalBool = myShortLanded.map(_v => _v === true);

register_signal(myLongSignalBool, 'HA Long No Wick MTF');
register_signal(myShortSignalBool, 'HA Short No Wick MTF');