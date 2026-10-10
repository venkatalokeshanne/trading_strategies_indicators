describe_indicator('PEM Terminator2', 'price');

// ---------------- INPUTS ----------------
const paramsTab = input.tab('Terminator2 Params');
const myAtrLen = paramsTab.number('ATR Length', 14, { min: 1, max: 100 });
const myImpulseMult = paramsTab.number('Impulse Strength (ATR)', 1.1, { min: 0.1, max: 10, step: 0.1 });
const myCompressPct = paramsTab.number('Compression Tightness %', 0.7, { min: 0.01, max: 5, step: 0.01 });
const myStallBars = paramsTab.number('Min Stall Bars', 2, { min: 1, max: 50 });
const myMinBodyFrac = paramsTab.number('Min Body % (Break)', 0.2, { min: 0, max: 1, step: 0.01 });

const emaTab = input.tab('EMA / VWAP');
const myEmaFastLen = emaTab.number('EMA Fast Length', 8, { min: 1, max: 500 });
const myEmaSlowLen = emaTab.number('EMA Slow Length', 55, { min: 1, max: 500 });

// ---------------- CORE INDICATORS ----------------
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myAtr = atr(high, low, close, myAtrLen);

// Session-anchored VWAP (resets on new trading session), replicating ta.vwap(hlc3)
const myVwap = series_of(null);
{
	let mySumPV = 0;
	let mySumVol = 0;
	let myPrevSession = null;

	for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
		const mySessionId = bar_at(time[myIndex]).session;

		if (mySessionId !== myPrevSession) {
			mySumPV = 0;
			mySumVol = 0;
			myPrevSession = mySessionId;
		}

		const myHlc3 = (high[myIndex] + low[myIndex] + close[myIndex]) / 3;
		mySumPV += myHlc3 * volume[myIndex];
		mySumVol += volume[myIndex];

		myVwap[myIndex] = mySumVol > 0 ? mySumPV / mySumVol : myHlc3;
	}
}

// ---------------- TERMINATOR 2 STATE MACHINE ----------------
// Sequential logic translated as-is from the Pine Script state machine.
const myFireLongArr = series_of(false);
const myFireShortArr = series_of(false);
const myIsConfirmBarArr = series_of(false);
const myConfirmLongArr = series_of(false);
const myConfirmShortArr = series_of(false);
const myGoLongArr = series_of(false);
const myGoShortArr = series_of(false);
const myFireEventArr = series_of(false);
const myPositionArr = series_of(0);

{
	let myState = 0;
	let myCompHigh = null;
	let myCompLow = null;
	let myStallCount = 0;
	let myFireBar = null;
	let myFireLong = false;
	let myFireShort = false;
	let myPosition = 0; // emulates strategy.position_size == 0 check (one position at a time)

	for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
		const myOpen = open[myIndex];
		const myClose = close[myIndex];
		const myHigh = high[myIndex];
		const myLow = low[myIndex];
		const myAtrValue = myAtr[myIndex];

		const myBarRange = myHigh - myLow;
		const myBody = Math.abs(myClose - myOpen);
		const myBodyFrac = myBarRange > 0 ? myBody / myBarRange : 0;

		const myStrongUp = myClose > myOpen && myBarRange > myAtrValue * myImpulseMult;
		const myStrongDown = myClose < myOpen && myBarRange > myAtrValue * myImpulseMult;

		if (myState === 0 && (myStrongUp || myStrongDown)) {
			myState = 1;
			myStallCount = 0;
			myCompHigh = null;
			myCompLow = null;
		}

		const mySmallCandle = myBarRange < myAtrValue * myCompressPct;

		if (myState === 1 && mySmallCandle) {
			myState = 2;
			myStallCount = 1;
			myCompHigh = myHigh;
			myCompLow = myLow;
		}

		if (myState === 2 && mySmallCandle) {
			myStallCount += 1;
			myCompHigh = Math.max(myCompHigh, myHigh);
			myCompLow = Math.min(myCompLow, myLow);
		}

		const myValidComp = myState === 2 && myStallCount >= myStallBars;
		const myBullBreak = myValidComp && myCompHigh !== null && myClose > myCompHigh;
		const myBearBreak = myValidComp && myCompLow !== null && myClose < myCompLow;
		const myBreakClean = myBodyFrac >= myMinBodyFrac;
		const myFire = (myBullBreak || myBearBreak) && myBreakClean;

		if (myFire) {
			myFireLong = myBullBreak;
			myFireShort = myBearBreak;
			myFireBar = myIndex;
			myState = 0;
			myStallCount = 0;
			myCompHigh = null;
			myCompLow = null;
		}

		if (myState !== 0 && myStallCount > 15) {
			myState = 0;
			myStallCount = 0;
			myCompHigh = null;
			myCompLow = null;
		}

		// Confirmation candle: bar immediately after fireBar
		const myIsConfirmBar = myFireBar !== null && myIndex === myFireBar + 1;
		const myConfirmLong = myIsConfirmBar && myFireLong && myClose > myOpen;
		const myConfirmShort = myIsConfirmBar && myFireShort && myClose < myOpen;

		// PEM filters
		const myFilterLong = myClose > myEmaSlow[myIndex] && myClose > myVwap[myIndex];
		const myFilterShort = myClose < myEmaSlow[myIndex] && myClose < myVwap[myIndex];

		const myGoLong = myConfirmLong && myFilterLong && myPosition === 0;
		const myGoShort = myConfirmShort && myFilterShort && myPosition === 0;

		if (myGoLong) {
			myPosition = 1;
		}
		else if (myGoShort) {
			myPosition = -1;
		}

		myFireLongArr[myIndex] = myFireLong;
		myFireShortArr[myIndex] = myFireShort;
		myIsConfirmBarArr[myIndex] = myIsConfirmBar;
		myConfirmLongArr[myIndex] = myConfirmLong;
		myConfirmShortArr[myIndex] = myConfirmShort;
		myGoLongArr[myIndex] = myGoLong;
		myGoShortArr[myIndex] = myGoShort;
		myFireEventArr[myIndex] = myFire;
		myPositionArr[myIndex] = myPosition;
	}
}

// ---------------- VISUALS ----------------
paint(myEmaFast, { name: 'EMAFast', color: '#2962FF', thickness: 1 });
paint(myEmaSlow, { name: 'EMASlow', color: '#2EBD85', thickness: 2 });
paint(myVwap, { name: 'VWAP', color: '#FF9800', thickness: 1 });

const myLongMarkers = for_every(myGoLongArr, low, (_g, _l) => _g ? constants.icons.triangle_up : null);
const myShortMarkers = for_every(myGoShortArr, high, (_g, _h) => _g ? constants.icons.triangle_down : null);

paint(myLongMarkers, { style: 'labels_below', color: '#00E676', name: 'LongEntry' });
paint(myShortMarkers, { style: 'labels_above', color: '#FF1744', name: 'ShortEntry' });

// ---------------- SIGNALS (for scanner / alerts / backtest) ----------------
register_signal(myGoLongArr, 'PEM Long Signal');
register_signal(myGoShortArr, 'PEM Short Signal');
register_signal(myFireEventArr, 'Terminator2 Fire');
register_signal(myConfirmLongArr, 'Confirm Long Candle');
register_signal(myConfirmShortArr, 'Confirm Short Candle');