describe_indicator('VWAP StdDev plus SVP Clean', 'price');
// NOTE: This is a best-effort port of a Pine Script v6 strategy into a
// TrendSpider indicator. TrendSpider has no native "Session Volume
// Profile Developing POC/VAH/VAL" data feed, no strategy broker emulation
// (position sizing, stop orders) and no generic multi-type anchor
// (Earnings/Dividends/Splits/Decade/Century). This script reproduces the
// VWAP + stdev band logic and the long/short signal condition as closely
// as possible, using "close" as the proxy source for the SVP POC/VAH/VAL
// inputs (which is also the literal default value used in the original
// Pine script's input.source() calls). Risk sizing (shares, stop ticks)
// is exposed as informational series only, since there is no broker here.

const myAnchorTab = input.tab('Anchor and Reset');
const myAnchor = myAnchorTab.select('Anchor Period', 'Session', ['Session', 'Week', 'Month', 'Quarter', 'Year']);
const myResetOnSessionOpen = myAnchorTab.boolean('Reset on Session Open', true);

const mySvpTab = input.tab('SVP and Risk');
// Shortened title to fit the platform's input name length limit.
const mySvpSourceName = mySvpTab.select('SVP Proxy Source', 'close', constants.price_source_options);
const myRiskPerTrade = mySvpTab.number('Risk per Trade ($)', 100, { min: 1, max: 1000000 });

const mySrc = hlc3;
const mySvpSource = market[mySvpSourceName];

// --- determine "new period" (reset) points, based on anchor selection ---
const myIsNewPeriod = series_of(false);
for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	if (myIndex === 0) {
		myIsNewPeriod[myIndex] = true;
		continue;
	}
	const myCurrentTime = time_of(time[myIndex]);
	const myPrevTime = time_of(time[myIndex - 1]);
	let myPeriodChanged = false;
	if (myAnchor === 'Session') myPeriodChanged = myCurrentTime.dayOfYear !== myPrevTime.dayOfYear || myCurrentTime.year !== myPrevTime.year;
	else if (myAnchor === 'Week') myPeriodChanged = myCurrentTime.weekOfYear !== myPrevTime.weekOfYear || myCurrentTime.year !== myPrevTime.year;
	else if (myAnchor === 'Month') myPeriodChanged = myCurrentTime.month !== myPrevTime.month || myCurrentTime.year !== myPrevTime.year;
	else if (myAnchor === 'Quarter') myPeriodChanged = myCurrentTime.quarter !== myPrevTime.quarter || myCurrentTime.year !== myPrevTime.year;
	else if (myAnchor === 'Year') myPeriodChanged = myCurrentTime.year !== myPrevTime.year;

	// approximation of "session open" detection: a new trading day start
	const myIsNewSessionOpen = myCurrentTime.dayOfYear !== myPrevTime.dayOfYear || myCurrentTime.year !== myPrevTime.year;

	myIsNewPeriod[myIndex] = myPeriodChanged || (myResetOnSessionOpen && myIsNewSessionOpen);
}

// --- anchored cumulative VWAP and standard deviation (reset at myIsNewPeriod) ---
const myPV = mult(mySrc, volume);
const myPV2 = mult(mult(mySrc, mySrc), volume);

const mySumV = for_every(volume, myIsNewPeriod, (_v, _reset, _prev, _i) => (_i === 0 || _reset) ? _v : (_prev || 0) + _v);
const mySumPV = for_every(myPV, myIsNewPeriod, (_pv, _reset, _prev, _i) => (_i === 0 || _reset) ? _pv : (_prev || 0) + _pv);
const mySumPV2 = for_every(myPV2, myIsNewPeriod, (_pv2, _reset, _prev, _i) => (_i === 0 || _reset) ? _pv2 : (_prev || 0) + _pv2);

const myVwapValue = div(mySumPV, mySumV);
const myMeanSquare = div(mySumPV2, mySumV);
const myVariance = sub(myMeanSquare, mult(myVwapValue, myVwapValue));
const myStdev = for_every(myVariance, _v => Math.sqrt(Math.max(_v, 0)));

const myUpper1 = add(myVwapValue, myStdev);
const myLower1 = sub(myVwapValue, myStdev);
const myU1p025 = add(myUpper1, mult(myStdev, 0.25));
const myU1m025 = sub(myUpper1, mult(myStdev, 0.25));
const myL1p025 = add(myLower1, mult(myStdev, 0.25));
const myL1m025 = sub(myLower1, mult(myStdev, 0.25));
const myU1p05 = add(myUpper1, mult(myStdev, 0.5));
const myL1m05 = sub(myLower1, mult(myStdev, 0.5));

// --- shifted (previous candle) references, as used in the Pine logic ---
const myCloseP1 = shift(close, 1);
const myU1m025P1 = shift(myU1m025, 1);
const myU1p025P1 = shift(myU1p025, 1);
const myL1m025P1 = shift(myL1m025, 1);
const myL1p025P1 = shift(myL1p025, 1);
const myUpper1P1 = shift(myUpper1, 1);
const myU1p05P1 = shift(myU1p05, 1);
const myLower1P1 = shift(myLower1, 1);
const myL1m05P1 = shift(myL1m05, 1);

// --- dollar volume liquidity filter ---
// timeframe.multiplier (minutes per bar) is approximated from current.resolution;
// non-numeric resolutions (D/W/M) default to 1440 minutes (1 day).
const myMinuteMultiplier = isNaN(parseInt(current.resolution, 10)) ? 1440 : parseInt(current.resolution, 10);
const myMinDollarVolume = (100000 / 60) * myMinuteMultiplier;
const myDollarVolume = mult(volume, close);
const myVolumeCheck = for_every(myDollarVolume, _dv => _dv >= myMinDollarVolume);

// --- long / short zone & SVP proxy conditions ---
const myInUpperZone = for_every(myCloseP1, myU1m025P1, myU1p025P1, (_c, _lo, _hi) => _c >= _lo && _c <= _hi);
const myInLowerZone = for_every(myCloseP1, myL1m025P1, myL1p025P1, (_c, _lo, _hi) => _c >= _lo && _c <= _hi);

const myLongCond = for_every(
	myVwapValue, myInUpperZone, myVolumeCheck, mySvpSource, myU1m025P1, myU1p025P1, myUpper1P1, myU1p05P1,
	(_vwap, _inZone, _volOk, _svp, _um025, _up025, _upper, _up05) =>
		!isNaN(_vwap) && _vwap !== null && _inZone && _volOk &&
		_svp >= _um025 && _svp <= _up025 &&
		_svp >= _upper && _svp <= _up05);

const myShortCond = for_every(
	myVwapValue, myInLowerZone, myVolumeCheck, mySvpSource, myL1m025P1, myL1p025P1, myLower1P1, myL1m05P1,
	(_vwap, _inZone, _volOk, _svp, _lm025, _lp025, _lower, _lm05) =>
		!isNaN(_vwap) && _vwap !== null && _inZone && _volOk &&
		_svp >= _lm025 && _svp <= _lp025 &&
		_svp <= _lower && _svp >= _lm05);

const myLongCondP1 = shift(myLongCond, 1);
const myShortCondP1 = shift(myShortCond, 1);

const myLongSignal = for_every(myLongCond, myLongCondP1, (_c, _p) => _c && !_p);
const myShortSignal = for_every(myShortCond, myShortCondP1, (_c, _p) => _c && !_p);

// --- informational risk sizing (no real broker emulation available) ---
const myRiskDiff = for_every(myUpper1, myVwapValue, (_u, _v) => Math.abs(_u - _v));
const myMinTick = Math.pow(10, -(current.decimals || 2));
const mySlTicks = for_every(myRiskDiff, _rd => Math.ceil(_rd / myMinTick));
const myShares = for_every(myRiskDiff, _rd => _rd > 0 ? Math.floor(myRiskPerTrade / _rd) : 0);

// --- painting ---
const myVwapLine = paint(myVwapValue, { name: 'VWAP', color: '#2962FF', thickness: 2 });

fill(
	paint(myUpper1, { name: 'Upper1', color: '#9598a1', thickness: 1, style: 'dotted' }),
	paint(myLower1, { name: 'Lower1', color: '#9598a1', thickness: 1, style: 'dotted' }),
	'#9598a1',
	0.1);

const myLongMarks = for_every(myLongSignal, close, (_s, _c) => _s ? _c : null);
const myShortMarks = for_every(myShortSignal, close, (_s, _c) => _s ? _c : null);

paint(myLongMarks, { name: 'LongMark', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myShortMarks, { name: 'ShortMark', style: 'labels_above', color: '#EF5350', thickness: 3 });

register_signal(myLongSignal, 'Long Signal');
register_signal(myShortSignal, 'Short Signal');
register_signal(for_every(myShares, _s => _s > 0), 'Position Size Valid');