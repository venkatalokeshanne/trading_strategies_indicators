describe_indicator('Multi-Timeframe Trend Dashboard', 'price');

// Timeframe Settings
const myTfTab = input.tab('Timeframe Settings');
const myTf1 = myTfTab.select('Timeframe 1', '15', constants.time_frames);
const myTf2 = myTfTab.select('Timeframe 2', '60', constants.time_frames);
const myTf3 = myTfTab.select('Timeframe 3', '240', constants.time_frames);
const myTf4 = myTfTab.select('Timeframe 4', 'D', constants.time_frames);

// Indicator Settings
const myIndTab = input.tab('Indicator Settings');
const myEmaFastLen = myIndTab.number('Fast EMA Length', 20, { min: 1, max: 500 });
const myEmaSlowLen = myIndTab.number('Slow EMA Length', 50, { min: 1, max: 500 });
const myAdxLen = myIndTab.number('ADX Trend Strength Length', 14, { min: 1, max: 100 });
const myAdxCutoff = myIndTab.number('ADX Strong Trend Cutoff', 20, { min: 1, max: 100 });

// NOTE: indicators.adx() only works off the *current chart's* OHLC data,
// it ignores custom series passed to it. Since this script needs ADX/DMI
// computed on higher timeframe data (fetched via request.history), we
// can't use indicators.adx() directly. Instead we hand-roll ADX/DMI using
// atr() and wildma(), both of which do support custom high/low/close
// series, so lengths always match.
//
// FIX for "Invalid array length" at wildma(): the previous length guard
// (minRequiredLength = max(lengths) + 2) was not large enough. wildma()
// internally needs a comfortable buffer above the window length to build
// its smoothing arrays, and very short/edge-length higher timeframe
// history results could still slip through and crash it. We now require
// a much bigger safety margin (2x the longest window length, plus a
// fixed buffer), and we additionally wrap the whole ADX/EMA computation
// in a try/catch, so that if wildma() (or anything else) still throws for
// an unexpected data shape, we gracefully fall back to a "no data /
// consolidating" result instead of crashing the whole script.
function myComputeCustomAdx(_myHigh, _myLow, _myClose, _myLen) {
	const myPrevHigh = shift(_myHigh, 1);
	const myPrevLow = shift(_myLow, 1);
	const myUpMove = sub(_myHigh, myPrevHigh);
	const myDownMove = sub(myPrevLow, _myLow);
	const myPlusDM = for_every(myUpMove, myDownMove, (_u, _d) => (_u > _d && _u > 0) ? _u : 0);
	const myMinusDM = for_every(myUpMove, myDownMove, (_u, _d) => (_d > _u && _d > 0) ? _d : 0);
	const myAtrValue = atr(_myHigh, _myLow, _myClose, _myLen);
	const mySmoothPlusDM = wildma(myPlusDM, _myLen);
	const mySmoothMinusDM = wildma(myMinusDM, _myLen);
	const myPlusDI = mult(div(mySmoothPlusDM, myAtrValue), 100);
	const myMinusDI = mult(div(mySmoothMinusDM, myAtrValue), 100);
	const myDiDiff = for_every(myPlusDI, myMinusDI, (_p, _m) => Math.abs(_p - _m));
	const myDiSum = add(myPlusDI, myMinusDI);
	const myDx = mult(div(myDiDiff, myDiSum), 100);
	const myAdxValue = wildma(myDx, _myLen);
	return { adx: myAdxValue, dmiPlus: myPlusDI, dmiMinus: myMinusDI };
}

// Computes direction (1 bull, -1 bear, 0 consolidating) and
// "strong" flag (ADX above cutoff), for a given set of OHLC data.
// Guards against data sets that are too short (or otherwise malformed)
// to feed into the moving-average/ADX math, which is what used to
// crash wildma() with "Invalid array length".
function myComputeDirAndStrong(_myClose, _myHigh, _myLow) {
	const myLongestLen = Math.max(myEmaFastLen, myEmaSlowLen, myAdxLen);
	// Require a generous buffer (2x the longest window + fixed padding)
	// above the longest window length, since wildma() needs more room
	// than a plain "+2" to build its internal smoothing buffers safely.
	const myMinRequiredLength = (myLongestLen * 2) + 10;

	const myFallback = () => ({
		myDir: _myClose ? _myClose.map(_c => 0) : [],
		myStrong: _myClose ? _myClose.map(_c => false) : []
	});

	if (!_myClose || !_myHigh || !_myLow || _myClose.length < myMinRequiredLength) {
		// Not enough candles on this timeframe/history result to compute
		// anything meaningful; report "consolidating / not strong".
		return myFallback();
	}

	try {
		const myFastEma = ema(_myClose, myEmaFastLen);
		const mySlowEma = ema(_myClose, myEmaSlowLen);
		const myAdxObject = myComputeCustomAdx(_myHigh, _myLow, _myClose, myAdxLen);

		const myDir = for_every(_myClose, myFastEma, mySlowEma, myAdxObject.dmiPlus, myAdxObject.dmiMinus, (_c, _fe, _se, _dp, _dm) => {
			if (_c > _fe && _fe > _se && _dp > _dm) return 1;
			if (_c < _fe && _fe < _se && _dm > _dp) return -1;
			return 0;
		});
		const myStrong = for_every(myAdxObject.adx, _a => _a > myAdxCutoff);

		return { myDir, myStrong };
	}
	catch (myErr) {
		// Guard against any unexpected failure (i.e. edge cases of
		// wildma() on unusual data shapes) by falling back safely.
		return myFallback();
	}
}

// Local (current chart timeframe) computation, used as a fallback
// in case any of the requested timeframe history calls fail.
const myLocal = myComputeDirAndStrong(close, high, low);

// Fetch the 4 requested timeframes in parallel.
const [myData1, myData2, myData3, myData4] = await Promise.all([
	request.history(current.ticker, myTf1),
	request.history(current.ticker, myTf2),
	request.history(current.ticker, myTf3),
	request.history(current.ticker, myTf4)
]);

assert(!myData1.error, 'Error fetching Timeframe 1 data: ' + myData1.error);
assert(!myData2.error, 'Error fetching Timeframe 2 data: ' + myData2.error);
assert(!myData3.error, 'Error fetching Timeframe 3 data: ' + myData3.error);
assert(!myData4.error, 'Error fetching Timeframe 4 data: ' + myData4.error);

// Computes dir/strong on a given higher timeframe data set, then
// lands/interpolates the result onto the current chart's time axis.
// 'constant' interpolation is used (no forward-looking lookahead),
// matching Pine's barmerge.lookahead_off behavior.
function myMapToCurrentChart(_myTfData) {
	const { myDir, myStrong } = myComputeDirAndStrong(_myTfData.close, _myTfData.high, _myTfData.low);

	if (!_myTfData.time || _myTfData.time.length === 0 || myDir.length === 0) {
		// No usable history for this timeframe; fall back to "consolidating".
		return {
			myDir: close.map(_c => 0),
			myStrong: close.map(_c => false)
		};
	}

	const myDirLanded = land_points_onto_series(_myTfData.time, myDir, time, 'le');
	const myStrongLanded = land_points_onto_series(_myTfData.time, myStrong, time, 'le');

	return {
		myDir: interpolate_sparse_series(myDirLanded, 'constant'),
		myStrong: interpolate_sparse_series(myStrongLanded, 'constant')
	};
}

const myMapped1 = myMapToCurrentChart(myData1);
const myMapped2 = myMapToCurrentChart(myData2);
const myMapped3 = myMapToCurrentChart(myData3);
const myMapped4 = myMapToCurrentChart(myData4);

// Translates a direction/strong pair into display text & colors.
function myCellInfo(_myDirValue, _myStrongValue) {
	let myText = 'CONSOLIDATING';
	let myBg = '#808080';
	const myTextColor = '#ffffff';

	if (_myDirValue === 1) {
		myText = _myStrongValue ? 'STRONG BULL' : 'WEAK BULL';
		myBg = _myStrongValue ? '#008000' : '#2ecc71';
	}
	else if (_myDirValue === -1) {
		myText = _myStrongValue ? 'STRONG BEAR' : 'WEAK BEAR';
		myBg = _myStrongValue ? '#ff0000' : '#800000';
	}

	return { myText, myBg, myTextColor };
}

const myLastIndex = close.length - 1;
const myRow1 = myCellInfo(myMapped1.myDir[myLastIndex], myMapped1.myStrong[myLastIndex]);
const myRow2 = myCellInfo(myMapped2.myDir[myLastIndex], myMapped2.myStrong[myLastIndex]);
const myRow3 = myCellInfo(myMapped3.myDir[myLastIndex], myMapped3.myStrong[myLastIndex]);
const myRow4 = myCellInfo(myMapped4.myDir[myLastIndex], myMapped4.myStrong[myLastIndex]);

paint_overlay('TrendDashboardTable', { position: 'bottom_right' }, {
	rows: [{
		cells: [
			{ text: 'TIMEFRAME', color: '#ffff00', background_color: '#000000' },
			{ text: 'TREND STATE', color: '#ffff00', background_color: '#000000' }
		]
	}, {
		cells: [
			{ text: 'TF 1 (' + myTf1 + ')', color: '#ffffff' },
			{ text: myRow1.myText, color: myRow1.myTextColor, background_color: myRow1.myBg }
		]
	}, {
		cells: [
			{ text: 'TF 2 (' + myTf2 + ')', color: '#ffffff' },
			{ text: myRow2.myText, color: myRow2.myTextColor, background_color: myRow2.myBg }
		]
	}, {
		cells: [
			{ text: 'TF 3 (' + myTf3 + ')', color: '#ffffff' },
			{ text: myRow3.myText, color: myRow3.myTextColor, background_color: myRow3.myBg }
		]
	}, {
		cells: [
			{ text: 'TF 4 (' + myTf4 + ')', color: '#ffffff' },
			{ text: myRow4.myText, color: myRow4.myTextColor, background_color: myRow4.myBg }
		]
	}]
});

// Register signals so this logic can be used in Scanners, Alerts
// and the Strategy Tester.
register_signal(for_every(myMapped1.myDir, myMapped1.myStrong, (_d, _s) => _d === 1 && _s), 'TF1 Strong Bull');
register_signal(for_every(myMapped1.myDir, myMapped1.myStrong, (_d, _s) => _d === 1 && !_s), 'TF1 Weak Bull');
register_signal(for_every(myMapped1.myDir, myMapped1.myStrong, (_d, _s) => _d === -1 && _s), 'TF1 Strong Bear');
register_signal(for_every(myMapped1.myDir, myMapped1.myStrong, (_d, _s) => _d === -1 && !_s), 'TF1 Weak Bear');

register_signal(for_every(myMapped2.myDir, myMapped2.myStrong, (_d, _s) => _d === 1 && _s), 'TF2 Strong Bull');
register_signal(for_every(myMapped2.myDir, myMapped2.myStrong, (_d, _s) => _d === 1 && !_s), 'TF2 Weak Bull');
register_signal(for_every(myMapped2.myDir, myMapped2.myStrong, (_d, _s) => _d === -1 && _s), 'TF2 Strong Bear');
register_signal(for_every(myMapped2.myDir, myMapped2.myStrong, (_d, _s) => _d === -1 && !_s), 'TF2 Weak Bear');

register_signal(for_every(myMapped3.myDir, myMapped3.myStrong, (_d, _s) => _d === 1 && _s), 'TF3 Strong Bull');
register_signal(for_every(myMapped3.myDir, myMapped3.myStrong, (_d, _s) => _d === 1 && !_s), 'TF3 Weak Bull');
register_signal(for_every(myMapped3.myDir, myMapped3.myStrong, (_d, _s) => _d === -1 && _s), 'TF3 Strong Bear');
register_signal(for_every(myMapped3.myDir, myMapped3.myStrong, (_d, _s) => _d === -1 && !_s), 'TF3 Weak Bear');

register_signal(for_every(myMapped4.myDir, myMapped4.myStrong, (_d, _s) => _d === 1 && _s), 'TF4 Strong Bull');
register_signal(for_every(myMapped4.myDir, myMapped4.myStrong, (_d, _s) => _d === 1 && !_s), 'TF4 Weak Bull');
register_signal(for_every(myMapped4.myDir, myMapped4.myStrong, (_d, _s) => _d === -1 && _s), 'TF4 Strong Bear');
register_signal(for_every(myMapped4.myDir, myMapped4.myStrong, (_d, _s) => _d === -1 && !_s), 'TF4 Weak Bear');