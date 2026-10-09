describe_indicator('Micro TL Final Balanced', 'price');

// NOTE: this is a best-effort port of a Pine Script v5 STRATEGY into an
// indicator. TrendSpider Custom JS indicators cannot execute broker-style
// order fills (strategy.entry/strategy.exit), so position tracking, fills
// and the "Active Stop Loss" line are approximated with a simple same-bar
// state machine (entry fills at signal bar close, exit triggers when
// high/low breaches stop or target). This will not reproduce the exact
// fill behavior of the Pine strategy engine (which usually fills on the
// next bar open), but reproduces the exact signal bars (long/short
// conditions) which are mapped to register_signal() for scanning/alerts.

const myPivotLen = input.number('Pivot Strength', 3, { min: 1, max: 50 });
const myRrRatio = input.number('Risk Reward', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myAtrMult = input.number('ATR Stop Multiplier', 1.5, { min: 0.1, max: 20, step: 0.1 });

const myHma = hullma(close, 20);
const myRsi = rsi(close, 14);
const myAtr = atr(high, low, close, 14);

// Pine: ta.pivothigh(pivotLen, 1) -> left = pivotLen, right = 1
const myPh = pivot_high(high, myPivotLen, 1);
const myPl = pivot_low(low, myPivotLen, 1);

const myN = close.length;

const myResPrice = series_of(null);
const mySupPrice = series_of(null);
const myLongCondition = series_of(false);
const myShortCondition = series_of(false);
const myCurrentSL = series_of(null);

let myPh1 = null, myPh2 = null, myPh1Idx = null, myPh2Idx = null;
let myPl1 = null, myPl2 = null, myPl1Idx = null, myPl2Idx = null;

let myPositionSize = 0;
let myEntryPrice = null;
let mySL = null;
let myTarget = null;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	if (myPh[myIndex] != null) {
		myPh2 = myPh1;
		myPh2Idx = myPh1Idx;
		myPh1 = myPh[myIndex];
		myPh1Idx = myIndex - 1;
	}

	if (myPl[myIndex] != null) {
		myPl2 = myPl1;
		myPl2Idx = myPl1Idx;
		myPl1 = myPl[myIndex];
		myPl1Idx = myIndex - 1;
	}

	if (myPh1 != null && myPh2 != null && myPh1Idx !== myPh2Idx) {
		myResPrice[myIndex] = myPh1 + ((myPh1 - myPh2) / (myPh1Idx - myPh2Idx)) * (myIndex - myPh1Idx);
	}

	if (myPl1 != null && myPl2 != null && myPl1Idx !== myPl2Idx) {
		mySupPrice[myIndex] = myPl1 + ((myPl1 - myPl2) / (myPl1Idx - myPl2Idx)) * (myIndex - myPl1Idx);
	}

	let myCrossOverRes = false;
	let myCrossUnderSup = false;

	if (myIndex > 0 && myResPrice[myIndex] != null && myResPrice[myIndex - 1] != null) {
		myCrossOverRes = close[myIndex] > myResPrice[myIndex] && close[myIndex - 1] <= myResPrice[myIndex - 1];
	}

	if (myIndex > 0 && mySupPrice[myIndex] != null && mySupPrice[myIndex - 1] != null) {
		myCrossUnderSup = close[myIndex] < mySupPrice[myIndex] && close[myIndex - 1] >= mySupPrice[myIndex - 1];
	}

	const myLongCond = myCrossOverRes && close[myIndex] > myHma[myIndex] && myRsi[myIndex] < 70;
	const myShortCond = myCrossUnderSup && close[myIndex] < myHma[myIndex] && myRsi[myIndex] > 30;

	myLongCondition[myIndex] = myLongCond;
	myShortCondition[myIndex] = myShortCond;

	// approximate position/SL state machine (see note at top)
	if (myPositionSize === 0 && !myLongCond && !myShortCond) {
		mySL = null;
	}

	if (myLongCond && myPositionSize === 0) {
		mySL = close[myIndex] - (myAtr[myIndex] * myAtrMult);
		myEntryPrice = close[myIndex];
		myTarget = myEntryPrice + ((myEntryPrice - mySL) * myRrRatio);
		myPositionSize = 1;
	}
	else if (myShortCond && myPositionSize === 0) {
		mySL = close[myIndex] + (myAtr[myIndex] * myAtrMult);
		myEntryPrice = close[myIndex];
		myTarget = myEntryPrice - ((mySL - myEntryPrice) * myRrRatio);
		myPositionSize = -1;
	}
	else if (myPositionSize === 1) {
		if (low[myIndex] <= mySL || high[myIndex] >= myTarget) {
			myPositionSize = 0;
		}
	}
	else if (myPositionSize === -1) {
		if (high[myIndex] >= mySL || low[myIndex] <= myTarget) {
			myPositionSize = 0;
		}
	}

	myCurrentSL[myIndex] = myPositionSize !== 0 ? mySL : null;
}

paint(myHma, { name: 'HMA Trend', color: '#9b59b6', thickness: 1 });
paint(myResPrice, { name: 'Resistance Line', color: '#e74c3c', style: 'line' });
paint(mySupPrice, { name: 'Support Line', color: '#2ecc71', style: 'line' });
paint(myCurrentSL, { name: 'Active Stop Loss', color: '#e67e22', thickness: 2, style: 'line' });

register_signal(myLongCondition, 'Long Condition');
register_signal(myShortCondition, 'Short Condition');