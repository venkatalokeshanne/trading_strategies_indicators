describe_indicator('Quantum Harmonic Oscillator (QHO)', 'lower', { decimals: 3 });

// ===================== INPUTS ===================== //
const myTauTab = input.tab('Parameters');
// Shortened input titles to satisfy the platform's input name length limit
const myLength = myTauTab.number('Lookback (tau)', 20, { min: 2, max: 500 });
const myKForce = myTauTab.number('Spring Const (k)', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myExtreme = myTauTab.number('Energy Threshold', 2.5, { min: 0.5, max: 20, step: 0.1 });

const mySessionTab = input.tab('Session');
const myUseSession = mySessionTab.boolean('Use Session Filter', true);

const myTfTab = input.tab('Timeframe');
// "Chart" means "use the current chart resolution", equivalent to Pine's empty string timeframe input
const myTfChoice = myTfTab.select('Timeframe', 'Chart', ['Chart', ...constants.time_frames]);

// ===================== DATA PIPELINE ===================== //
let myTfClose = close;
let myTfTime = time;

if (myTfChoice !== 'Chart') {
	const myHistoryData = await request.history(current.ticker, myTfChoice);
	assert(!myHistoryData.error, `Error fetching history: ${myHistoryData.error}`);
	myTfClose = myHistoryData.close;
	myTfTime = myHistoryData.time;
}

// Land the (possibly higher timeframe) close series onto the current chart's
// timeline, carrying the last known value forward (constant interpolation),
// which mirrors Pine's barmerge.gaps_on + fixnan() combination without
// repainting or looking into the future.
const myTfCloseLandedSparse = myTfChoice === 'Chart'
	? myTfClose
	: land_points_onto_series(myTfTime, myTfClose, time, 'le');

const myTfCloseAligned = myTfChoice === 'Chart'
	? myTfClose
	: interpolate_sparse_series(myTfCloseLandedSparse, 'constant');

// ===================== MATH ENGINE ===================== //
const mySystemNoise = stdev(myTfCloseAligned, myLength);
const myBaseline = sma(myTfCloseAligned, myLength);

// Signed Displacement (Z-score), guarding against division by zero
const mySignedDisplacement = for_every(
	myTfCloseAligned,
	myBaseline,
	mySystemNoise,
	(_tfClose, _baseline, _noise) => (_tfClose - _baseline) / (_noise > 0 ? _noise : 1)
);

// Core Equation: U = 0.5 * k * x^2 * sign(x)
const myPotentialEnergy = for_every(
	mySignedDisplacement,
	_x => 0.5 * myKForce * Math.pow(_x, 2) * Math.sign(_x)
);

// ===================== SESSION FILTER ===================== //
// Assumption: the exchange timezone of the current symbol represents the
// "America/New_York" session used in the original Pine script. This holds
// true for US equities, which is the intended use case here.
const myInSession = time.map(_t => {
	if (!myUseSession) {
		return true;
	}
	const myTimeInfo = time_of(_t);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myIsWeekday = myTimeInfo.dayOfWeek >= 1 && myTimeInfo.dayOfWeek <= 5;
	const myIsRegularHours = myMinutesOfDay >= (9 * 60 + 30) && myMinutesOfDay <= (16 * 60);
	return myIsWeekday && myIsRegularHours;
});

// ===================== SIGNALS ===================== //
const myLongEntrySignal = for_every(
	myPotentialEnergy,
	(_u, _prev, _index) => (_u < -myExtreme) && myInSession[_index]
);

const myCloseSignal = for_every(
	myPotentialEnergy,
	(_u, _prev, _index) => (_u >= 0) && myInSession[_index]
);

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myCloseSignal, 'Close Position');

// ===================== CHART METRICS ===================== //
const myEnergyColor = for_every(myPotentialEnergy, _u => _u > 0 ? '#9CCC65' : '#FFA726');

paint(myPotentialEnergy, { name: 'System U', style: 'column', color: myEnergyColor });
paint(horizontal_line(myExtreme), { name: 'Upper', color: '#EF5350', style: 'dotted' });
paint(horizontal_line(-myExtreme), { name: 'Lower', color: '#66BB6A', style: 'dotted' });
paint(horizontal_line(0), { name: 'Axis', color: '#9E9E9E', style: 'dotted' });