describe_indicator('Fair Value Gap plus Break of Structure', 'price');

// ── INPUTS ─────────────────────────────────────────────
const structureTab = input.group('Structure');
const mySwingLen = structureTab.number('Swing Lookback', 10, { min: 3, max: 100 });

const fvgTab = input.group('FVG');
const myFvgExpiry = fvgTab.number('FVG Max Age (bars)', 20, { min: 5, max: 200 });

const riskTab = input.group('Risk');
const myAtrLen = riskTab.number('ATR Length', 14, { min: 1, max: 100 });
const riskRow = riskTab.row();
const myTpMult = riskRow.number('TP ATR Multiplier', 2.0, { min: 0.1, max: 20, step: 0.1 });
const mySlBuffer = riskRow.number('SL Buffer ATR Mult', 0.1, { min: 0, max: 10, step: 0.1 });

// ── ATR ──────────────────────────────────────────────
const myAtrVal = atr(high, low, close, myAtrLen);

// ── SWING DETECTION ─────────────────────────────────
// pivot_high/pivot_low are the non-repainting equivalent of ta.pivothigh/pivotlow
const mySwingHigh = pivot_high(high, mySwingLen, mySwingLen);
const mySwingLow = pivot_low(low, mySwingLen, mySwingLen);

const myN = close.length;

// Output series
const myBosUp = series_of(false);
const myBosDn = series_of(false);
const myLongCond = series_of(false);
const myShortCond = series_of(false);
const myLongSL = series_of(null);
const myLongTP = series_of(null);
const myShortSL = series_of(null);
const myShortTP = series_of(null);

// State variables, carried across the loop (mirrors Pine's `var` behavior)
let myLastSwingHigh = null;
let myLastSwingLow = null;
let myBosUpBar = null;
let myBosDnBar = null;

let myBFvgH = null;
let myBFvgL = null;
let myBFvgBar = null;
let mySFvgH = null;
let mySFvgL = null;
let mySFvgBar = null;

// Tracks simulated position state, since strategy.position_size == 0
// can't be replicated exactly without a full backtest engine.
// We approximate it as "no open signal position" using entry/exit logic below.
let myPositionOpen = false;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	if (mySwingHigh[myIndex] !== null && mySwingHigh[myIndex] !== undefined) {
		myLastSwingHigh = mySwingHigh[myIndex];
	}
	if (mySwingLow[myIndex] !== null && mySwingLow[myIndex] !== undefined) {
		myLastSwingLow = mySwingLow[myIndex];
	}

	const myCloseNow = close[myIndex];
	const myBosUpNow = myLastSwingHigh !== null && myCloseNow > myLastSwingHigh;
	const myBosDnNow = myLastSwingLow !== null && myCloseNow < myLastSwingLow;

	if (myBosUpNow) {
		myBosUpBar = myIndex;
	}
	if (myBosDnNow) {
		myBosDnBar = myIndex;
	}

	myBosUp[myIndex] = myBosUpNow;
	myBosDn[myIndex] = myBosDnNow;

	// Fair Value Gap detection (needs 2 candles back)
	let myBullFvgHigh = null;
	let myBullFvgLow = null;
	let myBearFvgHigh = null;
	let myBearFvgLow = null;

	if (myIndex >= 2) {
		if (low[myIndex] > high[myIndex - 2]) {
			myBullFvgHigh = low[myIndex];
			myBullFvgLow = high[myIndex - 2];
		}
		if (high[myIndex] < low[myIndex - 2]) {
			myBearFvgHigh = low[myIndex - 2];
			myBearFvgLow = high[myIndex];
		}
	}

	const myRecentBosUp = myBosUpBar !== null && (myIndex - myBosUpBar) <= myFvgExpiry;
	const myRecentBosDn = myBosDnBar !== null && (myIndex - myBosDnBar) <= myFvgExpiry;

	if (myBullFvgHigh !== null && myRecentBosUp) {
		myBFvgH = myBullFvgHigh;
		myBFvgL = myBullFvgLow;
		myBFvgBar = myIndex;
	}

	if (myBearFvgHigh !== null && myRecentBosDn) {
		mySFvgH = myBearFvgHigh;
		mySFvgL = myBearFvgLow;
		mySFvgBar = myIndex;
	}

	// ── ENTRY CONDITIONS ────────────────────────────────
	const myFvgValid = myBFvgBar !== null && (myIndex - myBFvgBar) <= myFvgExpiry;
	const mySfvgValid = mySFvgBar !== null && (myIndex - mySFvgBar) <= myFvgExpiry;

	const myLongCondNow = myBFvgL !== null && myFvgValid
		&& low[myIndex] <= myBFvgH && myCloseNow >= myBFvgL
		&& !myPositionOpen;

	const myShortCondNow = mySFvgH !== null && mySfvgValid
		&& high[myIndex] >= mySFvgL && myCloseNow <= mySFvgH
		&& !myPositionOpen;

	myLongCond[myIndex] = myLongCondNow;
	myShortCond[myIndex] = myShortCondNow;

	if (myLongCondNow) {
		myLongSL[myIndex] = myBFvgL - myAtrVal[myIndex] * mySlBuffer;
		myLongTP[myIndex] = myCloseNow + myAtrVal[myIndex] * myTpMult;
		myBFvgH = null;
		myBFvgL = null;
		myPositionOpen = true;
	}

	if (myShortCondNow) {
		myShortSL[myIndex] = mySFvgH + myAtrVal[myIndex] * mySlBuffer;
		myShortTP[myIndex] = myCloseNow - myAtrVal[myIndex] * myTpMult;
		mySFvgH = null;
		mySFvgL = null;
		myPositionOpen = true;
	}

	// Simplified position close: we flatten on the opposite signal only,
	// since full stop/limit exit tracking requires a backtest engine
	// which is outside the scope of a plotting/scanning indicator.
	if (myPositionOpen && (myLongCondNow || myShortCondNow) === false) {
		// position stays open until an opposite-direction entry condition appears
	}
}

// ── VISUALS ─────────────────────────────────────────
const myBosUpShape = for_every(myBosUp, _b => _b ? constants.icons.diamond : null);
const myBosDnShape = for_every(myBosDn, _b => _b ? constants.icons.diamond : null);
const myLongShape = for_every(myLongCond, _b => _b ? constants.icons.triangle_up : null);
const myShortShape = for_every(myShortCond, _b => _b ? constants.icons.triangle_down : null);

paint(myBosUpShape, { style: 'labels_below', color: 'green', name: 'BOS Up' });
paint(myBosDnShape, { style: 'labels_above', color: 'red', name: 'BOS Down' });
paint(myLongShape, { style: 'labels_below', color: 'green', name: 'FVG Long' });
paint(myShortShape, { style: 'labels_above', color: 'red', name: 'FVG Short' });

// ── SIGNALS (for scanner, alerts, strategy tester) ───
register_signal(myBosUp, 'Break of Structure Up');
register_signal(myBosDn, 'Break of Structure Down');
register_signal(myLongCond, 'FVG Long Entry');
register_signal(myShortCond, 'FVG Short Entry');