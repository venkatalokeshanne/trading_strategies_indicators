// NOTE: This is a best-effort translation of a Pine Script v6 STRATEGY into a
// TrendSpider indicator. TrendSpider custom indicators cannot run the native
// Pine strategy engine (no strategy.entry/exit, no bar-by-bar broker
// simulation), so position/SL/TP management below is approximated with a
// manual bar-by-bar simulation loop. Intrabar fill order (whether stop or
// limit would hit first within the same candle) is approximated by checking
// high >= stopLoss first, then low <= takeProfit.
describe_indicator('BTC Sell Strategy Clean Entries v2', 'price');

const myStochTab = input.tab('Stoch RSI');
const myRsiLength = myStochTab.number('RSI Length', 14, { min: 1, max: 200 });
const myStochLength = myStochTab.number('Stoch Length', 14, { min: 1, max: 200 });
const myStochK = myStochTab.number('K Smoothing', 3, { min: 1, max: 50 });
const myStochD = myStochTab.number('D Smoothing', 3, { min: 1, max: 50 });
const myObLevel = myStochTab.number('Overbought Level', 80, { min: 1, max: 100 });

const myVixTab = input.tab('VIX Fix');
const myVixLength = myVixTab.number('VIX Fix Length', 22, { min: 1, max: 500 });
const myVixThreshold = myVixTab.number('VIX Max (Grey)', 2.0, { min: 0, max: 100 });

const myTradeTab = input.tab('Trade');
const myRrPrimary = myTradeTab.number('RR Take Profit', 1.5, { min: 0.01, max: 50 });
const myAtrLen = myTradeTab.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMultSL = myTradeTab.number('ATR SL Mult', 2.0, { min: 0.01, max: 50 });
const myBreakevenR = myTradeTab.number('Move SL to BE at R', 0.8, { min: 0, max: 50 });
const myTrailATR = myTradeTab.boolean('ATR Trailing after BE', true);
const myTrailMult = myTradeTab.number('ATR Trail Mult', 1.5, { min: 0.01, max: 50 });
const myCooldownBars = myTradeTab.number('Cooldown Bars', 10, { min: 0, max: 1000 });

const mySessionTab = input.tab('Session');
const myUseSession = mySessionTab.boolean('Limit to London/NY', true);

const myTrendTab = input.tab('Trend');
const myHtfTF = myTrendTab.select('HTF for Trend (min)', '240', constants.time_frames);
const myEmaLen = myTrendTab.number('EMA Length (HTF)', 200, { min: 1, max: 1000 });

// VIX FIX
const myHighestClose = highest(close, myVixLength);
const myVixFix = mult(div(sub(myHighestClose, low), myHighestClose), 100);
const myIsVixGrey = for_every(myVixFix, _v => _v < myVixThreshold);

// STOCH RSI
const myRsiVal = rsi(close, myRsiLength);
const myStochRaw = stochastic(myRsiVal, myRsiVal, myRsiVal, myStochLength);
const myKLine = sma(myStochRaw, myStochK);
const myDLine = sma(myKLine, myStochD);

// Double-top refined logic, done with an explicit loop since it needs
// "bars since" lookback logic across multiple prior candles.
// Fixed: replaced "new Array(...).fill(false)" (which uses the
// prohibited "new" keyword) with Array.from(), which is allowed.
const myIsDoubleTop = Array.from({ length: close.length }, () => false);
for (let myI = 2; myI < close.length; myI += 1) {
	let myWasPreviouslyOB = false;
	for (let myJ = Math.max(2, myI - 10); myJ <= myI; myJ += 1) {
		if (myKLine[myJ - 1] >= myObLevel && myKLine[myJ - 2] < myObLevel) {
			myWasPreviouslyOB = true;
		}
	}
	const myCrossUnder = myKLine[myI - 1] >= myObLevel && myKLine[myI] < myObLevel;
	const myBearConfirm = myKLine[myI] < myDLine[myI];
	myIsDoubleTop[myI] = myWasPreviouslyOB && myCrossUnder && myBearConfirm;
}

// Trend filter (HTF EMA)
const myHtfData = await request.history(current.ticker, myHtfTF);
assert(!myHtfData.error, `Error fetching HTF data: "${myHtfData.error}"`);
const myEmaHTFRaw = ema(myHtfData.close, myEmaLen);
const myEmaHTFLanded = land_points_onto_series(myHtfData.time, myEmaHTFRaw, time, 'ge');
const myEmaHTF = interpolate_sparse_series(myEmaHTFLanded, 'constant');
const myTrendOK = for_every(close, myEmaHTF, (_c, _e) => _e != null && _c < _e);

// Session filter: approximated as exchange-time hours between 08:00 and 22:00,
// covering all 7 days (as per the Pine session string "0800-2200:1234567").
const mySessionOK = time.map(_t => {
	if (!myUseSession) {
		return true;
	}
	const myParsedTime = time_of(_t);
	return myParsedTime.hours >= 8 && myParsedTime.hours < 22;
});

// ATR / swing based SL and TP inputs
const myAtr = atr(high, low, close, myAtrLen);
const mySwingSL = highest(high, 5);

// Entry signal (pre-cooldown)
const myRawEntry = for_every(close, (_c, _prev, _idx) => {
	return myIsDoubleTop[_idx] && myIsVixGrey[_idx] && myTrendOK[_idx] && mySessionOK[_idx];
});

// Bar-by-bar simulation of position, cooldown, SL/TP and breakeven/trailing
const myEntryOut = series_of(null);
const myExitOut = series_of(null);
const myStopLossSeries = series_of(null);
const myTakeProfitSeries = series_of(null);

let myPositionOpen = false;
let myEntryPrice = 0;
let myStopLoss = 0;
let myTakeProfit = 0;
let myMovedToBE = false;
let myLastTradeBar = -Infinity;

for (let myI = 0; myI < close.length; myI += 1) {
	if (!myPositionOpen) {
		const myCooldownOK = (myLastTradeBar === -Infinity) || (myI - myLastTradeBar > myCooldownBars);
		if (myRawEntry[myI] && myCooldownOK) {
			myEntryPrice = close[myI];
			myStopLoss = Math.max(mySwingSL[myI], close[myI] + myAtrMultSL * myAtr[myI]);
			const myRiskPts = myStopLoss - close[myI];
			myTakeProfit = close[myI] - myRrPrimary * myRiskPts;
			myMovedToBE = false;
			myPositionOpen = true;
			myLastTradeBar = myI;
			myEntryOut[myI] = true;
			myStopLossSeries[myI] = myStopLoss;
			myTakeProfitSeries[myI] = myTakeProfit;
		}
	}
	else {
		if (high[myI] >= myStopLoss || low[myI] <= myTakeProfit) {
			myExitOut[myI] = true;
			myPositionOpen = false;
		}
		else {
			const myRNow = (myEntryPrice - close[myI]) / (myStopLoss - myEntryPrice);
			if (!myMovedToBE && myRNow >= myBreakevenR) {
				const myBeStop = myEntryPrice;
				let myNewStop = myBeStop;
				if (myTrailATR) {
					const myTStop = close[myI] + myTrailMult * myAtr[myI];
					myNewStop = Math.min(myBeStop, myTStop);
				}
				myStopLoss = myNewStop;
				myMovedToBE = true;
			}
			myStopLossSeries[myI] = myStopLoss;
			myTakeProfitSeries[myI] = myTakeProfit;
		}
	}
}

const myEntrySignal = for_every(close, (_c, _prev, _idx) => !!myEntryOut[_idx]);
const myExitSignal = for_every(close, (_c, _prev, _idx) => !!myExitOut[_idx]);

register_signal(myEntrySignal, 'Short Entry');
register_signal(myExitSignal, 'Short Exit');

const myEntryLabelSeries = for_every(close, (_c, _prev, _idx) => myEntryOut[_idx] ? constants.icons.triangle_down : null);
paint(myEntryLabelSeries, { style: 'labels_above', color: 'red', name: 'Short Entry Marker' });

const myStopLossLine = paint(myStopLossSeries, { name: 'Stop Loss', color: '#EF5350', style: 'ladder' });
const myTakeProfitLine = paint(myTakeProfitSeries, { name: 'Take Profit', color: '#26A69A', style: 'ladder' });
paint(myEmaHTF, { name: 'HTF EMA', color: '#4DA3FF', style: 'line' });