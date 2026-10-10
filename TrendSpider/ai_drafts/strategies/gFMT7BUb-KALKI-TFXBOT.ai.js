// This is an adaptation of a Pine Script v6 strategy ("KALKI TFXBOT")
// into TrendSpider Custom JS. Some Pine Script concepts have no direct
// equivalent in this engine (see assumptions below), so this is a close
// approximation of the original logic, not a byte-for-byte port.
describe_indicator('KALKI TFXBOT', 'price');

// ------------------------------------------------------------------
// Inputs (grouped like the original Pine script groups)
// ------------------------------------------------------------------
const myRiskTab = input.tab('Cartel Risk Management');
const myRR = myRiskTab.number('Risk to Reward Ratio', 3.0, { min: 0.5, max: 20, step: 0.5 });
const mySlBufferPips = myRiskTab.number('Stop Loss Buffer (Pips)', 0.5, { min: 0, max: 50, step: 0.1 });

const myFiltTab = input.tab('SMC Filters');
const myEmaTrendLength = myFiltTab.number('EMA Trend Guard', 200, { min: 1, max: 500 });
const myPivotLeft = myFiltTab.number('Swing Left Lookback', 10, { min: 1, max: 100 });
const myPivotRight = myFiltTab.number('Swing Right Lookback', 3, { min: 1, max: 100 });

// ------------------------------------------------------------------
// Core SMC structure
// ------------------------------------------------------------------
const myEma200 = ema(close, myEmaTrendLength);

// Pine's ta.pivotlow/pivothigh use left/right lookback, confirmed `right` bars later.
// pivot_low/pivot_high here work the same way (sparse series).
const myPivotLowSparse = pivot_low(low, myPivotLeft, myPivotRight);
const myPivotHighSparse = pivot_high(high, myPivotLeft, myPivotRight);

// Carry forward the last known pivot value ("var float current_sup/res" in Pine)
const myCurrentSupport = for_every(myPivotLowSparse, (_pl, _prev) => (_pl !== null && _pl !== undefined) ? _pl : (_prev === undefined ? null : _prev));
const myCurrentResistance = for_every(myPivotHighSparse, (_ph, _prev) => (_ph !== null && _ph !== undefined) ? _ph : (_prev === undefined ? null : _prev));

// Sweep (liquidity grab) logic
const mySweepBuy = for_every(low, close, open, myEma200, myCurrentSupport,
	(_low, _close, _open, _ema, _sup) => _sup !== null && _low < _sup && _close > _sup && _close > _open && _close > _ema
);

const mySweepSell = for_every(high, close, open, myEma200, myCurrentResistance,
	(_high, _close, _open, _ema, _res) => _res !== null && _high > _res && _close < _res && _close < _open && _close < _ema
);

// ------------------------------------------------------------------
// Simplified strategy / position simulation
// ASSUMPTION: TrendSpider has no native strategy engine with intrabar
// stop/limit execution. We approximate exits by checking whether
// high/low of the SAME or LATER bars touch the stored SL/TP levels.
// This can diverge from the real Pine Script backtester, which
// processes orders on bar close and manages true broker-level fills.
// ------------------------------------------------------------------
const myCandleCount = close.length;
const myPositionSeries = series_of(0); // 1 = long, -1 = short, 0 = flat
const myEntrySignal = series_of(false);
const mySellSignal = series_of(false);
const myCloseLongSignal = series_of(false);
const myCloseShortSignal = series_of(false);
const mySlLine = series_of(null);
const myTpLine = series_of(null);
const myEntryLine = series_of(null);

let myPosition = 0;
let myEntryPrice = null;
let mySlPrice = null;
let myTpPrice = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	// Check exits first (approximation of strategy.exit stop/limit)
	if (myPosition === 1) {
		if (low[myIndex] <= mySlPrice) {
			myCloseLongSignal[myIndex] = true;
			myPosition = 0; myEntryPrice = null; mySlPrice = null; myTpPrice = null;
		}
		else if (high[myIndex] >= myTpPrice) {
			myCloseLongSignal[myIndex] = true;
			myPosition = 0; myEntryPrice = null; mySlPrice = null; myTpPrice = null;
		}
	}
	else if (myPosition === -1) {
		if (high[myIndex] >= mySlPrice) {
			myCloseShortSignal[myIndex] = true;
			myPosition = 0; myEntryPrice = null; mySlPrice = null; myTpPrice = null;
		}
		else if (low[myIndex] <= myTpPrice) {
			myCloseShortSignal[myIndex] = true;
			myPosition = 0; myEntryPrice = null; mySlPrice = null; myTpPrice = null;
		}
	}

	// Entries
	if (mySweepBuy[myIndex] && myPosition <= 0) {
		if (myPosition < 0) {
			myCloseShortSignal[myIndex] = true;
		}
		myEntryPrice = close[myIndex];
		mySlPrice = low[myIndex] - (mySlBufferPips / 10);
		const myRiskAmount = myEntryPrice - mySlPrice;
		myTpPrice = myEntryPrice + (myRiskAmount * myRR);
		myPosition = 1;
		myEntrySignal[myIndex] = true;
	}
	else if (mySweepSell[myIndex] && myPosition >= 0) {
		if (myPosition > 0) {
			myCloseLongSignal[myIndex] = true;
		}
		myEntryPrice = close[myIndex];
		mySlPrice = high[myIndex] + (mySlBufferPips / 10);
		const myRiskAmount = mySlPrice - myEntryPrice;
		myTpPrice = myEntryPrice - (myRiskAmount * myRR);
		myPosition = -1;
		mySellSignal[myIndex] = true;
	}

	myPositionSeries[myIndex] = myPosition;
	mySlLine[myIndex] = mySlPrice;
	myTpLine[myIndex] = myTpPrice;
	myEntryLine[myIndex] = myEntryPrice;
}

// ------------------------------------------------------------------
// Painting
// ------------------------------------------------------------------
paint(myEma200, { name: 'EMA Trend Guard', color: '#f7c948', thickness: 2 });

paint(myCurrentSupport, { name: 'Liquidity Floor', color: '#4da3ff', style: 'dotted', thickness: 2 });
paint(myCurrentResistance, { name: 'Liquidity Ceiling', color: '#ff5a5f', style: 'dotted', thickness: 2 });

paint(myEntryLine, { name: 'Entry Level', color: '#2962ff', style: 'ladder', thickness: 1 });

const mySlLinePainted = paint(mySlLine, { name: 'Stop Loss Level', color: '#9c9c9c', style: 'ladder', thickness: 1 });
const myTpLinePainted = paint(myTpLine, { name: 'Take Profit Level', color: '#4dd0e1', style: 'ladder', thickness: 1 });
fill(mySlLinePainted, myTpLinePainted, '#4dd0e1', 0.08);

const myBuyMarks = for_every(mySweepBuy, low, (_sig, _low) => _sig ? _low : null);
const mySellMarks = for_every(mySweepSell, high, (_sig, _high) => _sig ? _high : null);
paint(myBuyMarks, { name: 'Sweep Buy', style: 'labels_below', color: '#26a69a', thickness: 3 });
paint(mySellMarks, { name: 'Sweep Sell', style: 'labels_above', color: '#ef5350', thickness: 3 });

// ------------------------------------------------------------------
// Signals for scanner / alerts / strategy tester
// ------------------------------------------------------------------
register_signal(mySweepBuy, 'Sweep Buy Signal');
register_signal(mySweepSell, 'Sweep Sell Signal');
register_signal(myEntrySignal, 'Long Entry');
register_signal(mySellSignal, 'Short Entry');
register_signal(myCloseLongSignal, 'Close Long');
register_signal(myCloseShortSignal, 'Close Short');