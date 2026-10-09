describe_indicator('ADR AsianLS Signals', 'price');

// NOTE: This indicator approximates a TradingView strategy script.
// TrendSpider Custom JS API has no concept of broker-side strategy
// entries/exits (strategy.entry/strategy.exit), boxes or labels with
// multi-line auto adjusting position like Pine. Also, there is no way
// to force a fixed GMT-3 timezone session detector like Pine's time()
// function with a custom timezone string, so session hours are derived
// manually from the UTC timestamp shifted by -3 hours.
// This script reproduces the core detection logic (Asia session range,
// body% filter, breakout entry condition, one trade per session) and
// exposes Buy/Sell markers plus register_signal() outputs for scanning,
// alerts and backtesting. SL/TP/trailing exit logic is not reproduced
// since there is no strategy execution engine available here.

const myBodyThresholdTab = input.tab('Settings');
const myBodyThreshold = myBodyThresholdTab.number('Min Body %', 65, { min: 0, max: 100 });
const mySlOffset = myBodyThresholdTab.number('SL Offset', 10, { min: 0, max: 10000 });
const myTp1Pips = myBodyThresholdTab.number('TP1 Offset', 10, { min: 0, max: 10000 });
const myTp2Pips = myBodyThresholdTab.number('TP2 Offset', 20, { min: 0, max: 10000 });

// Derive GMT-3 hour/minute for every candle, from UTC unix timestamp.
const myGmt3Minutes = time.map(_t => {
	const myShifted = _t - 3 * 3600;
	const mySecondsOfDay = ((myShifted % 86400) + 86400) % 86400;
	return Math.floor(mySecondsOfDay / 60);
});

// Asia session: 19:00 to 24:00 (GMT-3)
const myInSession = myGmt3Minutes.map(_m => _m >= 19 * 60 && _m < 24 * 60);

// Trade window: 00:00 to 12:00 (GMT-3)
const myInTradeWindow = myGmt3Minutes.map(_m => _m >= 0 && _m < 12 * 60);

const mySessionHigh = series_of(null);
const mySessionLow = series_of(null);
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const myEntryMarker = series_of(null);
const myExitLevelsBuy = series_of(null);
const myExitLevelsSell = series_of(null);

let myCurrentHigh = null;
let myCurrentLow = null;
let myTradesToday = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myNewAsia = myInSession[myIndex] && !(myIndex > 0 && myInSession[myIndex - 1]);

	if (myNewAsia) {
		myCurrentHigh = high[myIndex];
		myCurrentLow = low[myIndex];
		myTradesToday = 0;
	}
	else if (myInSession[myIndex]) {
		myCurrentHigh = myCurrentHigh === null ? high[myIndex] : Math.max(myCurrentHigh, high[myIndex]);
		myCurrentLow = myCurrentLow === null ? low[myIndex] : Math.min(myCurrentLow, low[myIndex]);
	}

	mySessionHigh[myIndex] = myCurrentHigh;
	mySessionLow[myIndex] = myCurrentLow;

	const myRangeCandle = high[myIndex] - low[myIndex];
	const myBodyCandle = Math.abs(close[myIndex] - open[myIndex]);
	const myBodyPercent = (myBodyCandle / (myRangeCandle > 0 ? myRangeCandle : 1)) * 100;
	const myIsBodyCandle = myBodyPercent >= myBodyThreshold;

	const myCanTrade = !myInSession[myIndex] && myInTradeWindow[myIndex] && myTradesToday < 1 && myCurrentHigh !== null && myCurrentLow !== null;

	const myLongCond = myCanTrade && close[myIndex] > myCurrentHigh && open[myIndex] < close[myIndex] && myIsBodyCandle;
	const myShortCond = myCanTrade && close[myIndex] < myCurrentLow && open[myIndex] > close[myIndex] && myIsBodyCandle;

	if (myLongCond) {
		myTradesToday = 1;
		myLongSignal[myIndex] = true;
		myEntryMarker[myIndex] = constants.icons.triangle_up;
		myExitLevelsBuy[myIndex] = close[myIndex];
	}
	else if (myShortCond) {
		myTradesToday = 1;
		myShortSignal[myIndex] = true;
		myEntryMarker[myIndex] = constants.icons.triangle_down;
		myExitLevelsSell[myIndex] = close[myIndex];
	}
}

paint(mySessionHigh, { name: 'Asia Session High', color: '#9e9e9e', style: 'ladder' });
paint(mySessionLow, { name: 'Asia Session Low', color: '#9e9e9e', style: 'ladder' });

const myBuyMarks = for_every(myLongSignal, low, (_s, _l) => _s ? _l : null);
const mySellMarks = for_every(myShortSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: '#00c853' });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: '#d50000' });

register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');