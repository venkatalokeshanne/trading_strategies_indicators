describe_indicator('UT Bot 5min Strategy Signals', 'price');

// ===================== INPUTS =====================
const generalTab = input.tab('UT Bot');
const i_key = generalTab.number('UT Bot Key Value', 2.2, { min: 0.1, max: 20, step: 0.1 });
const i_atrLen = generalTab.number('ATR Period', 10, { min: 1, max: 200 });

const emaTab = input.tab('EMA Filters');
const i_useEmaFilter = emaTab.boolean('5min EMA 200 Filter', true);
const i_emaTrendLen = emaTab.number('5min EMA Trend Length', 200, { min: 1, max: 500 });
const i_emaFastLen = emaTab.number('5min EMA Fast Length', 21, { min: 1, max: 500 });
const i_use1min = emaTab.boolean('1min EMA Filter', true);
const i_ema1minLen = emaTab.number('1min EMA Length', 21, { min: 1, max: 500 });
const i_useHtf = emaTab.boolean('15min EMA 200 Filter', true);
const i_htfEmaLen = emaTab.number('15min EMA Length', 200, { min: 1, max: 500 });

const adxTab = input.tab('ADX / Distance');
const i_useAdx = adxTab.boolean('ADX Filter', true);
const i_adxLen = adxTab.number('ADX Length', 14, { min: 1, max: 100 });
const i_adxThreshold = adxTab.number('Minimum ADX', 23, { min: 1, max: 100 });
const i_useDistance = adxTab.boolean('EMA Distance Filter', true);
const i_distanceFilter = adxTab.number('Min Distance', 0.001, { min: 0, max: 1, step: 0.0001 });

const tpslTab = input.tab('TP / SL / Time');
const i_tpPercent = tpslTab.number('Take Profit (%)', 1.5, { min: 0, max: 100, step: 0.1 });
const i_slPercent = tpslTab.number('Stop Loss (%)', 1.0, { min: 0, max: 100, step: 0.1 });
const i_startHour = tpslTab.number('Start Hour', 3, { min: 0, max: 23 });
const i_endHour = tpslTab.number('End Hour', 15, { min: 0, max: 23 });

// ===================== BASE SERIES =====================
const src = close;
const xATR = atr(high, low, close, i_atrLen);
const nLoss = mult(xATR, i_key);

// ===================== UT TRAIL (recursive, matches Pine exactly) =====================
// Pine's nz(trail[1]) treats the very first "na" trail value as 0.
const myTrail = series_of(null);
for (let myIndex = 0; myIndex < src.length; myIndex += 1) {
	const myPrev = myIndex === 0 ? 0 : (myTrail[myIndex - 1] === null ? 0 : myTrail[myIndex - 1]);
	const mySrc = src[myIndex];
	const mySrcPrev = myIndex === 0 ? null : src[myIndex - 1];
	const myLoss = nLoss[myIndex];

	if (myLoss === null || mySrc === null) {
		myTrail[myIndex] = myPrev;
		continue;
	}

	if (mySrcPrev !== null && mySrc > myPrev && mySrcPrev > myPrev) {
		myTrail[myIndex] = Math.max(myPrev, mySrc - myLoss);
	}
	else if (mySrcPrev !== null && mySrc < myPrev && mySrcPrev < myPrev) {
		myTrail[myIndex] = Math.min(myPrev, mySrc + myLoss);
	}
	else if (mySrc > myPrev) {
		myTrail[myIndex] = mySrc - myLoss;
	}
	else {
		myTrail[myIndex] = mySrc + myLoss;
	}
}

// ===================== EMAs =====================
const myEmaFast = ema(src, i_emaFastLen);
const myEmaTrend = ema(src, i_emaTrendLen);

// ===================== LOWER TIME FRAME & HTF EMA (approximated via request.history) =====================
const myOtherTfPromises = Promise.all([
	request.history(current.ticker, '1'),
	request.history(current.ticker, '15')
]);
const [myData1min, myData15min] = await myOtherTfPromises;
assert(!myData1min.error, `Error fetching 1min data: ${myData1min.error}`);
assert(!myData15min.error, `Error fetching 15min data: ${myData15min.error}`);

const myEma1minRaw = ema(myData1min.close, i_ema1minLen);
const myHtfEmaRaw = ema(myData15min.close, i_htfEmaLen);

// Landing lower resolution computed series onto the current chart's candles.
// Using 'constant' interpolation (no forward-looking) to keep this backtestable,
// unlike Pine's request.security which can repaint on realtime bars.
const myEma1minLanded = interpolate_sparse_series(
	land_points_onto_series(myData1min.time, myEma1minRaw, time, 'le'),
	'constant'
);
const myHtfEmaLanded = interpolate_sparse_series(
	land_points_onto_series(myData15min.time, myHtfEmaRaw, time, 'le'),
	'constant'
);

// ===================== ADX =====================
const myAdxObject = indicators.adx(i_adxLen);
const myAdx = myAdxObject.adx;

// ===================== DISTANCE =====================
const myDistance = div(for_every(src, myEmaFast, (_s, _e) => Math.abs(_s - _e)), src);

// ===================== TIME FILTER =====================
const myHours = time.map(_t => time_of(_t).hours);
const myTimeAllowed = myHours.map(_h => _h >= i_startHour && _h < i_endHour);

// ===================== CROSSOVER / CROSSUNDER HELPERS =====================
const myCrossOver = for_every(src, myTrail, shift(src, 1), shift(myTrail, 1), (_s, _t, _sPrev, _tPrev) => {
	return _sPrev !== null && _tPrev !== null && _sPrev <= _tPrev && _s > _t;
});
const myCrossUnder = for_every(myTrail, src, shift(myTrail, 1), shift(src, 1), (_t, _s, _tPrev, _sPrev) => {
	return _sPrev !== null && _tPrev !== null && _sPrev >= _tPrev && _s < _t;
});
const myFastCrossUnderTrend = for_every(myEmaFast, myEmaTrend, shift(myEmaFast, 1), shift(myEmaTrend, 1), (_f, _t, _fPrev, _tPrev) => {
	return _fPrev !== null && _tPrev !== null && _fPrev >= _tPrev && _f < _t;
});
const myFastCrossOverTrend = for_every(myEmaFast, myEmaTrend, shift(myEmaFast, 1), shift(myEmaTrend, 1), (_f, _t, _fPrev, _tPrev) => {
	return _fPrev !== null && _tPrev !== null && _fPrev <= _tPrev && _f > _t;
});

// ===================== ENTRY CONDITIONS =====================
const myLongCondition = for_every(
	src, myEmaFast, myEmaTrend, myEma1minLanded, myHtfEmaLanded, myAdx, myDistance, myCrossOver,
	(_s, _ef, _et, _e1, _ehtf, _adx, _dist, _co) => {
		if (!_co) return false;
		if (_s <= _ef) return false;
		if (i_useEmaFilter && !(_s > _et)) return false;
		if (i_use1min && !(_s > _e1)) return false;
		if (i_useHtf && !(_s > _ehtf)) return false;
		if (i_useAdx && !(_adx > i_adxThreshold)) return false;
		if (i_useDistance && !(_dist > i_distanceFilter)) return false;
		return true;
	}
);
const myShortCondition = for_every(
	src, myEmaFast, myEmaTrend, myEma1minLanded, myHtfEmaLanded, myAdx, myDistance, myCrossUnder,
	(_s, _ef, _et, _e1, _ehtf, _adx, _dist, _cu) => {
		if (!_cu) return false;
		if (_s >= _ef) return false;
		if (i_useEmaFilter && !(_s < _et)) return false;
		if (i_use1min && !(_s < _e1)) return false;
		if (i_useHtf && !(_s < _ehtf)) return false;
		if (i_useAdx && !(_adx > i_adxThreshold)) return false;
		if (i_useDistance && !(_dist > i_distanceFilter)) return false;
		return true;
	}
);

const myLongEntrySignal = for_every(myLongCondition, myTimeAllowed, (_l, _ta) => _l && _ta);
const myShortEntrySignal = for_every(myShortCondition, myTimeAllowed, (_s, _ta) => _s && _ta);

// EMA based exit crosses
const myLongEmaExitSignal = myFastCrossUnderTrend;
const myShortEmaExitSignal = myFastCrossOverTrend;

// End of day forced close signal (approximate strategy.close_all)
const myDailyCloseSignal = myHours.map(_h => _h >= i_endHour);

// ===================== REGISTER SIGNALS (for scanner/alerts/strategy tester) =====================
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongEmaExitSignal, 'Long EMA Exit');
register_signal(myShortEmaExitSignal, 'Short EMA Exit');
register_signal(myDailyCloseSignal, 'Daily Close');

// ===================== PAINT =====================
paint(myEmaTrend, { name: 'EMA Trend', color: '#2962FF', thickness: 2 });
paint(myEmaFast, { name: 'EMA Fast', color: '#FF9800', thickness: 1 });
paint(i_useHtf ? myHtfEmaLanded : series_of(null), { name: 'HTF EMA', color: '#9C27B0', thickness: 2 });

const myLongMarks = for_every(myLongEntrySignal, low, (_sig, _l) => _sig ? _l : null);
const myShortMarks = for_every(myShortEntrySignal, high, (_sig, _h) => _sig ? _h : null);

// Renamed these painted marker series so their names no longer clash
// with the "Long Entry" / "Short Entry" names used by register_signal().
// Output series names (paint vs register_signal) must all be unique.
paint(myLongMarks, { name: 'Long Entry Marker', style: 'labels_below', color: '#26A69A' });
paint(myShortMarks, { name: 'Short Entry Marker', style: 'labels_above', color: '#EF5350' });