// EXPERIMENTAL CONVERSION: this indicator reproduces the Pine Script
// SIGNAL LOGIC (trend/FVG/imbalance/breakout conditions) as closely as
// the TrendSpider Custom JS API allows. Actual broker-style order
// management (stop entries, breakeven, trailing stops) cannot be
// expressed in an indicator - only signals/markers are provided here.
// Use these signals in the Strategy Tester / Scanner / Alerts modules
// to approximate the original strategy behavior.
describe_indicator('Ema Cross Plus Imbalance Signals', 'price');

const emaTab = input.tab('EMA Settings');
const myFastLen = emaTab.number('Fast EMA Length', 9, { min: 1, max: 200 });
const mySlowLen = emaTab.number('Slow EMA Length', 21, { min: 1, max: 200 });

const fvgTab = input.tab('FVG Settings');
const myMinGapTicks = fvgTab.number('Min FVG Tol in Ticks', 2, { min: 0, max: 1000 });

const timeTab = input.tab('Session Settings');
const myStartTime = timeTab.number('Trading Window Start (HHMM)', 730, { min: 0, max: 2359 });
const myEndTime = timeTab.number('Trading Window End (HHMM)', 1000, { min: 0, max: 2359 });

// Pine's syminfo.mintick is not exposed by the Custom JS API. We
// approximate tick size using current.decimals (10 ^ -decimals).
const myTickSize = Math.pow(10, -current.decimals);

const myAvgVol = sma(volume, 20);
const myEmaFast = ema(close, myFastLen);
const myEmaSlow = ema(close, mySlowLen);

// shifted (lagged) series equivalent to Pine's [1], [2], [3] indexing
const myHigh1 = shift(high, 1);
const myHigh2 = shift(high, 2);
const myHigh3 = shift(high, 3);
const myLow1 = shift(low, 1);
const myLow2 = shift(low, 2);
const myLow3 = shift(low, 3);
const myOpen1 = shift(open, 1);
const myClose1 = shift(close, 1);
const myVolume1 = shift(volume, 1);
const myAvgVol1 = shift(myAvgVol, 1);
const myEmaFast1 = shift(myEmaFast, 1);
const myEmaSlow1 = shift(myEmaSlow, 1);

// NOTE: time_of() uses the exchange timezone, not an arbitrary
// UTC offset like Pine's "UTC-6". This is an approximation of the
// original session filter.
const myTimeNowSeries = time.map(_t => {
	const myParsed = time_of(_t);
	return myParsed.hours * 100 + myParsed.minutes;
});

const myResult = for_every(
	myHigh1, myHigh2, myHigh3,
	myLow1, myLow2, myLow3,
	myOpen1, myClose1,
	myVolume1, myAvgVol1,
	myEmaFast1, myEmaSlow1,
	close,
	(_h1, _h2, _h3, _l1, _l2, _l3, _o1, _c1, _v1, _av1, _ef1, _es1, _c, _prev, _idx) => {
		const myRangeCandle = _h1 - _l1;
		const myBodyLength = Math.abs(_c1 - _o1);
		const myRatio = myRangeCandle !== 0 ? myBodyLength / myRangeCandle : 0;

		const myTrendUp = _ef1 > _es1 && _c1 > _ef1;
		const myTrendDown = _ef1 < _es1 && _c1 < _ef1;

		const myBullFvg = _l1 > _h3;
		const myBearFvg = _h1 < _l3;

		let myBullGap = _l1 - _h3;
		if (myBullGap < 0) myBullGap = 0;

		let myBearGap = _l3 - _h1;
		if (myBearGap < 0) myBearGap = 0;

		const myBullishImb = _c1 > _o1 && myRatio > 0.65 && _v1 > _av1;
		const myBearishImb = _c1 < _o1 && myRatio > 0.65 && _v1 > _av1;

		const myBrokeHigh = _h1 > _h2;
		const myBrokeLow = _l1 < _l2;

		const myTimeNow = myTimeNowSeries[_idx];
		const myTradTime = myTimeNow >= myStartTime && myTimeNow <= myEndTime;

		const myOrderLong = myTrendUp && myBullFvg && (myBullGap / myTickSize) >= myMinGapTicks && myBullishImb && myBrokeHigh && myTradTime;
		const myOrderShort = myTrendDown && myBearFvg && (myBearGap / myTickSize) >= myMinGapTicks && myBearishImb && myBrokeLow && myTradTime;

		return { long: myOrderLong, short: myOrderShort };
	}
);

const myLongSignal = myResult.map(_r => _r ? _r.long : false);
const myShortSignal = myResult.map(_r => _r ? _r.short : false);

register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myShortSignal, 'Short Entry Signal');

const myLongMarks = for_every(myLongSignal, low, (_s, _l) => _s ? _l : null);
const myShortMarks = for_every(myShortSignal, high, (_s, _h) => _s ? _h : null);

paint(myLongMarks, { name: 'Long Signal', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myShortMarks, { name: 'Short Signal', style: 'labels_above', color: '#EF5350', thickness: 3 });

paint(myEmaFast, { name: 'Ema Fast', color: '#2962FF', thickness: 1 });
paint(myEmaSlow, { name: 'Ema Slow', color: '#FF6D00', thickness: 1 });