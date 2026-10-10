describe_indicator('Sweep and Engulf Strategy', 'price');

// ═══════════════════════════════════════════════════════════════
// INPUTS
// ═══════════════════════════════════════════════════════════════

const myFiltersTab = input.tab('Signal Filters');
const myInvertTrades = myFiltersTab.boolean('Invert Strategy (Trade Opposite)', true);
const myPrevCandleFilter = myFiltersTab.select('Previous Candle Direction', 'Any', ['Any', 'Same Direction']);

const myEmaTab = input.tab('EMA Trend Filter');
const myUseEma = myEmaTab.boolean('Use & Show EMA Trend Filter', false);
const myEmaLength = myEmaTab.number('EMA Length', 200, { min: 1, max: 1000 });

const myRiskTab = input.tab('Risk Management');
const mySlType = myRiskTab.select('Stop Loss Method', 'ATR', ['ATR', 'Candle High/Low']);
const myAtrLength = myRiskTab.number('ATR Length', 14, { min: 1, max: 200 });
const mySlMult = myRiskTab.number('ATR Multiplier', 1.5, { min: 0.1, max: 20, step: 0.1 });
const myRrRatio = myRiskTab.number('Risk Reward Ratio', 2.0, { min: 0.1, max: 20, step: 0.1 });

// ═══════════════════════════════════════════════════════════════
// CORE SERIES (computed once, outside any loop)
// ═══════════════════════════════════════════════════════════════

const myEmaValue = ema(close, myEmaLength);
const myAtrValue = atr(high, low, close, myAtrLength);

const myLen = close.length;

// Output series
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const myEmaPlot = series_of(null);

// Sequential trade state machine, mirrors the Pine script's bar-by-bar logic.
// This cannot be vectorized because entries depend on the previous bar's
// trade state (inTrade), so we use a plain sequential loop (no indicator
// calls inside it, only plain arithmetic/comparisons which is allowed).
let myInTrade = false;
let myTradeDir = 0;
let myEntryPrice = null;
let mySlPrice = null;
let myTpPrice = null;
let myEntryBar = null;

for (let myIndex = 1; myIndex < myLen; myIndex += 1) {
	const myEmaVal = myEmaValue[myIndex];
	const myIsUptrend = close[myIndex] > myEmaVal;
	const myIsDowntrend = close[myIndex] < myEmaVal;

	myEmaPlot[myIndex] = myUseEma ? myEmaVal : null;

	const myPrevBullish = close[myIndex - 1] > open[myIndex - 1];
	const myPrevBearish = close[myIndex - 1] < open[myIndex - 1];

	const myReqBullish = myPrevCandleFilter === 'Any' || myPrevBullish;
	const myReqBearish = myPrevCandleFilter === 'Any' || myPrevBearish;

	const myTrendBullish = !myUseEma || myIsUptrend;
	const myTrendBearish = !myUseEma || myIsDowntrend;

	const myAtrVal = myAtrValue[myIndex];

	// Trade management (exit logic), mirrors the strategy.exit behavior
	if (myInTrade && myIndex > myEntryBar) {
		const myHitTP = (myTradeDir === 1 && high[myIndex] >= myTpPrice) || (myTradeDir === -1 && low[myIndex] <= myTpPrice);
		const myHitSL = (myTradeDir === 1 && low[myIndex] <= mySlPrice) || (myTradeDir === -1 && high[myIndex] >= mySlPrice);

		if (myHitTP || myHitSL) {
			myInTrade = false;
			myTradeDir = 0;
		}
	}

	const myBullishSweep = low[myIndex] < low[myIndex - 1] && close[myIndex] > high[myIndex - 1] && myReqBullish && myTrendBullish && myAtrVal != null && !isNaN(myAtrVal);
	const myBearishSweep = high[myIndex] > high[myIndex - 1] && close[myIndex] < low[myIndex - 1] && myReqBearish && myTrendBearish && myAtrVal != null && !isNaN(myAtrVal);

	const myRawLong = myInvertTrades ? myBearishSweep : myBullishSweep;
	const myRawShort = myInvertTrades ? myBullishSweep : myBearishSweep;

	const myLongSig = myRawLong && !myInTrade;
	const myShortSig = myRawShort && !myInTrade;

	myLongSignal[myIndex] = myLongSig;
	myShortSignal[myIndex] = myShortSig;

	if (myLongSig) {
		myInTrade = true;
		myTradeDir = 1;
		myEntryBar = myIndex;
		myEntryPrice = close[myIndex];
		mySlPrice = mySlType === 'Candle High/Low' ? low[myIndex] : myEntryPrice - (myAtrVal * mySlMult);
		const myRisk = myEntryPrice - mySlPrice;
		myTpPrice = myEntryPrice + (myRisk * myRrRatio);
	}

	if (myShortSig) {
		myInTrade = true;
		myTradeDir = -1;
		myEntryBar = myIndex;
		myEntryPrice = close[myIndex];
		mySlPrice = mySlType === 'Candle High/Low' ? high[myIndex] : myEntryPrice + (myAtrVal * mySlMult);
		const myRisk = mySlPrice - myEntryPrice;
		myTpPrice = myEntryPrice - (myRisk * myRrRatio);
	}
}

// ═══════════════════════════════════════════════════════════════
// VISUALS
// ═══════════════════════════════════════════════════════════════

const myEmaColor = for_every(close, myEmaValue, (_c, _e) => _c > _e ? '#089981' : '#f23645');
paint(myEmaPlot, { name: 'Trend EMA', color: myEmaColor, thickness: 2 });

const myLongMarks = for_every(myLongSignal, _s => _s ? constants.icons.triangle_up : null);
const myShortMarks = for_every(myShortSignal, _s => _s ? constants.icons.triangle_down : null);

paint(myLongMarks, { name: 'Long Entry', style: 'labels_below', color: '#089981' });
paint(myShortMarks, { name: 'Short Entry', style: 'labels_above', color: '#f23645' });

// ═══════════════════════════════════════════════════════════════
// SIGNALS (for scanners, alerts, strategy tester)
// ═══════════════════════════════════════════════════════════════

register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myShortSignal, 'Short Entry Signal');