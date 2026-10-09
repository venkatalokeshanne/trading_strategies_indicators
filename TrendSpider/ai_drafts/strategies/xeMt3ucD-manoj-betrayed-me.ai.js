describe_indicator('Manoj Betrayed Me - SMMA Breakout Signals', 'price');

// NOTE: TrendSpider Custom JS indicators cannot place/manage actual
// broker orders (no strategy.entry/exit/cancel engine exists here).
// This script reproduces the Pine SIGNAL LOGIC exactly (SMMA bands,
// session filter, signal/confirmation candles) and exposes buy/sell
// signal and confirmation series via register_signal() so they can be
// used in Scanners, Alerts and the Strategy Tester. The actual trade
// management (stop/target/pyramiding/session close exit) from the
// Pine strategy cannot be replicated here; only the entry/stop/target
// price levels are computed and plotted as reference lines on the
// confirmation bar.

const myLen = input.number('SMMA Length', 20, { min: 1, max: 500 });
const myTargetMult = input.number('Target Multiplier', 2, { min: 0.1, max: 20 });
const mySessionStart = input.text('Session Start (HHMM)', '0915');
const mySessionEnd = input.text('Session End (HHMM)', '1530');

// Parse "HHMM" strings into hours/minutes
const myStartHour = parseInt(mySessionStart.slice(0, 2), 10);
const myStartMinute = parseInt(mySessionStart.slice(2, 4), 10);
const myEndHour = parseInt(mySessionEnd.slice(0, 2), 10);
const myEndMinute = parseInt(mySessionEnd.slice(2, 4), 10);

assert(!isNaN(myStartHour) && !isNaN(myStartMinute), 'Invalid session start time');
assert(!isNaN(myEndHour) && !isNaN(myEndMinute), 'Invalid session end time');

// SMMA (RMA) bands
const mySmmaHigh = wildma(high, myLen);
const mySmmaLow = wildma(low, myLen);

// Determine, per candle, whether its close time is within the session
// and whether it is the session close bar (>= session end time)
const myTimeInfo = time.map(_t => time_of(_t));
const myInSession = myTimeInfo.map(_info => {
	const myMinutesOfDay = _info.hours * 60 + _info.minutes;
	const myStartMinutesOfDay = myStartHour * 60 + myStartMinute;
	const myEndMinutesOfDay = myEndHour * 60 + myEndMinute;
	return myMinutesOfDay >= myStartMinutesOfDay && myMinutesOfDay <= myEndMinutesOfDay;
});

const myIsSessionCloseBar = myTimeInfo.map((_info, _i) => {
	const myCloseHour = _info.hours;
	const myCloseMinute = _info.minutes;
	const myAfterOrAtEnd = (myCloseHour > myEndHour) || (myCloseHour === myEndHour && myCloseMinute >= myEndMinute);
	return myInSession[_i] && myAfterOrAtEnd;
});

const myCanTrade = myInSession.map((_v, _i) => _v && !myIsSessionCloseBar[_i]);

// Step 1: Signal candle
const myBuySignal = for_every(close, mySmmaHigh, (_c, _s, _p, _idx) => myCanTrade[_idx] && _c > _s);
const mySellSignal = for_every(close, mySmmaLow, (_c, _s, _p, _idx) => myCanTrade[_idx] && _c < _s);

// Step 2: Confirmation candle (requires previous bar signal)
const myBuyConfirm = series_of(false);
const mySellConfirm = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myPrevBuySignal = myBuySignal[myIndex - 1];
	const myPrevSellSignal = mySellSignal[myIndex - 1];

	myBuyConfirm[myIndex] = Boolean(
		myCanTrade[myIndex] && myPrevBuySignal &&
		close[myIndex] > mySmmaHigh[myIndex] &&
		low[myIndex] > mySmmaHigh[myIndex]
	);

	mySellConfirm[myIndex] = Boolean(
		myCanTrade[myIndex] && myPrevSellSignal &&
		close[myIndex] < mySmmaLow[myIndex] &&
		high[myIndex] < mySmmaLow[myIndex]
	);
}

myBuyConfirm[0] = false;
mySellConfirm[0] = false;

// Reference entry/stop/target levels (informational only, plotted at confirmation bars)
const myBuyEntryLevel = series_of(null);
const myBuyStopLevel = series_of(null);
const myBuyTargetLevel = series_of(null);
const mySellEntryLevel = series_of(null);
const mySellStopLevel = series_of(null);
const mySellTargetLevel = series_of(null);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	if (myBuyConfirm[myIndex]) {
		const myConfirmHigh = high[myIndex];
		const myConfirmSize = high[myIndex] - low[myIndex];
		myBuyEntryLevel[myIndex] = myConfirmHigh;
		myBuyStopLevel[myIndex] = mySmmaLow[myIndex - 1];
		myBuyTargetLevel[myIndex] = myConfirmHigh + myTargetMult * myConfirmSize;
	}
	if (mySellConfirm[myIndex]) {
		const myConfirmLow = low[myIndex];
		const myConfirmSize = high[myIndex] - low[myIndex];
		mySellEntryLevel[myIndex] = myConfirmLow;
		mySellStopLevel[myIndex] = mySmmaHigh[myIndex - 1];
		mySellTargetLevel[myIndex] = myConfirmLow - myTargetMult * myConfirmSize;
	}
}

// Plot SMMA bands
paint(mySmmaHigh, { name: 'SMMA High', color: '#2ca599', thickness: 2 });
paint(mySmmaLow, { name: 'SMMA Low', color: '#ee5451', thickness: 2 });

// Visual markers for signal candles
const myBuySignalMarks = for_every(myBuySignal, _v => _v ? constants.icons.circle : null);
const mySellSignalMarks = for_every(mySellSignal, _v => _v ? constants.icons.circle : null);
paint(myBuySignalMarks, { name: 'Buy Signal Marker', style: 'labels_below', color: '#2ca599' });
paint(mySellSignalMarks, { name: 'Sell Signal Marker', style: 'labels_above', color: '#ee5451' });

// Visual markers for confirmation candles
const myBuyConfirmMarks = for_every(myBuyConfirm, _v => _v ? constants.icons.triangle_up : null);
const mySellConfirmMarks = for_every(mySellConfirm, _v => _v ? constants.icons.triangle_down : null);
paint(myBuyConfirmMarks, { name: 'Buy Confirmation Marker', style: 'labels_below', color: '#2ca599' });
paint(mySellConfirmMarks, { name: 'Sell Confirmation Marker', style: 'labels_above', color: '#ee5451' });

// Reference trade levels (price axis), only meaningful on confirmation bars
paint(myBuyEntryLevel, { name: 'Buy Entry Level', color: '#2ca599', style: 'dotted', forceUsePriceAxis: true });
paint(myBuyStopLevel, { name: 'Buy Stop Level', color: '#ee5451', style: 'dotted', forceUsePriceAxis: true });
paint(myBuyTargetLevel, { name: 'Buy Target Level', color: '#2ca599', style: 'dotted', forceUsePriceAxis: true });
paint(mySellEntryLevel, { name: 'Sell Entry Level', color: '#ee5451', style: 'dotted', forceUsePriceAxis: true });
paint(mySellStopLevel, { name: 'Sell Stop Level', color: '#2ca599', style: 'dotted', forceUsePriceAxis: true });
paint(mySellTargetLevel, { name: 'Sell Target Level', color: '#ee5451', style: 'dotted', forceUsePriceAxis: true });

// Signals for Scanners, Alerts and Strategy Tester
// Renamed to avoid name collisions with the paint() labels above,
// since all painted series and signals share the same naming space.
register_signal(myBuySignal, 'Buy Signal Raised');
register_signal(mySellSignal, 'Sell Signal Raised');
register_signal(myBuyConfirm, 'Buy Confirmation Signal');
register_signal(mySellConfirm, 'Sell Confirmation Signal');