describe_indicator('Ichimoku ATR Chikou V4', 'price');

const myIchimokuTab = input.tab('Ichimoku');
const myTenkanBars = myIchimokuTab.number('Tenkan Sen Bars', 9, { min: 1, max: 200 });
const myKijunBars = myIchimokuTab.number('Kijun Sen Bars', 26, { min: 1, max: 400 });
const mySenkouBBars = myIchimokuTab.number('Senkou Span B Bars', 52, { min: 1, max: 600 });

const myRow1 = myIchimokuTab.row();
const myChikouOffset = myRow1.number('Chikou Span Offset', 26, { min: 1, max: 400 });
const mySenkouOffset = myRow1.number('Senkou Span Offset', 26, { min: 1, max: 400 });

const myAtrTab = input.tab('ATR Model');
const myAtrLength = myAtrTab.number('ATR Length', 14, { min: 1, max: 200 });
// Shortened title to fix "input(): name is too lengthy" error
const myAtrMult = myAtrTab.number('ATR Mult Activation', 1.5, { min: 0.1, max: 20, step: 0.1 });

// Ichimoku core lines
const myTenkan = div(add(highest(high, myTenkanBars), lowest(low, myTenkanBars)), 2);
const myKijun = div(add(highest(high, myKijunBars), lowest(low, myKijunBars)), 2);
const mySenkouA = div(add(myTenkan, myKijun), 2);
const mySenkouB = div(add(highest(high, mySenkouBBars), lowest(low, mySenkouBBars)), 2);

const myAtrValue = atr(high, low, close, myAtrLength);

// Shifted senkou values used for the breakout condition (ss_offset-1 bars back)
const mySenkouAShiftedBack = shift(mySenkouA, mySenkouOffset - 1);
const mySenkouBShiftedBack = shift(mySenkouB, mySenkouOffset - 1);
const mySsHigh = max_of(mySenkouAShiftedBack, mySenkouBShiftedBack);
const mySsLow = min_of(mySenkouAShiftedBack, mySenkouBShiftedBack);

const myMomentum = momentum(close, myChikouOffset - 1);
const myPriceLookback = shift(close, myChikouOffset - 1);

const myBullish = for_every(
	myTenkan, myKijun, myMomentum, close, mySsHigh,
	(_tenkan, _kijun, _mom, _close, _ssHigh) => _tenkan > _kijun && _mom > 0 && _close > _ssHigh
);

const myBearish = for_every(
	myTenkan, myKijun, myMomentum, close, mySsLow,
	(_tenkan, _kijun, _mom, _close, _ssLow) => _tenkan < _kijun && _mom < 0 && _close < _ssLow
);

// Chikou "cross" of close vs price_lookback
const myDiff = sub(close, myPriceLookback);
const myDiffPrev = shift(myDiff, 1);
const myChikouTouch = for_every(
	myDiff, myDiffPrev,
	(_d, _dPrev) => _dPrev != null && _d != null && ((_dPrev <= 0 && _d > 0) || (_dPrev >= 0 && _d < 0))
);

// --- Path dependent strategy state simulation (plain loop, no indicator calls inside) ---
// NOTE: this indicator approximates the Pine strategy logic. TrendSpider
// Custom JS does not have a broker/order-fill simulator like Pine Script
// strategies (strategy.entry/strategy.close execute with a fill delay in
// Pine). Here all entries/exits are approximated as happening on the SAME
// bar the signal fires (no 1-bar fill delay), and position state is
// re-built bar by bar in a plain loop. Treat exact bar-by-bar PnL numbers
// as an approximation, not an exact 1:1 match to the Pine backtester.
const myCandleCount = close.length;
const myPosition = series_of(0);
const myEntryPrice = series_of(0);
const myChikouActive = series_of(false);
const myActivationLevel = series_of(null);
const myIsNewEntry = series_of(false);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

let myPos = 0;
let myEntry = 0;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myClose = close[myIndex];
	const myAtr = myAtrValue[myIndex];
	const myIsBullish = myBullish[myIndex];
	const myIsBearish = myBearish[myIndex];
	const myIsTouch = myChikouTouch[myIndex];

	let myProfitPoints = 0;
	if (myPos > 0) {
		myProfitPoints = myClose - myEntry;
	}
	else if (myPos < 0) {
		myProfitPoints = myEntry - myClose;
	}

	const myIsChikouActive = (myAtr != null) && myProfitPoints > (myAtr * myAtrMult);

	let myNewEntry = false;
	let myLongExit = false;
	let myShortExit = false;
	let myLongEntry = false;
	let myShortEntry = false;

	// Exits (Chikou based or original cross-based)
	if (myPos > 0 && myIsChikouActive && myIsTouch) {
		myLongExit = true;
		myPos = 0;
	}
	else if (myPos > 0 && myIsBearish) {
		myLongExit = true;
		myPos = 0;
	}
	else if (myPos < 0 && myIsChikouActive && myIsTouch) {
		myShortExit = true;
		myPos = 0;
	}
	else if (myPos < 0 && myIsBearish === false && myIsBullish) {
		myShortExit = true;
		myPos = 0;
	}

	// Entries (only when flat)
	if (myPos === 0 && myIsBullish) {
		myPos = 1;
		myEntry = myClose;
		myNewEntry = true;
		myLongEntry = true;
	}
	else if (myPos === 0 && myIsBearish) {
		myPos = -1;
		myEntry = myClose;
		myNewEntry = true;
		myShortEntry = true;
	}

	myPosition[myIndex] = myPos;
	myEntryPrice[myIndex] = myEntry;
	myChikouActive[myIndex] = myIsChikouActive;
	myIsNewEntry[myIndex] = myNewEntry;
	myLongEntrySignal[myIndex] = myLongEntry;
	myShortEntrySignal[myIndex] = myShortEntry;
	myLongExitSignal[myIndex] = myLongExit;
	myShortExitSignal[myIndex] = myShortExit;

	if (myNewEntry) {
		myActivationLevel[myIndex] = myPos > 0 ? (myEntry + myAtr * myAtrMult) : (myEntry - myAtr * myAtrMult);
	}
}

// --- Visualization ---
paint(myTenkan, { name: 'TenkanSen', color: '#0496ff', thickness: 1 });
paint(myKijun, { name: 'KijunSen', color: '#991515', thickness: 2 });

const mySenkouAPainted = paint(shift(mySenkouA, mySenkouOffset - 1), { name: 'SenkouA', color: 'rgba(0,170,0,0.6)', thickness: 1 });
const mySenkouBPainted = paint(shift(mySenkouB, mySenkouOffset - 1), { name: 'SenkouB', color: 'rgba(170,0,0,0.6)', thickness: 1 });

color_cloud(
	shift(mySenkouA, mySenkouOffset - 1),
	shift(mySenkouB, mySenkouOffset - 1),
	'#2ca599',
	'#ee5451',
	'KumoBull',
	'KumoBear',
	0.2
);

const myChikouColor = for_every(myChikouActive, _active => _active ? '#32cd32' : '#ffcdd2');
paint(myPriceLookback, { name: 'ChikouRef', color: myChikouColor, thickness: 2 });
paint(myActivationLevel, { name: 'AtrCross', style: 'dotted', color: 'white', thickness: 4 });

// --- Scanner / Alert / Strategy Tester signals ---
register_signal(myBullish, 'Bullish Setup');
register_signal(myBearish, 'Bearish Setup');
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');