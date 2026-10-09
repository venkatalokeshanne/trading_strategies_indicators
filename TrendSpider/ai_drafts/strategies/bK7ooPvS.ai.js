describe_indicator('Supertrend ATR Signals', 'price');
// NOTE: This is translated as an INDICATOR, not a backtestable
// strategy. TrendSpider Custom JS indicators cannot place orders,
// manage position sizing, leverage or trailing stop exits like a
// Pine `strategy()` script does. This code reproduces the exact
// Supertrend trend/signal math and exposes Buy/Sell as signals,
// but the money-management portion (equity, risk%, leverage,
// trailing stop) is not simulated.

const myAtrTab = input.tab('ATR / Supertrend');
const myPeriods = myAtrTab.number('ATR Period', 10, { min: 1, max: 200 });
const myMultiplier = myAtrTab.number('ATR Multiplier', 3.0, { min: 0.1, max: 20, step: 0.1 });
const myUseBuiltinAtr = myAtrTab.boolean('Use builtin ATR', true);

const myFilterTab = input.tab('Consolidation Filter');
const myAtrFilterLength = myFilterTab.number('ATR Length for Filter', 14, { min: 1, max: 200 });
const myAtrFilterMult = myFilterTab.number('ATR Multiplier for Filter', 0.5, { min: 0.01, max: 10, step: 0.01 });
const mySmaAtrLength = myFilterTab.number('SMA ATR Length', 20, { min: 1, max: 200 });

// True Range (manual, needed for the "custom" ATR option)
const myPrevClose = shift(close, 1);
const myTrueRange = for_every(high, low, close, myPrevClose, (_h, _l, _c, _pc) => {
	if (_pc === null || _pc === undefined) {
		return _h - _l;
	}
	return Math.max(_h - _l, Math.abs(_h - _pc), Math.abs(_l - _pc));
});

const myAtrBuiltin = atr(high, low, close, myPeriods);
const myAtrCustom = sma(myTrueRange, myPeriods);
const myAtrVal = myUseBuiltinAtr ? myAtrBuiltin : myAtrCustom;
const mySrc = hl2;

// ATR consolidation filter
const myAtrForFilter = atr(high, low, close, myAtrFilterLength);
const mySmaAtrForFilter = sma(myAtrForFilter, mySmaAtrLength);
const myAtrForTrend = atr(high, low, close, myPeriods);
const myAtrFilter = for_every(myAtrForTrend, mySmaAtrForFilter, (_a, _s) => _a < _s * myAtrFilterMult);

// Supertrend-style recursive up/dn/trend calculation.
// Computed in a plain loop (not calling any indicator function inside
// the loop) because up/dn/trend are mutually recursive and for_every's
// callback was returning a "previous value" that could be null on the
// very first iterations where source series still contain null (NaN
// warm-up period of ATR/SMA), which crashed when read as `.trend`.
const myUpArr = series_of(null);
const myDnArr = series_of(null);
const myTrendArr = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const mySrcVal = mySrc[myIndex];
	const myAtrHere = myAtrVal[myIndex];
	const myCloseHere = close[myIndex];
	const myPrevCloseHere = myPrevClose[myIndex];

	let myUpCandidate = null;
	let myDnCandidate = null;

	if (mySrcVal !== null && mySrcVal !== undefined && myAtrHere !== null && myAtrHere !== undefined && !isNaN(myAtrHere)) {
		myUpCandidate = mySrcVal - (myMultiplier * myAtrHere);
		myDnCandidate = mySrcVal + (myMultiplier * myAtrHere);
	}

	const myHasPrev = myIndex > 0 && myUpArr[myIndex - 1] !== null && myDnArr[myIndex - 1] !== null && myTrendArr[myIndex - 1] !== null;

	const myUp1 = myHasPrev ? myUpArr[myIndex - 1] : myUpCandidate;
	const myDn1 = myHasPrev ? myDnArr[myIndex - 1] : myDnCandidate;
	const myPrevTrend = myHasPrev ? myTrendArr[myIndex - 1] : 1;

	let myNewUp = myUpCandidate;
	let myNewDn = myDnCandidate;

	if (myUpCandidate === null || myDnCandidate === null) {
		myUpArr[myIndex] = null;
		myDnArr[myIndex] = null;
		myTrendArr[myIndex] = null;
		continue;
	}

	if (myPrevCloseHere !== null && myPrevCloseHere !== undefined && myUp1 !== null && myPrevCloseHere > myUp1) {
		myNewUp = Math.max(myUpCandidate, myUp1);
	}
	if (myPrevCloseHere !== null && myPrevCloseHere !== undefined && myDn1 !== null && myPrevCloseHere < myDn1) {
		myNewDn = Math.min(myDnCandidate, myDn1);
	}

	let myNewTrend = myPrevTrend;
	if (myPrevTrend === -1 && myCloseHere > myDn1) {
		myNewTrend = 1;
	}
	else if (myPrevTrend === 1 && myCloseHere < myUp1) {
		myNewTrend = -1;
	}

	myUpArr[myIndex] = myNewUp;
	myDnArr[myIndex] = myNewDn;
	myTrendArr[myIndex] = myNewTrend;
}

const myPrevTrendSeries = shift(myTrendArr, 1);
const myBuySignal = for_every(myTrendArr, myPrevTrendSeries, (_t, _pt) => _t === 1 && _pt === -1);
const mySellSignal = for_every(myTrendArr, myPrevTrendSeries, (_t, _pt) => _t === -1 && _pt === 1);

const myCanTrade = for_every(myAtrFilter, _f => !_f);
const myFinalBuySignal = for_every(myBuySignal, myCanTrade, (_b, _ct) => _b && _ct);
const myFinalSellSignal = for_every(mySellSignal, myCanTrade, (_s, _ct) => _s && _ct);

const myUpLine = for_every(myTrendArr, myUpArr, (_t, _u) => _t === 1 ? _u : null);
const myDnLine = for_every(myTrendArr, myDnArr, (_t, _d) => _t === -1 ? _d : null);

paint(myUpLine, { name: 'UpTrend', color: '#26A69A', thickness: 2, style: 'line' });
paint(myDnLine, { name: 'DownTrend', color: '#EF5350', thickness: 2, style: 'line' });

const myBuyLabels = for_every(myFinalBuySignal, _b => _b ? constants.icons.triangle_up : null);
const mySellLabels = for_every(myFinalSellSignal, _s => _s ? constants.icons.triangle_down : null);

paint(myBuyLabels, { name: 'BuySignal', style: 'labels_below', color: '#26A69A' });
paint(mySellLabels, { name: 'SellSignal', style: 'labels_above', color: '#EF5350' });

register_signal(myFinalBuySignal, 'Buy Signal');
register_signal(myFinalSellSignal, 'Sell Signal');
register_signal(myAtrFilter, 'Consolidation Filter Active');