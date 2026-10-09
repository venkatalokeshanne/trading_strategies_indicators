// NOTE: This is a best-effort re-implementation of a TradingView Pine
// Script "strategy" inside the Custom JS API, which has NO order engine
// (no strategy.entry/exit/close_all, no intrabar stop/limit fills).
// This script approximates fills: entries/EOW immediate closes are
// filled at the triggering bar's open/close, momentum-exit is filled
// at the next bar's open. Intrabar stop-loss / take-profit touches are
// NOT modeled (we only know close-of-day values here), so results will
// diverge from the real Pine strategy whenever price pierces the
// stop/target intrabar without closing beyond it. Assumes a Daily chart
// (one bar = one regular session), since "first/last bar of session"
// concepts collapse to "the bar itself" on Daily resolution.
describe_indicator('One Percent A Week Adaptive (TQQQ)', 'price');

const myMonPercentInput = input.number('Monday Percent Threshold', 2, { min: 1, max: 3, step: 0.1 });
const myTuesPercentInput = input.number('Tuesday Percent Threshold', 3, { min: 1, max: 5, step: 0.1 });

const myCandleCount = close.length;

const myEntryLine = series_of(null);
const mySlLine = series_of(null);
const myPtLine = series_of(null);
const myBuySignalArr = series_of(false);
const mySellSignalArr = series_of(false);
const myEowCloseSignalArr = series_of(false);

let myInPosition = false;
let myEntryPrice = null;
let myPt = null;
let mySl = null;
let myEowClose = false;
let myMonProf = null;
let myPendingEntry = false;
let myPendingExit = false;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myDow = time_of(time[myIndex]).dayOfWeek; // ISO: 1=Mon ... 7=Sun
	const myNextDow = (myIndex + 1 < myCandleCount) ? time_of(time[myIndex + 1]).dayOfWeek : null;

	let myEowCloseHappened = false;

	// Fill a pending entry (scheduled at prior EOW) at this bar's open
	if (myPendingEntry) {
		myInPosition = true;
		myEntryPrice = open[myIndex];
		myPt = null;
		mySl = null;
		myPendingEntry = false;
	}

	// Fill a pending momentum exit at this bar's open
	if (myPendingExit) {
		myInPosition = false;
		myEntryPrice = null;
		myPt = null;
		mySl = null;
		myPendingExit = false;
	}

	const myIsMonday = myDow === 1;
	const myIsTuesday = myDow === 2;

	// newMon: set initial bracket orders
	if (myIsMonday && myInPosition && myEntryPrice !== null && mySl === null) {
		myEowClose = true;
		mySl = myEntryPrice * 0.985;
		myPt = myEntryPrice * 1.07;
	}

	let myPlPct = null;
	if (myInPosition && myEntryPrice) {
		myPlPct = 100 * (close[myIndex] - myEntryPrice) / myEntryPrice;
	}

	// endMon: adjust target
	if (myIsMonday && myInPosition && myPlPct !== null) {
		myMonProf = myPlPct;
		if (myPlPct > 0.3) {
			myPt = myPt * 1.011;
		}
		else if (myPlPct <= 0) {
			myPt = myEntryPrice * 1.025;
		}
	}

	// endTue: loss of momentum exit, filled next bar open
	if (myIsTuesday && myInPosition && myMonProf !== null && myPlPct !== null
		&& myMonProf > myMonPercentInput && myPlPct < myTuesPercentInput) {
		myPendingExit = true;
	}

	// End of week logic: Friday, or last trading day before a gap to a later weekday
	const myIsLastDayOfWeek = (myDow === 5) || (myNextDow !== null && myNextDow < myDow);

	if (myIsLastDayOfWeek) {
		if (myEowClose && myInPosition) {
			myInPosition = false;
			myEntryPrice = null;
			myEowClose = false;
			myEowCloseHappened = true;
		}
		if (myNextDow === 1) {
			myPendingEntry = true;
			myPt = null;
			mySl = null;
		}
	}

	myEntryLine[myIndex] = myInPosition ? myEntryPrice : null;
	mySlLine[myIndex] = myInPosition ? mySl : null;
	myPtLine[myIndex] = myInPosition ? myPt : null;
	myBuySignalArr[myIndex] = myPendingEntry;
	mySellSignalArr[myIndex] = myPendingExit;
	myEowCloseSignalArr[myIndex] = myEowCloseHappened;
}

paint(myEntryLine, { name: 'EntryPrice', color: 'blue', style: 'line' });
paint(mySlLine, { name: 'HardStop', color: '#ff0000', style: 'dotted' });
paint(myPtLine, { name: 'ProfitTarget', color: '#00ff00', style: 'line' });

register_signal(myBuySignalArr, 'Scheduled Buy Entry');
register_signal(mySellSignalArr, 'Momentum Loss Exit Scheduled');
register_signal(myEowCloseSignalArr, 'End Of Week Close');