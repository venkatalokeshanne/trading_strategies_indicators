describe_indicator("Allahs Compass", "lower");

// ─────────────────────────────────────────
// INPUTS
// ─────────────────────────────────────────
const myBbLength = input.number("BB Length", 20, { min: 1, max: 500 });
const myBbMult = input.number("BB StdDev Multiplier", 2.0, { min: 0.1, max: 10, step: 0.1 });
const myStopLossPct = input.number("Stop Loss Percent", 100.0, { min: 0.1, max: 1000, step: 0.1 });
const myDivLookback = input.number("Divergence Lookback Bars", 10, { min: 1, max: 200 });

// ─────────────────────────────────────────
// BOLLINGER BAND %B CALCULATION
// ─────────────────────────────────────────
const myBasis = sma(close, myBbLength);
const myDev = mult(stdev(close, myBbLength), myBbMult);
const myUpper = add(myBasis, myDev);
const myLower = sub(myBasis, myDev);

// bbPct = (close - lower) / (upper - lower)
const myBbPct = for_every(close, myUpper, myLower, (_c, _u, _l) => {
	const myRange = _u - _l;
	return myRange !== 0 ? (_c - _l) / myRange : null;
});

// ─────────────────────────────────────────
// SIMULATE STRATEGY STATE (position, stop price, signals)
// This replicates Pine's bar-by-bar strategy execution using a loop,
// since Custom JS API has no native strategy engine. No indicator
// functions are called inside this loop (only plain comparisons).
// ─────────────────────────────────────────
const myN = close.length;

const myBuySignal = series_of(null);
const myDivAddOn = series_of(null);
const myBearishDivAlert = series_of(null);
const myExitSignal = series_of(null);
const myStopLossHitSignal = series_of(null);
const myStopPriceLine = series_of(null);

let myPositionSize = 0;
let myStopPrice = null;
const myBearishDivPrevState = [];
const myBullishDivPrevState = [];

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myCloseNow = close[myIndex];
	const myBbPctNow = myBbPct[myIndex];

	const myPrevBbPct = myIndex > 0 ? myBbPct[myIndex - 1] : null;
	const myCrossIntoGreen = (myPrevBbPct !== null && myBbPctNow !== null) && (myPrevBbPct <= 0.0 && myBbPctNow > 0.0);

	let myBullishDiv = false;
	let myBearishDiv = false;

	if (myIndex >= myDivLookback && myBbPctNow !== null) {
		const myPrevPriceLow = close[myIndex - myDivLookback];
		const myPrevBbPctLow = myBbPct[myIndex - myDivLookback];

		if (myPrevBbPctLow !== null) {
			myBullishDiv = (myCloseNow < myPrevPriceLow) && (myBbPctNow > myPrevBbPctLow) && (myBbPctNow < 0.2);
			myBearishDiv = (myCloseNow > myPrevPriceLow) && (myBbPctNow < myPrevBbPctLow) && (myBbPctNow > 0.8);
		}
	}

	const myBullishDivPrev = myBullishDivPrevState[myIndex - 1] || false;
	const myBearishDivPrev = myBearishDivPrevState[myIndex - 1] || false;
	myBullishDivPrevState[myIndex] = myBullishDiv;
	myBearishDivPrevState[myIndex] = myBearishDiv;

	const myDivAddOnNow = myBullishDiv && !myBullishDivPrev && myPositionSize > 0;
	const myBearishDivAlertNow = myBearishDiv && !myBearishDivPrev;

	const myExitSignalNow = myBbPctNow !== null && myBbPctNow >= 1.0;

	let myStopLossHitNow = false;

	// Initial entry
	if (myCrossIntoGreen && myPositionSize === 0) {
		myPositionSize = 1;
		myStopPrice = myCloseNow * (1 - myStopLossPct / 100);
	}

	// Add-on entry
	if (myDivAddOnNow) {
		myPositionSize += 2;
		const myCandidateStop = myCloseNow * (1 - myStopLossPct / 100);
		myStopPrice = myStopPrice === null ? myCandidateStop : Math.min(myStopPrice, myCandidateStop);
	}

	// Stop loss
	if (myPositionSize > 0 && myStopPrice !== null && myCloseNow <= myStopPrice) {
		myPositionSize = 0;
		myStopPrice = null;
		myStopLossHitNow = true;
	}

	// Take profit at BB% top
	if (myExitSignalNow && myPositionSize > 0) {
		myPositionSize = 0;
		myStopPrice = null;
	}

	myBuySignal[myIndex] = myCrossIntoGreen && (myPositionSize === 1 || (myPositionSize !== 0 && myStopLossHitNow === false)) ? true : null;
	// Note: buy signal is captured strictly at the entry condition evaluated before stop/exit same-bar changes
	myBuySignal[myIndex] = (myCrossIntoGreen) ? true : null;

	myDivAddOn[myIndex] = myDivAddOnNow ? true : null;
	myBearishDivAlert[myIndex] = myBearishDivAlertNow ? true : null;
	myExitSignal[myIndex] = (myExitSignalNow && myPositionSize >= 0 && (myDivAddOnNow || myCrossIntoGreen || true)) ? (myExitSignalNow ? true : null) : null;
	myStopLossHitSignal[myIndex] = myStopLossHitNow ? true : null;
	myStopPriceLine[myIndex] = myPositionSize > 0 ? myStopPrice : null;
}

// ─────────────────────────────────────────
// VISUALS
// ─────────────────────────────────────────
paint(horizontal_line(1.0), { name: "Upper Band", color: "#ef5350", style: "dotted" });
paint(horizontal_line(0.5), { name: "Middle Line", color: "#9e9e9e", style: "dotted" });
paint(horizontal_line(0.0), { name: "Lower Band", color: "#26a69a", style: "dotted" });

const myBbPctColor = for_every(myBbPct, _b => (_b !== null && _b >= 0.5) ? "#26a69a" : "#ef5350");
const myBbLinePainted = paint(myBbPct, { name: "BB Percent", color: myBbPctColor, thickness: 2 });

paint(myStopPriceLine, { name: "Stop Loss Line", color: "#ef5350", style: "dotted", forceUsePriceAxis: true });

// ─────────────────────────────────────────
// SIGNAL SHAPES
// ─────────────────────────────────────────
const myBuyMarks = for_every(myBuySignal, _s => _s ? constants.icons.triangle_up : null);
const myAddOnMarks = for_every(myDivAddOn, _s => _s ? constants.icons.diamond : null);
const myBearishMarks = for_every(myBearishDivAlert, _s => _s ? constants.icons.diamond : null);
const myExitMarks = for_every(myExitSignal, _s => _s ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: "Buy Signal", style: "labels_below", color: "#26a69a" });
paint(myAddOnMarks, { name: "Divergence AddOn", style: "labels_below", color: "#00bcd4" });
paint(myBearishMarks, { name: "Bearish Divergence", style: "labels_above", color: "#ff9800" });
paint(myExitMarks, { name: "Exit Signal", style: "labels_above", color: "#ef5350" });

// ─────────────────────────────────────────
// SCANNER / ALERT / STRATEGY SIGNALS
// ─────────────────────────────────────────
register_signal(for_every(myBuySignal, _s => !!_s), "Buy Entry");
register_signal(for_every(myDivAddOn, _s => !!_s), "Divergence AddOn Entry");
register_signal(for_every(myBearishDivAlert, _s => !!_s), "Bearish Divergence Alert");
register_signal(for_every(myExitSignal, _s => !!_s), "BB Top Exit");
register_signal(for_every(myStopLossHitSignal, _s => !!_s), "Stop Loss Hit");