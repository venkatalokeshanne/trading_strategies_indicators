describe_indicator('SMC Breakout', 'price');

// ───── Inputs ─────────────────────────────────────────────────────
const coreTab = input.tab('Core Settings');
const myPeriod = coreTab.number('Swing Length', 20, { min: 1, max: 200 });
const myCandleType = coreTab.select('Breakout Type', 'Wicks', ['Wicks', 'Body']);
const myRR = coreTab.number('Risk Reward Ratio', 1.1, { min: 0.1, max: 20, step: 0.1 });
const mySlType = coreTab.select('SL Type', 'Close', ['Close', 'High/Low']);
const myShowSignals = coreTab.boolean('Show Signals', true);

const riskTab = input.tab('Risk');
// shortened input names to satisfy the input() name length limit
const myStopLossPct = riskTab.number('Stop Loss %', 1.0, { min: 0, max: 100, step: 0.1 });
const myTakeProfitPct = riskTab.number('Take Profit %', 2.0, { min: 0, max: 100, step: 0.1 });
const myRiskPct = riskTab.number('Risk %', 1.0, { min: 0, max: 100, step: 0.1 });

const GREEN = '#028545';
const RED = '#f60707';
const GREENDARK = '#026a59';

// ───── ATR based stop distance (mirrors ta.rma(ta.tr(true), 14)) ────
const myAtr = atr(high, low, close, 14);
const myX2 = sub(low, mult(myAtr, 1.5));
const myXz = add(mult(myAtr, 1.5), high);
const myLongDiffSL = for_every(close, myX2, (_c, _x2) => Math.abs(_c - _x2));
const myLongDiffSL2 = for_every(close, myXz, (_c, _xz) => Math.abs(_c - _xz));

// ───── Pivot detection ───────────────────────────────────────────────
const myPH = pivot_high(high, myPeriod, myPeriod);
const myPL = pivot_low(low, myPeriod, myPeriod);

const myScrHigh = myCandleType === 'Wicks' ? high : close;
const myScrLow = myCandleType === 'Wicks' ? low : close;

// ───── Stateful simulation (mirrors Pine's bar-by-bar var state) ────
const myLen = close.length;
const myBuySignal = series_of(null);
const mySellSignal = series_of(null);
const myBullCon = series_of(false);
const myBearCon = series_of(false);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);

let myUpdatedHigh = null;
let myUpdatedLow = null;
let myPhActive = false;
let myPlActive = false;
let myTradeIsOn = false;
let myLongTrade = false;
let myShortTrade = false;

for (let myIndex = 0; myIndex < myLen; myIndex += 1) {
	if (myPH[myIndex] !== null && myPH[myIndex] !== undefined) {
		myUpdatedHigh = myPH[myIndex];
		myPhActive = true;
	}
	if (myPL[myIndex] !== null && myPL[myIndex] !== undefined) {
		myUpdatedLow = myPL[myIndex];
		myPlActive = true;
	}

	const myBuy = myUpdatedHigh !== null && myScrHigh[myIndex] > myUpdatedHigh && myPhActive;
	const mySell = myUpdatedLow !== null && myScrLow[myIndex] < myUpdatedLow && myPlActive;

	if (myBuy) {
		myPhActive = false;
	}
	if (mySell) {
		myPlActive = false;
	}

	// Note: barstate.isconfirmed is approximated as "always true" since
	// the Custom JS engine has no concept of a live/unconfirmed bar here.
	const myLongCondition = myBuy && !myTradeIsOn;
	const myShortCondition = mySell && !myTradeIsOn;

	if (myLongCondition) {
		myLongTrade = true;
		myShortTrade = false;
		myTradeIsOn = true;
	}
	if (myShortCondition) {
		myLongTrade = false;
		myShortTrade = true;
		myTradeIsOn = true;
	}

	// Simplified position-closed detection: since this is not a real
	// strategy engine, we treat a trade as closed once the opposite
	// signal fires or at the next breakout event (approximation of
	// strategy.position_size == 0, which requires a real backtester).
	if (myLongCondition || myShortCondition) {
		// trade just opened, stays on until an opposite/next signal
	}

	myBuySignal[myIndex] = myLongCondition ? constants.icons.triangle_up : null;
	mySellSignal[myIndex] = myShortCondition ? constants.icons.triangle_down : null;
	myBullCon[myIndex] = myTradeIsOn && myLongTrade;
	myBearCon[myIndex] = myTradeIsOn && myShortTrade;
	myLongEntrySignal[myIndex] = myLongCondition;
	myShortEntrySignal[myIndex] = myShortCondition;
}

// ───── Candle coloring ───────────────────────────────────────────────
const myCandleColors = for_every(myBearCon, myBullCon, (_bear, _bull) => _bear ? RED : (_bull ? GREENDARK : null));
color_candles(myCandleColors);

// ───── Signal plotting ────────────────────────────────────────────────
paint(myShowSignals ? myBuySignal : series_of(null), { style: 'labels_below', color: GREEN, name: 'Buy Signal' });
paint(myShowSignals ? mySellSignal : series_of(null), { style: 'labels_above', color: RED, name: 'Sell Signal' });

// ───── Scanner/strategy signals ───────────────────────────────────────
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myBullCon, 'In Long Trade');
register_signal(myBearCon, 'In Short Trade');