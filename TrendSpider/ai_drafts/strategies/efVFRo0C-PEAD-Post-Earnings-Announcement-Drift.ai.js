describe_indicator('PEAD Post Earnings Announcement Drift', 'price');

// NOTE: TrendSpider Custom JS indicators cannot run a Pine "strategy()"
// (no order management, equity, pyramiding, commissions). This script
// reproduces the SIGNAL logic (surprise%, reaction%, long/short signals,
// hold-period exit signal) and exposes them via register_signal() so they
// can be used in Scanners / Alerts / Strategy Tester. The actual trade
// simulation (entries/exits/equity) from the original strategy() block is
// not reproduced.

const myHoldBars = input.number('Holding period, bars', 60, { min: 1, max: 500 });
const myMinSurprisePct = input.number('Min EPS surprise %', 5.0, { min: -100, max: 1000, step: 0.5 });
const myMinReactionPct = input.number('Min price reaction %', 0.0, { min: -100, max: 100, step: 0.25 });
const myAllowShorts = input.boolean('Enable short PEAD', false);
const myReactionMode = input.select('Reaction confirmation', 'Next daily bar', ['Next daily bar', 'Earnings bar']);

// Fetch earnings history (actual + estimate) for the current ticker.
const myEarningsData = await request.earnings(current.ticker);
assert(!myEarningsData.error, 'Error fetching earnings: ' + myEarningsData.error);

// Build sparse surprise% source points (only for reported, non-future records
// with a usable estimate), sorted ascending by time (request.earnings returns
// most recent first).
const myReportRecords = myEarningsData
	.filter(_r => !_r.isFuture && _r.eps !== null && _r.eps !== undefined && _r.eps_est !== null && _r.eps_est !== undefined && Math.abs(_r.eps_est) > 0)
	.map(_r => ({
		timestamp: _r.timestamp,
		surprisePct: 100.0 * (_r.eps - _r.eps_est) / Math.abs(_r.eps_est)
	}))
	.sort((_a, _b) => _a.timestamp - _b.timestamp);

const mySourceTimestamps = myReportRecords.map(_r => _r.timestamp);
const mySourceValues = myReportRecords.map(_r => _r.surprisePct);

// Land each earnings surprise% onto the first candle at/after the report time.
// This is an approximation of Pine's intraday request.earnings() alignment,
// since Custom JS does not expose a per-bar earnings feed directly.
const mySurpriseLanded = mySourceTimestamps.length > 0
	? land_points_onto_series(mySourceTimestamps, mySourceValues, time, 'ge')
	: series_of(null);

const myHasReport = for_every(mySurpriseLanded, _s => _s !== null && _s !== undefined);

const mySurpriseDir = for_every(mySurpriseLanded, _s => {
	if (_s === null || _s === undefined) return 0;
	if (_s >= myMinSurprisePct) return 1;
	if (_s <= -myMinSurprisePct) return -1;
	return 0;
});

// Price reaction%, equivalent to Pine's 100*(close/close[1]-1)
const myBarReactionPct = roc(close, 1);

// Sequential state machine replicating the Pine "var" pending logic.
// This must run in a single top-level loop (no indicator calls inside it).
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const myExitSignal = series_of(false);

let myPendingDir = 0;
let myPendingBar = null;
let myPositionDir = 0; // 1 long, -1 short, 0 flat
let myEntryBarIndex = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	let myLong = false;
	let myShort = false;

	if (myReactionMode === 'Earnings bar') {
		myLong = mySurpriseDir[myIndex] === 1 && myBarReactionPct[myIndex] >= myMinReactionPct;
		myShort = myAllowShorts && mySurpriseDir[myIndex] === -1 && myBarReactionPct[myIndex] <= -myMinReactionPct;
	}

	if (myReactionMode === 'Next daily bar') {
		if (myPendingBar !== null && myIndex === myPendingBar + 1) {
			myLong = myPendingDir === 1 && myBarReactionPct[myIndex] >= myMinReactionPct;
			myShort = myAllowShorts && myPendingDir === -1 && myBarReactionPct[myIndex] <= -myMinReactionPct;
			myPendingDir = 0;
			myPendingBar = null;
		}

		if (myHasReport[myIndex]) {
			myPendingDir = mySurpriseDir[myIndex];
			myPendingBar = myIndex;
		}
	}

	myLongSignal[myIndex] = myLong;
	myShortSignal[myIndex] = myShort;

	// Simplified single-position simulation (no pyramiding), used only to
	// derive a hold-period exit signal; this is not a full strategy backtest.
	if (myPositionDir === 0 && myLong) {
		myPositionDir = 1;
		myEntryBarIndex = myIndex;
	}
	else if (myPositionDir === 0 && myShort) {
		myPositionDir = -1;
		myEntryBarIndex = myIndex;
	}
	else if (myPositionDir !== 0 && (myIndex - myEntryBarIndex) >= myHoldBars) {
		myExitSignal[myIndex] = true;
		myPositionDir = 0;
		myEntryBarIndex = null;
	}
}

const myReportMarks = for_every(myHasReport, _h => _h ? constants.icons.circle : null);
const myLongMarks = for_every(myLongSignal, _l => _l ? constants.icons.triangle_up : null);
const myShortMarks = for_every(myShortSignal, _s => _s ? constants.icons.triangle_down : null);

paint(myReportMarks, { name: 'Earnings Report Mark', style: 'labels_below', color: 'gray' });
paint(myLongMarks, { name: 'PEAD Long Mark', style: 'labels_below', color: 'lime' });
paint(myShortMarks, { name: 'PEAD Short Mark', style: 'labels_above', color: 'red' });

// Signal names must be unique across the whole indicator (paint() names and
// register_signal() names share the same namespace), so each register_signal
// name below has been made distinct from the paint() names above.
register_signal(myHasReport, 'Earnings Report Signal');
register_signal(myLongSignal, 'PEAD Long Signal');
register_signal(myShortSignal, 'PEAD Short Signal');
register_signal(myExitSignal, 'PEAD Hold Period Exit');