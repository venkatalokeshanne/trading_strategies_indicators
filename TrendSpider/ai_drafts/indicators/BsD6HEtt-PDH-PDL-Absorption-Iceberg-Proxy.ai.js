describe_indicator('PDH PDL Absorption Iceberg Proxy', 'price');

// ============================================================
// SECTION 1: Previous Day High/Low (+ optional Premarket H/L)
// ============================================================
const myShowPDHL = input.boolean('Show Prior Day H/L', true);
const myShowPMHL = input.boolean('Show Premarket H/L', false);
const myLevelTolPts = input.number('Level Tolerance Pts', 2.0, { min: 0 });

// SECTION 2 inputs
const myVolLen = input.number('Volume Lookback', 20, { min: 5 });
const myRangeLen = input.number('Range Lookback', 20, { min: 5 });
const myVolMult = input.number('Volume Threshold x', 1.8, { min: 1, step: 0.1 });
const myRangeMult = input.number('Range Threshold x', 0.6, { min: 0.1, step: 0.1 });
const myOnlyAtLevel = input.boolean('Only Near PDH/PDL', true);

// Fetch daily data to derive "previous day" high/low (equivalent to high[1]/low[1] on D timeframe)
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);

// Build "previous day high/low" series aligned to daily candles (shifted by 1 day)
const myPrevDayHighDaily = shift(myDailyData.high, 1);
const myPrevDayLowDaily = shift(myDailyData.low, 1);

// Land these daily values onto the current chart's candles
const myPrevDayHighLanded = land_points_onto_series(myDailyData.time, myPrevDayHighDaily, time, 'ge');
const myPrevDayLowLanded = land_points_onto_series(myDailyData.time, myPrevDayLowDaily, time, 'ge');
const myPrevDayHigh = interpolate_sparse_series(myPrevDayHighLanded, 'constant');
const myPrevDayLow = interpolate_sparse_series(myPrevDayLowLanded, 'constant');

const myPDHLine = paint(myShowPDHL ? myPrevDayHigh : constants.empty_series, { name: 'PDH', color: 'red', style: 'line', thickness: 1 });
const myPDLLine = paint(myShowPDHL ? myPrevDayLow : constants.empty_series, { name: 'PDL', color: 'green', style: 'line', thickness: 1 });

// Premarket High/Low (approximation): computed from the current chart's candles,
// using the exchange's defined pre-market session window. This requires the chart
// to have extended-hours data loaded (ext_session enabled); otherwise it stays empty.
const myPMHigh = series_of(null);
const myPMLow = series_of(null);

if (current.ext_session_premarket) {
	let myRunningPMHigh = null;
	let myRunningPMLow = null;
	let myPrevDayId = null;

	for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
		const myBarInfo = bar_at(time[myIndex]);
		const myDayId = myBarInfo.session;

		if (myDayId !== myPrevDayId) {
			myRunningPMHigh = null;
			myRunningPMLow = null;
			myPrevDayId = myDayId;
		}

		const myTimeInfo = time_of(time[myIndex]);
		const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
		const myPMStartMin = current.ext_session_premarket.start.hours * 60 + current.ext_session_premarket.start.minutes;
		const myPMEndMin = current.ext_session_premarket.end.hours * 60 + current.ext_session_premarket.end.minutes;
		const myInPM = myMinutesOfDay >= myPMStartMin && myMinutesOfDay < myPMEndMin;

		if (myInPM) {
			myRunningPMHigh = myRunningPMHigh === null ? high[myIndex] : Math.max(myRunningPMHigh, high[myIndex]);
			myRunningPMLow = myRunningPMLow === null ? low[myIndex] : Math.min(myRunningPMLow, low[myIndex]);
		}

		myPMHigh[myIndex] = myRunningPMHigh;
		myPMLow[myIndex] = myRunningPMLow;
	}
}

paint(myShowPMHL ? myPMHigh : constants.empty_series, { name: 'PM High', color: 'orange', style: 'dotted', thickness: 2 });
paint(myShowPMHL ? myPMLow : constants.empty_series, { name: 'PM Low', color: 'blue', style: 'dotted', thickness: 2 });

// ============================================================
// SECTION 2: Absorption / Iceberg Proxy Detection
// ============================================================
const myAvgVol = sma(volume, myVolLen);
const myAvgRange = sma(sub(high, low), myRangeLen);
const myBarRange = sub(high, low);

const myHighVol = for_every(volume, myAvgVol, (_v, _av) => _v > _av * myVolMult);
const myTightRange = for_every(myBarRange, myAvgRange, (_r, _ar) => _r < _ar * myRangeMult);

const myNearPDH = for_every(close, myPrevDayHigh, (_c, _p) => Math.abs(_c - _p) <= myLevelTolPts);
const myNearPDL = for_every(close, myPrevDayLow, (_c, _p) => Math.abs(_c - _p) <= myLevelTolPts);
const myNearLevel = for_every(myNearPDH, myNearPDL, (_a, _b) => _a || _b);

const myRawAbsorption = for_every(myHighVol, myTightRange, (_hv, _tr) => _hv && _tr);
const myAbsorptionSignal = for_every(myRawAbsorption, myNearLevel, (_raw, _near) => myOnlyAtLevel ? (_raw && _near) : _raw);

// Flag shape above bars, matches Pine's plotshape triangledown "ABS"
const myAbsorptionMarks = for_every(myAbsorptionSignal, high, (_sig, _h) => _sig ? _h : null);
paint(myAbsorptionMarks, { name: 'Absorption', style: 'labels_above', color: 'fuchsia' });

// ============================================================
// SECTION 3: Signal for scanners / alerts / strategy tester
// ============================================================
register_signal(myAbsorptionSignal, 'Absorption Iceberg Detected');