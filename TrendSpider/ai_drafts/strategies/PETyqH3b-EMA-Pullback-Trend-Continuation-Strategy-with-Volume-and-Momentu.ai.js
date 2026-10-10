describe_indicator('EMA Pullback Trend Continuation', 'price');

// ── INPUTS ─────────────────────────────────────────────
const emaTab = input.tab('EMAs');
const myEmaFastLen = emaTab.number('Fast EMA (Pullback Level)', 50, { min: 1, max: 500 });
const myEmaSlowLen = emaTab.number('Slow EMA (Trend Filter)', 200, { min: 1, max: 1000 });

const momTab = input.tab('Momentum');
const myRsiLen = momTab.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiBull = momTab.number('RSI Min for Longs', 40, { min: 0, max: 100 });
const myRsiBear = momTab.number('RSI Max for Shorts', 60, { min: 0, max: 100 });

const volTab = input.tab('Volume');
const myVolLen = volTab.number('Volume MA Length', 20, { min: 1, max: 500 });

const riskTab = input.tab('Risk');
const myAtrLen = riskTab.number('ATR Length', 14, { min: 1, max: 200 });
const myTpMult = riskTab.number('TP ATR Multiplier', 2.5, { min: 0.1, max: 20 });
const mySlBuf = riskTab.number('SL ATR Buffer', 0.5, { min: 0, max: 20 });

// ── INDICATORS ──────────────────────────────────────────
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myRsiVal = rsi(close, myRsiLen);
const myAtrVal = atr(high, low, close, myAtrLen);
const myVolSma = sma(volume, myVolLen);
const mySwingLow = lowest(low, 5);
const mySwingHigh = highest(high, 5);

// ── TREND REGIME / PULLBACK / ENTRY LOGIC ───────────────
// NOTE: Pine's barstate.isconfirmed is approximated as "always true"
// since the engine always computes on closed data points here.
// NOTE: strategy.position_size==0 is reproduced via a manual stateful
// loop tracking a synthetic "in position" flag, since there is no
// built-in strategy/backtesting engine in Custom JS. SL/TP exits are
// approximated by checking whether a subsequent candle's high/low
// crosses the computed stop/limit levels (no intrabar fill priority
// modeling is possible, unlike Pine's broker emulator).
const myLongCond = series_of(false);
const myShortCond = series_of(false);
const myLongSL = series_of(null);
const myLongTP = series_of(null);
const myShortSL = series_of(null);
const myShortTP = series_of(null);
const myPnlLabelText = series_of(null);
const myPnlLabelIsLong = series_of(null);

let myPositionState = 0; // 0 = flat, 1 = long, -1 = short
let myEntrySL = null;
let myEntryTP = null;
let myEntryIsLong = null;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	// check for exit of an existing synthetic position first
	if (myPositionState === 1) {
		const myHitSL = low[myIndex] <= myEntrySL;
		const myHitTP = high[myIndex] >= myEntryTP;
		if (myHitSL || myHitTP) {
			const myExitPrice = myHitSL ? myEntrySL : myEntryTP;
			const myPnl = myExitPrice - close[myIndex]; // approximate, not sized
			myPnlLabelText[myIndex] = (myPnl > 0 ? 'W ' : 'L ') + myPnl.toFixed(2);
			myPnlLabelIsLong[myIndex] = true;
			myPositionState = 0;
		}
	}
	else if (myPositionState === -1) {
		const myHitSL = high[myIndex] >= myEntrySL;
		const myHitTP = low[myIndex] <= myEntryTP;
		if (myHitSL || myHitTP) {
			const myExitPrice = myHitSL ? myEntrySL : myEntryTP;
			const myPnl = close[myIndex] - myExitPrice; // approximate, not sized
			myPnlLabelText[myIndex] = (myPnl > 0 ? 'W ' : 'L ') + myPnl.toFixed(2);
			myPnlLabelIsLong[myIndex] = false;
			myPositionState = 0;
		}
	}

	const myBullRegime = myEmaFast[myIndex] > myEmaSlow[myIndex];
	const myBearRegime = myEmaFast[myIndex] < myEmaSlow[myIndex];

	const myTouchedEmaFromAbove = (low[myIndex - 1] <= myEmaFast[myIndex - 1]) || (close[myIndex - 1] < myEmaFast[myIndex - 1]);
	const myTouchedEmaFromBelow = (high[myIndex - 1] >= myEmaFast[myIndex - 1]) || (close[myIndex - 1] > myEmaFast[myIndex - 1]);

	const myBullConfirm = (close[myIndex] > myEmaFast[myIndex]) && myTouchedEmaFromAbove;
	const myBearConfirm = (close[myIndex] < myEmaFast[myIndex]) && myTouchedEmaFromBelow;

	const myVolAbove = volume[myIndex] > myVolSma[myIndex];

	const myLong = myBullRegime && myBullConfirm && myVolAbove && (myRsiVal[myIndex] > myRsiBull) && (myPositionState === 0);
	const myShort = myBearRegime && myBearConfirm && myVolAbove && (myRsiVal[myIndex] < myRsiBear) && (myPositionState === 0);

	myLongCond[myIndex] = myLong;
	myShortCond[myIndex] = myShort;

	if (myLong) {
		myLongSL[myIndex] = mySwingLow[myIndex] - myAtrVal[myIndex] * mySlBuf;
		myLongTP[myIndex] = close[myIndex] + myAtrVal[myIndex] * myTpMult;
		myPositionState = 1;
		myEntrySL = myLongSL[myIndex];
		myEntryTP = myLongTP[myIndex];
	}
	else if (myShort) {
		myShortSL[myIndex] = mySwingHigh[myIndex] + myAtrVal[myIndex] * mySlBuf;
		myShortTP[myIndex] = close[myIndex] - myAtrVal[myIndex] * myTpMult;
		myPositionState = -1;
		myEntrySL = myShortSL[myIndex];
		myEntryTP = myShortTP[myIndex];
	}
}

// ── VISUALS ─────────────────────────────────────────────
paint(myEmaFast, { name: 'Fast EMA', color: '#FF9800', thickness: 2 });
paint(myEmaSlow, { name: 'Slow EMA', color: '#4284F3', thickness: 1 });

const myLongShapeSeries = for_every(myLongCond, _c => _c ? constants.icons.triangle_up : null);
const myShortShapeSeries = for_every(myShortCond, _c => _c ? constants.icons.triangle_down : null);

paint(myLongShapeSeries, { name: 'Pullback Long', style: 'labels_below', color: '#26A69A' });
paint(myShortShapeSeries, { name: 'Pullback Short', style: 'labels_above', color: '#EF5350' });

// P&L approximation labels, painted on the Fast EMA line
const myEmaFastPainted = paint(series_of(null), { name: 'Pnl Marker Anchor', color: 'gray', hidden: true });
for (let myLabelIndex = 0; myLabelIndex < myPnlLabelText.length; myLabelIndex += 1) {
	if (myPnlLabelText[myLabelIndex] !== null) {
		paint_label_at_line(myEmaFastPainted, myLabelIndex, myPnlLabelText[myLabelIndex], {
			background_color: myPnlLabelText[myLabelIndex].startsWith('W') ? 'green' : 'red',
			color: 'white'
		});
	}
}

// ── SIGNALS FOR SCANNER STRATEGY ALERTS ─────────────────
register_signal(myLongCond, 'EMA Pullback Long Confirmed');
register_signal(myShortCond, 'EMA Pullback Short Confirmed');