describe_indicator('Earnings Fundamentals Overlay', 'price');

// ---------------- Inputs ----------------
const myShowEps = input.boolean('EPS actual / estimate / surprise', true);
const myShowRev = input.boolean('Revenue + QoQ + YoY', true);
const myShowMargins = input.boolean('Gross / Pretax / Net margin', true);
const myLabelBelow = input.boolean('Place labels below bars', true);

// ---------------- Fetch earnings & fundamentals ----------------
// NOTE: TrendSpider has no "FQ financial series" plot engine like Pine. We fetch
// earnings records (actual/estimate) via request.earnings(), and quarterly
// fundamentals via request.fundamental(). The metric names 'gross_margin',
// 'operating_margin' and 'net_margin' are NOT valid in the fundamentals
// catalog. We also found that 'operating_income' AND 'ebit' are NOT valid
// metric names either (both threw "unknown_metric"). We now use
// 'pretax_income' as the closest available proxy for operating profitability,
// along with 'revenue', 'gross_profit' and 'net_income', and compute the
// margins ourselves as (metric / revenue) * 100.
const myQuarters = 24;
const [myEarningsData, myFundamentalData] = await Promise.all([
	request.earnings(current.ticker),
	request.fundamental(current.ticker, ['revenue', 'gross_profit', 'pretax_income', 'net_income'], myQuarters)
]);

assert(!myEarningsData.error, 'Error fetching earnings: ' + myEarningsData.error);
assert(!myFundamentalData.error, 'Error fetching fundamentals: ' + myFundamentalData.error);

// Keep only reported (non-future) earnings events, oldest first
const myEarningsReported = (myEarningsData || [])
	.filter(_e => !_e.isFuture && _e.eps != null)
	.sort((_a, _b) => _a.timestamp - _b.timestamp);

const myEarningsTimestamps = myEarningsReported.map(_e => _e.timestamp);
const myEpsActualValues = myEarningsReported.map(_e => _e.eps);
const myEpsEstimateValues = myEarningsReported.map(_e => (_e.eps_est == null ? null : _e.eps_est));

// Revenue series (quarterly, oldest first) used for QoQ/YoY
const myRevenueRecords = (myFundamentalData.revenue || []).slice().reverse();
const myRevenueTimestamps = myRevenueRecords.map(_r => _r.reportdate);
const myRevenueValues = myRevenueRecords.map(_r => _r.value);

const myGrossProfitRecords = (myFundamentalData.gross_profit || []).slice().reverse();
const myPretaxIncomeRecords = (myFundamentalData.pretax_income || []).slice().reverse();
const myNetIncomeRecords = (myFundamentalData.net_income || []).slice().reverse();

function myFindFundamentalForTimestamp(_records, _timestamp) {
	// Finds the most recent fundamental record at or before a given timestamp
	let myResult = null;
	for (let myIndex = 0; myIndex < _records.length; myIndex += 1) {
		if (_records[myIndex].reportdate <= _timestamp) {
			myResult = _records[myIndex].value;
		}
	}
	return myResult;
}

// ---------------- Formatting helpers ----------------
function myFormatBillions(_value) {
	if (_value == null || isNaN(_value)) return 'n/a';
	const myAbs = Math.abs(_value);
	if (myAbs >= 1e9) return (_value / 1e9).toFixed(2) + 'B';
	return (_value / 1e6).toFixed(1) + 'M';
}

function myFormatPercent(_value) {
	if (_value == null || isNaN(_value)) return 'n/a';
	return _value.toFixed(1) + '%';
}

function myFormatChange(_cur, _prev) {
	if (_cur == null || _prev == null || _prev === 0) return 'n/a';
	const myChangePercent = (_cur / _prev - 1) * 100;
	return (myChangePercent >= 0 ? '+' : '') + myChangePercent.toFixed(1) + '%';
}

// ---------------- Build per-earnings-event label text ----------------
const myLabelTexts = [];
const mySurpriseValues = [];

for (let myEventIndex = 0; myEventIndex < myEarningsReported.length; myEventIndex += 1) {
	const myEventTimestamp = myEarningsTimestamps[myEventIndex];
	const myEpsActual = myEpsActualValues[myEventIndex];
	const myEpsEstimate = myEpsEstimateValues[myEventIndex];

	const mySurprise = (myEpsActual == null || myEpsEstimate == null || myEpsEstimate === 0)
		? null
		: (myEpsActual / myEpsEstimate - 1) * 100;
	mySurpriseValues.push(mySurprise);

	// Revenue history up to and including this earnings event's quarter
	const myRevenueUpToIndex = myRevenueTimestamps.filter(_t => _t <= myEventTimestamp).length;
	const myRevenueCurrent = myRevenueUpToIndex >= 1 ? myRevenueValues[myRevenueUpToIndex - 1] : null;
	const myRevenuePrev = myRevenueUpToIndex >= 2 ? myRevenueValues[myRevenueUpToIndex - 2] : null;
	const myRevenueYoY = myRevenueUpToIndex >= 5 ? myRevenueValues[myRevenueUpToIndex - 5] : null;

	const myGrossProfit = myFindFundamentalForTimestamp(myGrossProfitRecords, myEventTimestamp);
	const myPretaxIncome = myFindFundamentalForTimestamp(myPretaxIncomeRecords, myEventTimestamp);
	const myNetIncome = myFindFundamentalForTimestamp(myNetIncomeRecords, myEventTimestamp);

	// Margins computed manually as (metric / revenue) * 100
	const myGrossMargin = (myGrossProfit == null || myRevenueCurrent == null || myRevenueCurrent === 0)
		? null : (myGrossProfit / myRevenueCurrent) * 100;
	const myPretaxMargin = (myPretaxIncome == null || myRevenueCurrent == null || myRevenueCurrent === 0)
		? null : (myPretaxIncome / myRevenueCurrent) * 100;
	const myNetMargin = (myNetIncome == null || myRevenueCurrent == null || myRevenueCurrent === 0)
		? null : (myNetIncome / myRevenueCurrent) * 100;

	let myText = '';
	if (myShowEps) {
		const myBeatText = mySurprise == null ? '' : ('  (' + (mySurprise >= 0 ? '+' : '') + mySurprise.toFixed(1) + '%)');
		myText += 'EPS ' + (myEpsActual == null ? 'n/a' : myEpsActual.toFixed(2)) + ' vs ' + (myEpsEstimate == null ? 'n/a' : myEpsEstimate.toFixed(2)) + myBeatText;
	}
	if (myShowRev) {
		myText += (myText === '' ? '' : '\n') + 'Rev ' + myFormatBillions(myRevenueCurrent) + '  QoQ ' + myFormatChange(myRevenueCurrent, myRevenuePrev) + '  YoY ' + myFormatChange(myRevenueCurrent, myRevenueYoY);
	}
	if (myShowMargins) {
		myText += (myText === '' ? '' : '\n') + 'GM ' + myFormatPercent(myGrossMargin) + '  PM ' + myFormatPercent(myPretaxMargin) + '  NM ' + myFormatPercent(myNetMargin);
	}
	myLabelTexts.push(myText);
}

// ---------------- Land earnings events onto chart candles ----------------
// 'le' lands each earnings timestamp onto the first candle timestamp <= it,
// mimicking "the bar on which the actual earnings value first appears".
const myEarnBarLanded = land_points_onto_series(myEarningsTimestamps, series_of(1).map((_v, _i) => _i), time, 'le');
const mySurpriseLanded = land_points_onto_series(myEarningsTimestamps, mySurpriseValues, time, 'le');

// Anchor series for the label (low or high of the bar), hidden line used only
// as an attachment point for paint_label_at_line
const myAnchorSeries = for_every(myEarnBarLanded, low, high, (_eventIdx, _low, _high) => {
	if (_eventIdx == null) return null;
	return myLabelBelow ? _low : _high;
});

const myAnchorLinePainted = paint(myAnchorSeries, { style: 'dotted', color: 'gray', thickness: 1, name: 'EarningsAnchor' });

// Attach a text label to every landed earnings event
const myAnchorPoints = indexed_points_of(myEarnBarLanded);
for (const myPoint of myAnchorPoints) {
	const myEventIndex = Math.round(myPoint.value);
	const myLabelColor = mySurpriseValues[myEventIndex] == null
		? 'gray'
		: (mySurpriseValues[myEventIndex] >= 0 ? 'teal' : 'red');

	paint_label_at_line(myAnchorLinePainted, myPoint.candleIndex, myLabelTexts[myEventIndex], {
		color: 'white',
		background_color: myLabelColor,
		vertical_align: myLabelBelow ? 'bottom' : 'top'
	});
}

// ---------------- Scanning / strategy signals ----------------
// Earnings beat signal: true on the bar where actual EPS beats estimate
const myEarningsBeatSignal = for_every(myEarnBarLanded, mySurpriseLanded, (_eventIdx, _surprise) => _eventIdx != null && _surprise != null && _surprise >= 0);
register_signal(myEarningsBeatSignal, 'Earnings Beat');

// Earnings miss signal: true on the bar where actual EPS misses estimate
const myEarningsMissSignal = for_every(myEarnBarLanded, mySurpriseLanded, (_eventIdx, _surprise) => _eventIdx != null && _surprise != null && _surprise < 0);
register_signal(myEarningsMissSignal, 'Earnings Miss');

// Generic "earnings report bar" signal (equivalent of Pine's earnBar flag)
const myEarningsBarSignal = for_every(myEarnBarLanded, _eventIdx => _eventIdx != null);
register_signal(myEarningsBarSignal, 'Earnings Report Bar');