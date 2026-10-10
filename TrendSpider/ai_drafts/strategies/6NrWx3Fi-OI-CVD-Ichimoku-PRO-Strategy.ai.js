// ⚠️ EXPERIMENTAL CONVERSION NOTICE ⚠️
// This indicator reproduces the Pine Script strategy's ENTRY LOGIC
// (EMA cross + Order Flow/Ichimoku filter) as closely as the TrendSpider
// Custom JS API allows. Important differences vs the original Pine script
// are explained in the warnings block that follows this code.
describe_indicator('OI CVD Ichimoku PRO Signals', 'price');

// --- EMA settings ---
const emaTab = input.tab('EMA Settings');
const myLen1 = emaTab.number('EMA 1 Fast', 13, { min: 1, max: 500 });
const myLen2 = emaTab.number('EMA 2 Slow', 25, { min: 1, max: 500 });

// --- Order Flow settings ---
const ofTab = input.tab('Order Flow Settings');
const myOiThresh = ofTab.number('OI Min Change Threshold', 0, { min: 0, max: 1000000 });
const myCvdLen = ofTab.number('CVD Smoothing Period', 14, { min: 1, max: 200 });

// --- Ichimoku settings ---
const ichiTab = input.tab('Ichimoku Settings');
const myUseIchimokuFilter = ichiTab.boolean('Use Ichimoku Cloud as trend filter', true);
const myTenkanLen = ichiTab.number('Tenkan sen Length', 9, { min: 1, max: 200 });
const myKijunLen = ichiTab.number('Kijun sen Length', 26, { min: 1, max: 200 });
const mySenkouBLen = ichiTab.number('Senkou Span B Length', 52, { min: 1, max: 300 });
const myDisplacement = ichiTab.number('Cloud Displacement', 26, { min: 1, max: 100 });

// --- Stop Loss settings ---
const slTab = input.tab('Stop Loss Settings');
const myUseAtrSl = slTab.boolean('Use ATR for SL', true);
const mySlFixedPercent = slTab.number('Fixed SL Percent', 1.5, { min: 0.1, max: 50 });
const mySlAtrMult = slTab.number('ATR Multiplier for SL', 1.5, { min: 0.1, max: 20 });

// --- Take Profit settings ---
const tpTab = input.tab('Take Profit Settings');
const myTpCount = tpTab.number('Number of TPs', 2, { min: 1, max: 2 });
const myTp1Mult = tpTab.number('TP1 ATR Multiplier', 1.5, { min: 0.1, max: 20 });
const myTp2Mult = tpTab.number('TP2 ATR Multiplier', 3.0, { min: 0.1, max: 20 });

// --- Core calculations ---
const myEma1 = ema(close, myLen1);
const myEma2 = ema(close, myLen2);
const myAtr = atr(high, low, close, 14);

// Open Interest data (OI) is not available via the Custom JS API, so the
// "oid" input of the original script is approximated as always 0. This
// means the "filter_bullish/bearish" condition below relies on CVD only.
const myOid = series_of(0);

// CVD approximation: volume signed by candle direction, then EMA-smoothed
const mySignedVolume = for_every(close, open, volume, (_c, _o, _v) => (_c > _o ? _v : -_v));
const myCvd = ema(mySignedVolume, myCvdLen);

// --- Ichimoku calculations ---
const myTenkan = div(add(highest(high, myTenkanLen), lowest(low, myTenkanLen)), 2);
const myKijun = div(add(highest(high, myKijunLen), lowest(low, myKijunLen)), 2);
const mySenkouA = div(add(myTenkan, myKijun), 2);
const mySenkouB = div(add(highest(high, mySenkouBLen), lowest(low, mySenkouBLen)), 2);

// The cloud actually visible "now" was computed `displacement` bars ago
const mySenkouAShifted = shift(mySenkouA, myDisplacement);
const mySenkouBShifted = shift(mySenkouB, myDisplacement);
const myCloudTopNow = max_of(mySenkouAShifted, mySenkouBShifted);
const myCloudBotNow = min_of(mySenkouAShifted, mySenkouBShifted);

// --- Sequential pass to compute signals and SL/TP levels (stateful logic) ---
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const mySlLevel = series_of(null);
const myTp1Level = series_of(null);
const myTp2Level = series_of(null);
const myPositionDirection = series_of(0);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myIchimokuBullish = !myUseIchimokuFilter || close[myIndex] > myCloudTopNow[myIndex];
	const myIchimokuBearish = !myUseIchimokuFilter || close[myIndex] < myCloudBotNow[myIndex];

	const myOidValue = myOid[myIndex] || 0;
	const myFilterBullish = (myOidValue > myOiThresh || myCvd[myIndex] > 0) && myIchimokuBullish;
	const myFilterBearish = (myOidValue < -myOiThresh || myCvd[myIndex] < 0) && myIchimokuBearish;

	const myCrossover = myEma1[myIndex] > myEma2[myIndex] && myEma1[myIndex - 1] <= myEma2[myIndex - 1];
	const myCrossunder = myEma1[myIndex] < myEma2[myIndex] && myEma1[myIndex - 1] >= myEma2[myIndex - 1];

	const myLongCondition = myCrossover && myFilterBullish;
	const myShortCondition = myCrossunder && myFilterBearish;

	myLongSignal[myIndex] = myLongCondition;
	myShortSignal[myIndex] = myShortCondition;

	// carry forward previous levels/position by default
	mySlLevel[myIndex] = mySlLevel[myIndex - 1];
	myTp1Level[myIndex] = myTp1Level[myIndex - 1];
	myTp2Level[myIndex] = myTp2Level[myIndex - 1];
	myPositionDirection[myIndex] = myPositionDirection[myIndex - 1];

	if (myLongCondition) {
		mySlLevel[myIndex] = myUseAtrSl
			? close[myIndex] - myAtr[myIndex] * mySlAtrMult
			: close[myIndex] - close[myIndex] * (mySlFixedPercent / 100);
		myTp1Level[myIndex] = close[myIndex] + myAtr[myIndex] * myTp1Mult;
		myTp2Level[myIndex] = close[myIndex] + myAtr[myIndex] * myTp2Mult;
		myPositionDirection[myIndex] = 1;
	}

	if (myShortCondition) {
		mySlLevel[myIndex] = myUseAtrSl
			? close[myIndex] + myAtr[myIndex] * mySlAtrMult
			: close[myIndex] + close[myIndex] * (mySlFixedPercent / 100);
		myTp1Level[myIndex] = close[myIndex] - myAtr[myIndex] * myTp1Mult;
		myTp2Level[myIndex] = close[myIndex] - myAtr[myIndex] * myTp2Mult;
		myPositionDirection[myIndex] = -1;
	}
}

// Only show levels while a position is conceptually "open" (direction != 0)
const mySlLevelDisplay = for_every(mySlLevel, myPositionDirection, (_sl, _pos) => (_pos !== 0 ? _sl : null));
const myTp1LevelDisplay = for_every(myTp1Level, myPositionDirection, (_tp1, _pos) => (_pos !== 0 ? _tp1 : null));
const myTp2LevelDisplay = for_every(myTp2Level, myPositionDirection, (_tp2, _pos) => (_pos !== 0 && myTpCount === 2 ? _tp2 : null));

// --- Visualization ---
const myEma1Painted = paint(myEma1, { name: 'EMA Fast', color: '#2962FF', thickness: 2 });
const myEma2Painted = paint(myEma2, { name: 'EMA Slow', color: '#D500F9', thickness: 2 });
fill(myEma1Painted, myEma2Painted, '#2962FF', 0.15);

const mySenkouAPainted = paint(mySenkouA, { name: 'Senkou Span A', color: '#26A69A', thickness: 1, style: 'dotted' });
const mySenkouBPainted = paint(mySenkouB, { name: 'Senkou Span B', color: '#EF5350', thickness: 1, style: 'dotted' });
fill(mySenkouAPainted, mySenkouBPainted, '#26A69A', 0.1);

paint(myTenkan, { name: 'Tenkan sen', color: '#FFA726', thickness: 1 });
paint(myKijun, { name: 'Kijun sen', color: '#003366', thickness: 1 });

paint(mySlLevelDisplay, { name: 'SL Level', color: 'red', thickness: 2, style: 'ladder' });
paint(myTp1LevelDisplay, { name: 'TP1 Level', color: 'green', thickness: 2, style: 'ladder' });
paint(myTp2LevelDisplay, { name: 'TP2 Level', color: 'olive', thickness: 2, style: 'ladder' });

// --- Signals for Scanners / Alerts / Backtests ---
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');