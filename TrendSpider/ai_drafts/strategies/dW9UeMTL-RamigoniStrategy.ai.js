describe_indicator('Night Breakout 2130 WIB v12', 'price');

// NOTE: TrendSpider Custom JS indicators cannot replicate a Pine Script
// `strategy()` (no position sizing, no intrabar stop/limit fills, no
// strategy.entry/exit/close_all engine). This script reproduces the exact
// Pine SIGNAL LOGIC (trend filter, candle filter, EMA200 touch filter,
// Jakarta time filter, SL/TP level calc) as an indicator with
// register_signal() outputs usable in Scanner/Alerts, plus visual SL/TP
// and EMA lines. Position-state tracking (flat/in-trade, 5-day timeout)
// is approximated with a simple sequential loop that mimics
// strategy.position_size == 0 checks.

const myTab = input.tab('Parameters');
const myTargetRiskUsd = myTab.number('Target Risk USD', 100, { min: 0.01, max: 1000000 });
const myLotStep = myTab.number('Broker Lot Step', 0.01, { min: 0.0001, max: 10 });
const myMaxSlPips = myTab.number('Max SL Pips', 500, { min: 1, max: 100000 });
const myPipValue = myTab.number('Pip Value', 0.1, { min: 0.000001, max: 1000 });
const myLookbackSr = myTab.number('Lookback Support/Resistance', 20, { min: 1, max: 500 });
const myTvMultiplier = myTab.number('Unit Multiplier', 100, { min: 0.0001, max: 100000 });
const myFiveDaySeconds = 432000; // 5 days in seconds (unix time is in seconds here)

const myMoment = library('moment-timezone');

// --- Indicators ---
const myEma50 = ema(close, 50);
const myEma200 = ema(close, 200);
const myRecentLow = lowest(low, myLookbackSr);
const myRecentHigh = highest(high, myLookbackSr);
const myMaxSlDist = myMaxSlPips * myPipValue;

// --- Entry time filter (Asia/Jakarta 21:15) ---
const myIsEntryTime = time.map(_t => {
	const myZoned = myMoment.tz(_t * 1000, 'Asia/Jakarta');
	return myZoned.hour() === 21 && myZoned.minute() === 15;
});

// --- Condition series ---
const myUptrendValid = for_every(myEma50, myEma200, close, (_e50, _e200, _c) => _e50 > _e200 && _c > _e50);
const myDowntrendValid = for_every(myEma50, myEma200, close, (_e50, _e200, _c) => _e50 < _e200 && _c < _e50);

const myBullishCandles = series_of(null);
const myBearishCandles = series_of(null);
const myNoTouchBuy = series_of(null);
const myNoTouchSell = series_of(null);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	myBullishCandles[myIndex] = (close[myIndex] > open[myIndex]) && (close[myIndex - 1] > open[myIndex - 1]);
	myBearishCandles[myIndex] = (close[myIndex] < open[myIndex]) && (close[myIndex - 1] < open[myIndex - 1]);
	myNoTouchBuy[myIndex] = (low[myIndex] > myEma200[myIndex]) && (low[myIndex - 1] > myEma200[myIndex - 1]);
	myNoTouchSell[myIndex] = (high[myIndex] < myEma200[myIndex]) && (high[myIndex - 1] < myEma200[myIndex - 1]);
}

const myLongCond = series_of(false);
const myShortCond = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	myLongCond[myIndex] = !!(myIsEntryTime[myIndex] && myUptrendValid[myIndex] && myBullishCandles[myIndex] && myNoTouchBuy[myIndex]);
	myShortCond[myIndex] = !!(myIsEntryTime[myIndex] && myDowntrendValid[myIndex] && myBearishCandles[myIndex] && myNoTouchSell[myIndex]);
}

// --- Stateful simulation: position flat/open, SL/TP, 5-day timeout ---
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myExitSignal = series_of(false);
const mySlLine = series_of(null);
const myTpLine = series_of(null);

let myPositionSize = 0; // 0 flat, 1 long, -1 short
let mySlPrice = null;
let myTpPrice = null;
let myEntryTime = null;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	// 5-day timeout check (checked first, like Pine's order of blocks run every bar)
	if (myPositionSize !== 0 && myEntryTime !== null) {
		const myElapsedSeconds = time[myIndex] - myEntryTime;
		if (myElapsedSeconds >= myFiveDaySeconds) {
			myExitSignal[myIndex] = true;
			myPositionSize = 0;
			mySlPrice = null;
			myTpPrice = null;
			myEntryTime = null;
		}
	}

	if (myLongCond[myIndex] && myPositionSize === 0) {
		const myJarakSl = close[myIndex] - myRecentLow[myIndex];
		const myCandidateSl = myJarakSl > myMaxSlDist ? close[myIndex] - myMaxSlDist : myRecentLow[myIndex];
		const myCandidateTp = close[myIndex] + (close[myIndex] - myCandidateSl);

		const mySlDistancePoint = close[myIndex] - myCandidateSl;
		const mySlDistancePips = mySlDistancePoint / myPipValue;
		const myLossPer01Lot = mySlDistancePips * 0.1;

		if (myLossPer01Lot > 0) {
			myBuySignal[myIndex] = true;
			myPositionSize = 1;
			mySlPrice = myCandidateSl;
			myTpPrice = myCandidateTp;
			myEntryTime = time[myIndex];
		}
	}
	else if (myShortCond[myIndex] && myPositionSize === 0) {
		const myJarakSl = myRecentHigh[myIndex] - close[myIndex];
		const myCandidateSl = myJarakSl > myMaxSlDist ? close[myIndex] + myMaxSlDist : myRecentHigh[myIndex];
		const myCandidateTp = close[myIndex] - (myCandidateSl - close[myIndex]);

		const mySlDistancePoint = myCandidateSl - close[myIndex];
		const mySlDistancePips = mySlDistancePoint / myPipValue;
		const myLossPer01Lot = mySlDistancePips * 0.1;

		if (myLossPer01Lot > 0) {
			mySellSignal[myIndex] = true;
			myPositionSize = -1;
			mySlPrice = myCandidateSl;
			myTpPrice = myCandidateTp;
			myEntryTime = time[myIndex];
		}
	}

	// SL/TP intrabar hit check (approximation of strategy.exit stop/limit)
	if (myPositionSize === 1 && mySlPrice !== null) {
		if (low[myIndex] <= mySlPrice || high[myIndex] >= myTpPrice) {
			myExitSignal[myIndex] = true;
			myPositionSize = 0;
			mySlPrice = null;
			myTpPrice = null;
			myEntryTime = null;
		}
	}
	else if (myPositionSize === -1 && mySlPrice !== null) {
		if (high[myIndex] >= mySlPrice || low[myIndex] <= myTpPrice) {
			myExitSignal[myIndex] = true;
			myPositionSize = 0;
			mySlPrice = null;
			myTpPrice = null;
			myEntryTime = null;
		}
	}

	mySlLine[myIndex] = mySlPrice;
	myTpLine[myIndex] = myTpPrice;
}

// --- Visuals ---
paint(myEma50, { name: 'EMA50', color: '#2962FF', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#EF5350', thickness: 2 });
paint(mySlLine, { name: 'StopLoss', color: '#B71C1C', style: 'dotted', thickness: 1 });
paint(myTpLine, { name: 'TakeProfit', color: '#1B5E20', style: 'dotted', thickness: 1 });

const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);
paint(myBuyMarks, { name: 'BuyMark', style: 'labels_below', color: '#1B5E20', thickness: 6 });
paint(mySellMarks, { name: 'SellMark', style: 'labels_above', color: '#B71C1C', thickness: 6 });

// --- Signals for Scanner / Alerts / Strategy Tester ---
register_signal(myBuySignal, 'Buy Entry');
register_signal(mySellSignal, 'Sell Entry');
register_signal(myExitSignal, 'Exit Position');