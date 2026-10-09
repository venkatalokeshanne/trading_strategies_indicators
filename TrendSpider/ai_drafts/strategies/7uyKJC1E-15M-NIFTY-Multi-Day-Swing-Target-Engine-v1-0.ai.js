describe_indicator('NIFTY 5M Multi Day Swing Target Engine v14', 'price');

// ----------------------------------------------------------------
// This is a conversion of a Pine Script strategy into an indicator.
// Strategy order routing (fills, same-bar entry+exit interaction)
// is approximated: we check Target/SL hit on the SAME bar an entry
// happens, in bar order (high/low touch), since there is no real
// broker simulation engine available here. See flagged notes.
// ----------------------------------------------------------------

const myBodyThreshold = input.number('Body Threshold Pct', 70, { min: 10, max: 100 });
const myTpAtrMult = input.number('TP ATR Mult', 3, { min: 0.1, max: 20 });
const mySlLookback = input.number('SL Lookback', 3, { min: 1, max: 50 });

// ---- candle anatomy ----
const myAtr = atr(high, low, close, 14);
const myCandleRange = sub(high, low);
const myCandleBody = for_every(close, open, (_c, _o) => Math.abs(_c - _o));
const myBodyPercentage = for_every(myCandleRange, myCandleBody, (_r, _b) => _r > 0 ? (_b / _r) * 100 : 0);
const myIsGreen = for_every(close, open, (_c, _o) => _c > _o);
const myIsRed = for_every(close, open, (_c, _o) => _c < _o);

// ---- entry window: 09:20 to 15:00, Monday to Friday ----
const myInEntryWindow = for_every(time, _t => {
	const myTimeInfo = time_of(_t);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myIsWeekday = myTimeInfo.dayOfWeek >= 1 && myTimeInfo.dayOfWeek <= 5;
	return myIsWeekday && myMinutesOfDay >= 560 && myMinutesOfDay < 900;
});

// ---- trailing SL support math (precomputed outside the loop) ----
const myLowestLow = lowest(low, mySlLookback);
const myHighestHigh = highest(high, mySlLookback);

// ---- state machine (replicates strategy position/bracket logic) ----
const myLongEntryFlag = series_of(false);
const myShortEntryFlag = series_of(false);
const myLongExitFlag = series_of(false);
const myShortExitFlag = series_of(false);
const mySwingTargetSeries = series_of(null);
const myTrailingSlSeries = series_of(null);
const myPositionSeries = series_of(0);

let myPosition = 0;
let mySwingTarget = null;
let myTrailingSl = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myLongSignal = myInEntryWindow[myIndex] && myIsGreen[myIndex] && myBodyPercentage[myIndex] >= myBodyThreshold;
	const myShortSignal = myInEntryWindow[myIndex] && myIsRed[myIndex] && myBodyPercentage[myIndex] >= myBodyThreshold;

	if (myLongSignal && myPosition <= 0) {
		myPosition = 1;
		mySwingTarget = close[myIndex] + (myAtr[myIndex] * myTpAtrMult);
		myTrailingSl = myIndex > 0 ? low[myIndex - 1] : low[myIndex];
		myLongEntryFlag[myIndex] = true;
	}
	if (myShortSignal && myPosition >= 0) {
		myPosition = -1;
		mySwingTarget = close[myIndex] - (myAtr[myIndex] * myTpAtrMult);
		myTrailingSl = myIndex > 0 ? high[myIndex - 1] : high[myIndex];
		myShortEntryFlag[myIndex] = true;
	}

	if (myPosition > 0) {
		myTrailingSl = Math.max(myTrailingSl, myLowestLow[myIndex]);
	}
	if (myPosition < 0) {
		myTrailingSl = Math.min(myTrailingSl, myHighestHigh[myIndex]);
	}

	if (myPosition > 0 && (high[myIndex] >= mySwingTarget || low[myIndex] <= myTrailingSl)) {
		myPosition = 0;
		myLongExitFlag[myIndex] = true;
	}
	if (myPosition < 0 && (low[myIndex] <= mySwingTarget || high[myIndex] >= myTrailingSl)) {
		myPosition = 0;
		myShortExitFlag[myIndex] = true;
	}

	if (myPosition === 0) {
		mySwingTarget = null;
		myTrailingSl = null;
	}

	mySwingTargetSeries[myIndex] = mySwingTarget;
	myTrailingSlSeries[myIndex] = myTrailingSl;
	myPositionSeries[myIndex] = myPosition;
}

// ---- painting ----
paint(mySwingTargetSeries, { name: 'SwingTarget', color: '#2ca599', style: 'ladder', thickness: 2 });
paint(myTrailingSlSeries, { name: 'TrailingSL', color: '#ee5451', style: 'ladder', thickness: 2 });

const myLongEntryMarks = for_every(myLongEntryFlag, low, (_f, _l) => _f ? _l : null);
const myShortEntryMarks = for_every(myShortEntryFlag, high, (_f, _h) => _f ? _h : null);
const myLongExitMarks = for_every(myLongExitFlag, low, (_f, _l) => _f ? _l : null);
const myShortExitMarks = for_every(myShortExitFlag, high, (_f, _h) => _f ? _h : null);

paint(myLongEntryMarks, { name: 'SwingCEEntry', color: '#26A69A', style: 'labels_below' });
paint(myShortEntryMarks, { name: 'SwingPEEntry', color: '#EF5350', style: 'labels_above' });
paint(myLongExitMarks, { name: 'CEExit', color: '#26A69A', style: 'labels_above' });
paint(myShortExitMarks, { name: 'PEExit', color: '#EF5350', style: 'labels_below' });

// ---- signals for scanner/alerts/strategy tester ----
register_signal(myLongEntryFlag, 'Swing CE Entry');
register_signal(myShortEntryFlag, 'Swing PE Entry');
register_signal(myLongExitFlag, 'CE Exit');
register_signal(myShortExitFlag, 'PE Exit');
register_signal(for_every(myPositionSeries, _p => _p > 0), 'Long Position Active');
register_signal(for_every(myPositionSeries, _p => _p < 0), 'Short Position Active');
register_signal(for_every(myPositionSeries, _p => _p === 0), 'Flat');