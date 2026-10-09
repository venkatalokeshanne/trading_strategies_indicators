describe_indicator('Run Signal', 'price');

// Signal color input (shape color can be customized by user)
const mySignalColor = input.color('Signal Color', 'red');

// Fetch all required multi-timeframe data in parallel
const [myDailyData, myH4Data, myH2Data, myM15Data] = await Promise.all([
	request.history(current.ticker, 'D'),
	request.history(current.ticker, '240'),
	request.history(current.ticker, '120'),
	request.history(current.ticker, '15')
]);

assert(!myDailyData.error, "Error fetching Daily data: " + myDailyData.error);
assert(!myH4Data.error, "Error fetching 4H data: " + myH4Data.error);
assert(!myH2Data.error, "Error fetching 2H data: " + myH2Data.error);
assert(!myM15Data.error, "Error fetching 15m data: " + myM15Data.error);

// --- Condition 1: Daily close crosses under Daily HMA(200) ---
const myDailyHma = hullma(myDailyData.close, 200);
const myDailyClosePrev = shift(myDailyData.close, 1);
const myDailyHmaPrev = shift(myDailyHma, 1);

const myCond1Daily = for_every(
	myDailyData.close, myDailyHma, myDailyClosePrev, myDailyHmaPrev,
	(_c, _h, _cp, _hp) => (_cp >= _hp && _c < _h) ? 1 : 0
);

// --- Condition 2: Daily momentum below zero and decreasing ---
const myDailyMom = momentum(myDailyData.close, 14);
const myDailyMomPrev = shift(myDailyMom, 1);

const myCond2Daily = for_every(
	myDailyMom, myDailyMomPrev,
	(_m, _mp) => (_m < 0 && _m < _mp) ? 1 : 0
);

// --- Condition 3: 4H HMA(200) above 4H close ---
const myH4Hma = hullma(myH4Data.close, 200);

const myCond3H4 = for_every(
	myH4Hma, myH4Data.close,
	(_h, _c) => (_h > _c) ? 1 : 0
);

// --- Condition 4: 2H HMA/EMA distance decreasing while HMA above EMA ---
const myH2Hma = hullma(myH2Data.close, 200);
const myH2Ema = ema(myH2Data.close, 200);
const myH2Distance = sub(myH2Hma, myH2Ema);
const myH2DistancePrev = shift(myH2Distance, 1);

const myCond4H2 = for_every(
	myH2Distance, myH2DistancePrev, myH2Hma, myH2Ema,
	(_d, _dp, _h, _e) => (_d < _dp && _h > _e) ? 1 : 0
);

// --- Condition 5: 15m HMA(200) below 15m EMA(200) ---
const myM15Hma = hullma(myM15Data.close, 200);
const myM15Ema = ema(myM15Data.close, 200);

const myCond5M15 = for_every(
	myM15Hma, myM15Ema,
	(_h, _e) => (_h < _e) ? 1 : 0
);

// Land each condition onto the current chart's timestamps.
// Using "le" (last timestamp <= current bar time) avoids look-ahead bias,
// since the corresponding higher/other timeframe bar must be closed already.
const myCond1Landed = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myCond1Daily, time, 'le'), 'constant'
);
const myCond2Landed = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myCond2Daily, time, 'le'), 'constant'
);
const myCond3Landed = interpolate_sparse_series(
	land_points_onto_series(myH4Data.time, myCond3H4, time, 'le'), 'constant'
);
const myCond4Landed = interpolate_sparse_series(
	land_points_onto_series(myH2Data.time, myCond4H2, time, 'le'), 'constant'
);
const myCond5Landed = interpolate_sparse_series(
	land_points_onto_series(myM15Data.time, myCond5M15, time, 'le'), 'constant'
);

// Combine all conditions
const myRunSignal = for_every(
	myCond1Landed, myCond2Landed, myCond3Landed, myCond4Landed, myCond5Landed,
	(_c1, _c2, _c3, _c4, _c5) => Boolean(_c1 && _c2 && _c3 && _c4 && _c5)
);

// Shape series: only non-null on signal bars
const myRunSignalShape = for_every(
	myRunSignal, high,
	(_signal, _high) => _signal ? _high : null
);

paint(myRunSignalShape, {
	style: 'labels_above',
	color: mySignalColor,
	name: 'RunSignal'
});

// Register signal for scanners, alerts and strategy testing
register_signal(myRunSignal, 'Run Signal');