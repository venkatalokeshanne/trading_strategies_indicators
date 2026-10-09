describe_indicator('Asia Liquidity Sweep Reversal Scalper', 'price');

// NOTE: this indicator reproduces the Pine Script logic as closely as
// the TrendSpider Custom JS API allows. There is no actual backtesting
// engine available here (no strategy.entry/exit, no equity simulation),
// so the strategy loop below is a manual re-implementation of the Pine
// position state machine, driven bar by bar. Also, input.session() does
// not exist in this API, so the Asia session is approximated using
// plain "start hour" / "end hour" (New York time) numeric inputs instead
// of a full session string.

const momentTz = library('moment-timezone');

const sessionTab = input.tab('Session');
const useSession = sessionTab.boolean('Restrict trades to Asia session', true);
const sessionRow = sessionTab.row();
// Input names were shortened to fit the platform's name length limit.
const sessionStartHour = sessionRow.number('Asia Start Hour NY', 19, { min: 0, max: 23 });
const sessionEndHour = sessionRow.number('Asia End Hour NY', 0, { min: 0, max: 23 });

const pivotTab = input.tab('Pivots & RSI');
const pivotRow = pivotTab.row();
const myPivotLeft = pivotRow.number('Pivot Left Bars', 3, { min: 1, max: 20 });
const myPivotRight = pivotRow.number('Pivot Right Bars', 3, { min: 1, max: 20 });

const rsiRow = pivotTab.row();
const myRsiLen = rsiRow.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiMaxLong = rsiRow.number('Max RSI for Long', 45, { min: 1, max: 99 });
const myRsiMinShort = rsiRow.number('Min RSI for Short', 55, { min: 1, max: 99 });

const exitTab = input.tab('Exits');
const atrRow = exitTab.row();
const myAtrLen = atrRow.number('ATR Length', 14, { min: 1, max: 200 });
const mySlAtr = atrRow.number('Stop Loss ATR Mult', 1.2, { min: 0.1, max: 20, step: 0.1 });
const myTpAtr = atrRow.number('Take Profit ATR Mult', 1.4, { min: 0.1, max: 20, step: 0.1 });

const timeExitRow = exitTab.row();
const myUseTimeExit = timeExitRow.boolean('Time-based exit (bars)', true);
const myMaxHoldBars = timeExitRow.number('Max Bars to Hold', 25, { min: 1, max: 500 });

// -------------------------
// Base series computed outside loop (never call indicators inside loops)
// -------------------------
const myPivotHighSparse = pivot_high(high, myPivotLeft, myPivotRight);
const myPivotLowSparse = pivot_low(low, myPivotLeft, myPivotRight);
const myRsiArr = rsi(close, myRsiLen);
const myAtrArr = atr(high, low, close, myAtrLen);

// Approximate "Asia session (New York time)" membership per candle
const myInSessionArr = time.map(_t => {
	const myNyTime = momentTz.tz(_t * 1000, 'America/New_York');
	const myHour = myNyTime.hour();

	if (sessionStartHour <= sessionEndHour) {
		return myHour >= sessionStartHour && myHour < sessionEndHour;
	}
	// overnight session, e.g. 19 -> 0
	return myHour >= sessionStartHour || myHour < sessionEndHour;
});

// -------------------------
// Output series
// -------------------------
const myLastPivotHighArr = series_of(null);
const myLastPivotLowArr = series_of(null);
const myLongEntryArr = series_of(false);
const myShortEntryArr = series_of(false);
const myStopTpExitArr = series_of(false);
const myTimeExitArr = series_of(false);

let myLastPH = null;
let myLastPL = null;
let myPositionSize = 0; // 0 = flat, 1 = long, -1 = short
let myEntryBar = -1;
let myEntryPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPivotHighSparse[myIndex] !== null) {
		myLastPH = myPivotHighSparse[myIndex];
	}
	if (myPivotLowSparse[myIndex] !== null) {
		myLastPL = myPivotLowSparse[myIndex];
	}

	myLastPivotHighArr[myIndex] = myLastPH;
	myLastPivotLowArr[myIndex] = myLastPL;

	const myTradeOK = useSession ? myInSessionArr[myIndex] : true;
	const mySweepDown = myTradeOK && myLastPL !== null && low[myIndex] < myLastPL && close[myIndex] > myLastPL;
	const mySweepUp = myTradeOK && myLastPH !== null && high[myIndex] > myLastPH && close[myIndex] < myLastPH;

	if (myPositionSize === 0) {
		const myLongOK = mySweepDown && myRsiArr[myIndex] <= myRsiMaxLong;
		const myShortOK = mySweepUp && myRsiArr[myIndex] >= myRsiMinShort;

		if (myLongOK) {
			myLongEntryArr[myIndex] = true;
			myPositionSize = 1;
			myEntryPrice = close[myIndex];
			myEntryBar = myIndex;
		}
		else if (myShortOK) {
			myShortEntryArr[myIndex] = true;
			myPositionSize = -1;
			myEntryPrice = close[myIndex];
			myEntryBar = myIndex;
		}
	}
	else {
		const myCurrentAtr = myAtrArr[myIndex];
		let myExited = false;

		if (myPositionSize === 1) {
			const myLongStop = myEntryPrice - mySlAtr * myCurrentAtr;
			const myLongLimit = myEntryPrice + myTpAtr * myCurrentAtr;

			if (low[myIndex] <= myLongStop || high[myIndex] >= myLongLimit) {
				myStopTpExitArr[myIndex] = true;
				myPositionSize = 0;
				myExited = true;
			}
		}
		else {
			const myShortStop = myEntryPrice + mySlAtr * myCurrentAtr;
			const myShortLimit = myEntryPrice - myTpAtr * myCurrentAtr;

			if (high[myIndex] >= myShortStop || low[myIndex] <= myShortLimit) {
				myStopTpExitArr[myIndex] = true;
				myPositionSize = 0;
				myExited = true;
			}
		}

		if (!myExited && myUseTimeExit) {
			const myHeldBars = myIndex - myEntryBar;

			if (myHeldBars >= myMaxHoldBars) {
				myTimeExitArr[myIndex] = true;
				myPositionSize = 0;
			}
		}
	}
}

// -------------------------
// Visuals
// -------------------------
paint(myLastPivotHighArr, { name: 'Last Pivot High', color: '#EF5350', style: 'ladder', thickness: 1 });
paint(myLastPivotLowArr, { name: 'Last Pivot Low', color: '#26A69A', style: 'ladder', thickness: 1 });

const myCandleColors = myInSessionArr.map(_s => _s ? 'rgba(156,39,176,0.25)' : null);
color_candles(myCandleColors);

// -------------------------
// Signals for scanning, alerts and strategy testing
// -------------------------
register_signal(myLongEntryArr, 'Long Entry');
register_signal(myShortEntryArr, 'Short Entry');
register_signal(myStopTpExitArr, 'Stop Loss or Take Profit Exit');
register_signal(myTimeExitArr, 'Time Based Exit');