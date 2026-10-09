describe_indicator("AGNI MOMENTUM Ultimate Swing Strategy", "price");

// ======================================================
// This is a best-effort line-by-line port of the Pine
// Strategy. TrendSpider Custom JS has no native
// strategy.entry/strategy.exit broker simulation, so the
// position/entry/stop/target state machine below is
// manually re-implemented bar by bar using plain arrays,
// mirroring the Pine logic as closely as possible.
// Custom session timezone offset (tzOffset, e.g. GMT+530)
// is not supported by the platform; the script uses the
// exchange's native timezone time instead (see flag below).
// ======================================================

const myDirectionRow = input.tab("Trade Direction");
const myEnableBuy = myDirectionRow.boolean("Allow BUY Trades", true);
const myEnableSell = myDirectionRow.boolean("Allow SELL Trades", false);

const mySessionTab = input.tab("Session");
const myEntrySessionText = mySessionTab.text("Entry Window (HHMM-HHMM)", "0015-0000");
const myExitTime = mySessionTab.number("Forced Exit Time (HHMM)", 1529, { min: 0, max: 2359 });

const myRiskTab = input.tab("Risk");
const myRRRatio = myRiskTab.number("Risk/Reward Ratio", 3.0, { min: 1, max: 20 });
const myAtrMultiplier = myRiskTab.number("ATR SL Multiplier", 1.5, { min: 0.1, max: 10 });
const myUseTrailing = myRiskTab.boolean("Enable Trailing Stop", true);

const myIndicatorsTab = input.tab("Indicators");
const myStochLen = myIndicatorsTab.number("Stoch RSI Length", 14, { min: 1, max: 100 });
const mySmoothK = myIndicatorsTab.number("K Smoothing", 3, { min: 1, max: 50 });
const mySmoothD = myIndicatorsTab.number("D Smoothing", 3, { min: 1, max: 50 });

// ======================================================
// Parse entry session window "HHMM-HHMM" (supports wrap-around)
// ======================================================
function myParseSession(_text) {
	const myParts = _text.split("-");
	const myFromRaw = parseInt(myParts[0], 10);
	const myToRaw = parseInt(myParts[1], 10);
	return { from: myFromRaw, to: myToRaw };
}
const mySessionWindow = myParseSession(myEntrySessionText);

// ======================================================
// Daily-resetting VWAP (manual, since built-in vwap() is
// anchored from a fixed index, not auto daily resetting)
// ======================================================
const myHlc3 = hlc3;
const myVwapValues = series_of(null);
let mySumPV = 0;
let mySumV = 0;
let myPrevDaySession = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myDaySession = bar_at(time[myIndex]).session;
	if (myDaySession !== myPrevDaySession) {
		mySumPV = 0;
		mySumV = 0;
		myPrevDaySession = myDaySession;
	}
	mySumPV += myHlc3[myIndex] * (volume[myIndex] || 0);
	mySumV += (volume[myIndex] || 0);
	myVwapValues[myIndex] = mySumV > 0 ? mySumPV / mySumV : myHlc3[myIndex];
}

// ======================================================
// Indicators
// ======================================================
const myRsiVal = rsi(close, myStochLen);
const myStochRaw = stochastic(myRsiVal, myRsiVal, myRsiVal, myStochLen);
const myStochK = sma(myStochRaw, mySmoothK);
const myStochD = sma(myStochK, mySmoothD);
const myAtrVal = atr(high, low, close, 14);

// ======================================================
// Session / time filter (uses exchange timezone, not the
// custom tzOffset defined in Pine)
// ======================================================
const myCurrTime = time.map(_t => {
	const myParsed = time_of(_t);
	return myParsed.hours * 100 + myParsed.minutes;
});

function myInSession(_curr) {
	if (mySessionWindow.from <= mySessionWindow.to) {
		return _curr >= mySessionWindow.from && _curr < mySessionWindow.to;
	}
	else {
		// window wraps past midnight
		return _curr >= mySessionWindow.from || _curr < mySessionWindow.to;
	}
}

// ======================================================
// Crossover / Crossunder of stochK vs stochD
// ======================================================
const myLongTrigger = series_of(false);
const myShortTrigger = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myK = myStochK[myIndex];
	const myD = myStochD[myIndex];
	const myKPrev = myStochK[myIndex - 1];
	const myDPrev = myStochD[myIndex - 1];

	if (myK == null || myD == null || myKPrev == null || myDPrev == null) {
		continue;
	}

	const myCrossOver = myKPrev <= myDPrev && myK > myD;
	const myCrossUnder = myKPrev >= myDPrev && myK < myD;
	const myInSess = myInSession(myCurrTime[myIndex]);

	myLongTrigger[myIndex] = myCrossOver && close[myIndex] > myVwapValues[myIndex] && myInSess && myEnableBuy;
	myShortTrigger[myIndex] = myCrossUnder && close[myIndex] < myVwapValues[myIndex] && myInSess && myEnableSell;
}

// ======================================================
// Manual position / entry / SL / TP / trailing simulation
// ======================================================
const myTargetLine = series_of(null);
const myStopLine = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myExitSignal = series_of(false);

let myPositionSize = 0; // 0 = flat, 1 = long, -1 = short
let myEntrySl = null;
let myEntryTp = null;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myClose = close[myIndex];
	const myAtr = myAtrVal[myIndex];

	if (myLongTrigger[myIndex] && myPositionSize === 0) {
		myEntrySl = myClose - (myAtr * myAtrMultiplier);
		const myRisk = myClose - myEntrySl;
		myEntryTp = myClose + (myRisk * myRRRatio);
		myPositionSize = 1;
		myLongEntrySignal[myIndex] = true;
	}

	if (myShortTrigger[myIndex] && myPositionSize === 0) {
		myEntrySl = myClose + (myAtr * myAtrMultiplier);
		const myRisk = myEntrySl - myClose;
		myEntryTp = myClose - (myRisk * myRRRatio);
		myPositionSize = -1;
		myShortEntrySignal[myIndex] = true;
	}

	if (myUseTrailing && myPositionSize > 0) {
		myEntrySl = Math.max(myEntrySl, low[myIndex - 1]);
	}
	if (myUseTrailing && myPositionSize < 0) {
		myEntrySl = Math.min(myEntrySl, high[myIndex - 1]);
	}

	// Exit checks: stop or target hit intrabar (using high/low of current candle)
	if (myPositionSize > 0) {
		if (low[myIndex] <= myEntrySl || high[myIndex] >= myEntryTp) {
			myPositionSize = 0;
			myEntrySl = null;
			myEntryTp = null;
			myExitSignal[myIndex] = true;
		}
	}
	else if (myPositionSize < 0) {
		if (high[myIndex] >= myEntrySl || low[myIndex] <= myEntryTp) {
			myPositionSize = 0;
			myEntrySl = null;
			myEntryTp = null;
			myExitSignal[myIndex] = true;
		}
	}

	// Forced EOD exit
	if (myPositionSize !== 0 && myCurrTime[myIndex] >= myExitTime) {
		myPositionSize = 0;
		myEntrySl = null;
		myEntryTp = null;
		myExitSignal[myIndex] = true;
	}

	myTargetLine[myIndex] = myPositionSize !== 0 ? myEntryTp : null;
	myStopLine[myIndex] = myPositionSize !== 0 ? myEntrySl : null;
}

// ======================================================
// Visuals
// ======================================================
paint(myVwapValues, { name: "VWAP Line", color: "orange", thickness: 2, hidden: true });
paint(myTargetLine, { name: "Target Line", color: "#00FF00", thickness: 4, style: "line" });
paint(myStopLine, { name: "Stop Trail Line", color: "#FF0000", thickness: 4, style: "line" });

// ======================================================
// Signals for Scanner / Alerts / Strategy Tester
// ======================================================
register_signal(myLongEntrySignal, "Long Entry");
register_signal(myShortEntrySignal, "Short Entry");
register_signal(myExitSignal, "Position Exit");