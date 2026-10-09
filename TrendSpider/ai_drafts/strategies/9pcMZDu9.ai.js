describe_indicator('Serhan3 WMA ADX Trailing Date Filter', 'price');

// ------------------------------------------------------------------
// INPUTS
// ------------------------------------------------------------------
const myInputsTab = input.tab('Settings');

const myWmaRow = myInputsTab.row();
const myFastLen = myWmaRow.number('Fast WMA', 11, { min: 1, max: 500 });
const mySlowLen = myWmaRow.number('Slow WMA', 28, { min: 1, max: 500 });

const myAdxRow = myInputsTab.row();
const myAdxLen = myAdxRow.number('ADX Period', 18, { min: 1, max: 100 });
const myAdxThreshold = myAdxRow.number('ADX Threshold', 24.0, { min: 0, max: 100, step: 0.1 });

const myTrailPercInput = myInputsTab.number('Trailing Stop Percent', 0.8, { min: 0.01, max: 100, step: 0.1 });

const myDateGroup = myInputsTab.group('Date Filter');
const myFromRow = myDateGroup.row();
const myFromMonth = myFromRow.number('From Month', 1, { min: 1, max: 12 });
const myFromDay = myFromRow.number('From Day', 1, { min: 1, max: 31 });
const myFromYear = myFromRow.number('From Year', 2025, { min: 2000, max: 2199 });

const myToRow = myDateGroup.row();
const myToMonth = myToRow.number('To Month', 12, { min: 1, max: 12 });
const myToDay = myToRow.number('To Day', 31, { min: 1, max: 31 });
const myToYear = myToRow.number('To Year', 2099, { min: 2000, max: 2199 });

// ------------------------------------------------------------------
// CALCULATIONS
// ------------------------------------------------------------------
const myFastWMA = wma(close, myFastLen);
const mySlowWMA = wma(close, mySlowLen);

const myAdxObject = indicators.adx(myAdxLen);
const myAdxVal = myAdxObject.adx;

const myTrailPerc = myTrailPercInput / 100;

// Date filter boundaries, computed as Unix timestamps (seconds).
// Date.UTC() is a static method (not the "new" operator), so it's allowed here.
const myStartTime = Date.UTC(myFromYear, myFromMonth - 1, myFromDay, 0, 0) / 1000;
const myEndTime = Date.UTC(myToYear, myToMonth - 1, myToDay, 23, 59) / 1000;

const myInDateRange = for_every(time, _t => _t >= myStartTime && _t <= myEndTime);

const myTrendFilter = for_every(myAdxVal, _adx => _adx > myAdxThreshold);

// Crossover / crossunder of fast vs slow WMA, computed via previous-bar comparison
const myCrossOver = for_every(myFastWMA, mySlowWMA, (_f, _s, _prev, _i) => {
	if (_i === 0) return false;
	return (_f > _s) && (myFastWMA[_i - 1] <= mySlowWMA[_i - 1]);
});

const myCrossUnder = for_every(myFastWMA, mySlowWMA, (_f, _s, _prev, _i) => {
	if (_i === 0) return false;
	return (_f < _s) && (myFastWMA[_i - 1] >= mySlowWMA[_i - 1]);
});

// Long / Short entry conditions, matching the Pine logic exactly
const myLongCondition = for_every(myCrossOver, close, myFastWMA, mySlowWMA, myTrendFilter, myInDateRange,
	(_co, _c, _f, _s, _tf, _dr) => _co && _c > _f && _c > _s && _tf && _dr);

const myShortCondition = for_every(myCrossUnder, close, myFastWMA, mySlowWMA, myTrendFilter, myInDateRange,
	(_cu, _c, _f, _s, _tf, _dr) => _cu && _c < _f && _c < _s && _tf && _dr);

// ------------------------------------------------------------------
// TRAILING STOP SIMULATION (position state machine, mirrors the
// strategy.exit(trail_points, trail_offset=0) behavior from Pine)
// ------------------------------------------------------------------
const myExitLongSignal = series_of(false);
const myExitShortSignal = series_of(false);

let myPositionDirection = 0; // 0 = flat, 1 = long, -1 = short
let myTrailStopPrice = null;
let myExtremePrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myClosePrice = close[myIndex];

	// Check exits first (trailing stop), using the current bar's close as proxy
	// for intrabar trailing (TrendSpider custom scripts have no intrabar access)
	if (myPositionDirection === 1) {
		myExtremePrice = Math.max(myExtremePrice, myClosePrice);
		myTrailStopPrice = myExtremePrice * (1 - myTrailPerc);
		if (myClosePrice <= myTrailStopPrice) {
			myExitLongSignal[myIndex] = true;
			myPositionDirection = 0;
			myTrailStopPrice = null;
			myExtremePrice = null;
		}
	}
	else if (myPositionDirection === -1) {
		myExtremePrice = Math.min(myExtremePrice, myClosePrice);
		myTrailStopPrice = myExtremePrice * (1 + myTrailPerc);
		if (myClosePrice >= myTrailStopPrice) {
			myExitShortSignal[myIndex] = true;
			myPositionDirection = 0;
			myTrailStopPrice = null;
			myExtremePrice = null;
		}
	}

	// Entries (only when flat, matching Pine's single-position behavior)
	if (myPositionDirection === 0) {
		if (myLongCondition[myIndex]) {
			myPositionDirection = 1;
			myExtremePrice = myClosePrice;
		}
		else if (myShortCondition[myIndex]) {
			myPositionDirection = -1;
			myExtremePrice = myClosePrice;
		}
	}
}

// ------------------------------------------------------------------
// PLOTS
// ------------------------------------------------------------------
paint(myFastWMA, { name: 'Fast WMA', color: '#2962FF', thickness: 2 });
paint(mySlowWMA, { name: 'Slow WMA', color: '#FF9800', thickness: 2 });

// ------------------------------------------------------------------
// SCANNER / ALERT / STRATEGY SIGNALS
// ------------------------------------------------------------------
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');
register_signal(myExitLongSignal, 'Exit Long Trailing Stop');
register_signal(myExitShortSignal, 'Exit Short Trailing Stop');