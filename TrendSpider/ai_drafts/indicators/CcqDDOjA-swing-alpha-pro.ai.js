describe_indicator('Swing Alpha Pro', 'price');

// ===================== INPUTS =====================
const signalTab = input.tab('Signal Logic');
const myAtrSens = signalTab.number('Signal Sensitivity', 1.2, { min: 0.1, max: 10, step: 0.1 });
const myAtrPeriod = signalTab.number('ATR Period', 10, { min: 1, max: 100 });

const ribbonTab = input.tab('Swing Alpha Ribbon');
const myRibbonLen = ribbonTab.number('Channel Length', 34, { min: 1, max: 300 });
const myMultTop = ribbonTab.number('Upper Band Distance', 3.0, { min: 0.1, max: 20, step: 0.1 });
const myMultBot = ribbonTab.number('Lower Band Distance', 3.0, { min: 0.1, max: 20, step: 0.1 });
const myBandWidth = ribbonTab.number('Band Thickness', 1.2, { min: 0.1, max: 20, step: 0.1 });

const tpTab = input.tab('Take Profit Settings');
const myUseTP = tpTab.boolean('Show TP Targets', true);
const myTpRatio1 = tpTab.number('TP 1 Multiplier', 1.2, { min: 0.1, max: 20, step: 0.1 });
const myTpRatio2 = tpTab.number('TP 2 Multiplier', 2.2, { min: 0.1, max: 20, step: 0.1 });

// ===================== CHANNEL / RIBBON =====================
const myBaseMa = ema(close, myRibbonLen);
const myAtr14 = atr(high, low, close, 14);

const myTopOuter = add(myBaseMa, mult(myAtr14, myMultTop));
const myTopInner = sub(myTopOuter, mult(myAtr14, myBandWidth));

const myBotOuter = sub(myBaseMa, mult(myAtr14, myMultBot));
const myBotInner = add(myBotOuter, mult(myAtr14, myBandWidth));

const myTopOuterPainted = paint(myTopOuter, { name: 'TopOuter', color: 'rgba(229,57,53,0.4)', thickness: 1 });
const myTopInnerPainted = paint(myTopInner, { name: 'TopInner', color: 'rgba(229,57,53,0.2)', thickness: 1 });
const myBotInnerPainted = paint(myBotInner, { name: 'BotInner', color: 'rgba(0,200,83,0.2)', thickness: 1 });
const myBotOuterPainted = paint(myBotOuter, { name: 'BotOuter', color: 'rgba(0,200,83,0.4)', thickness: 1 });

fill(myTopOuterPainted, myTopInnerPainted, '#E53935', 0.3, 'Upper Resistance Ribbon');
fill(myBotInnerPainted, myBotOuterPainted, '#00C853', 0.3, 'Lower Support Ribbon');

// ===================== UT BOT CORE LOGIC =====================
// Note: this part is inherently sequential (recursive state), so a plain
// loop is used instead of indicator functions, as required.
const myXatr = atr(high, low, close, myAtrPeriod);
const myNloss = mult(myXatr, myAtrSens);

const myTrailingStop = series_of(0);
const myPos = series_of(0);
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevStop = myIndex > 0 ? (myTrailingStop[myIndex - 1] || 0) : 0;
	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : close[myIndex];
	const myCurrClose = close[myIndex];
	const myCurrNloss = myNloss[myIndex] || 0;

	let myStopValue;
	if (myCurrClose > myPrevStop && myPrevClose > myPrevStop) {
		myStopValue = Math.max(myPrevStop, myCurrClose - myCurrNloss);
	}
	else if (myCurrClose < myPrevStop && myPrevClose < myPrevStop) {
		myStopValue = Math.min(myPrevStop, myCurrClose + myCurrNloss);
	}
	else if (myCurrClose > myPrevStop) {
		myStopValue = myCurrClose - myCurrNloss;
	}
	else {
		myStopValue = myCurrClose + myCurrNloss;
	}
	myTrailingStop[myIndex] = myStopValue;

	const myPrevPos = myIndex > 0 ? (myPos[myIndex - 1] || 0) : 0;
	let myPosValue;
	if (myPrevClose < myPrevStop && myCurrClose > myStopValue) {
		myPosValue = 1;
	}
	else if (myPrevClose > myPrevStop && myCurrClose < myStopValue) {
		myPosValue = -1;
	}
	else {
		myPosValue = myPrevPos;
	}
	myPos[myIndex] = myPosValue;

	myBuySignal[myIndex] = myPosValue == 1 && myPrevPos != 1;
	mySellSignal[myIndex] = myPosValue == -1 && myPrevPos != -1;
}

// ===================== TAKE PROFIT TRACKING =====================
const myTp1HitSeries = series_of(false);
const myTp2HitSeries = series_of(false);

let myEntryPrice = null;
let myTp1Level = null;
let myTp2Level = null;
let myTradeDir = 0;
let myTp1Hit = false;
let myTp2Hit = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myBuySignal[myIndex]) {
		myEntryPrice = close[myIndex];
		myTradeDir = 1;
		myTp1Level = myEntryPrice + (myXatr[myIndex] * myTpRatio1);
		myTp2Level = myEntryPrice + (myXatr[myIndex] * myTpRatio2);
		myTp1Hit = false;
		myTp2Hit = false;
	}
	if (mySellSignal[myIndex]) {
		myEntryPrice = close[myIndex];
		myTradeDir = -1;
		myTp1Level = myEntryPrice - (myXatr[myIndex] * myTpRatio1);
		myTp2Level = myEntryPrice - (myXatr[myIndex] * myTpRatio2);
		myTp1Hit = false;
		myTp2Hit = false;
	}

	const myHitTP1 = myUseTP && myTradeDir == 1 && !myTp1Hit && high[myIndex] >= myTp1Level;
	const myHitTP2 = myUseTP && myTradeDir == 1 && myTp1Hit && !myTp2Hit && high[myIndex] >= myTp2Level;
	const myHitSellTP1 = myUseTP && myTradeDir == -1 && !myTp1Hit && low[myIndex] <= myTp1Level;
	const myHitSellTP2 = myUseTP && myTradeDir == -1 && myTp1Hit && !myTp2Hit && low[myIndex] <= myTp2Level;

	if (myHitTP1 || myHitSellTP1) {
		myTp1Hit = true;
	}
	if (myHitTP2 || myHitSellTP2) {
		myTp2Hit = true;
	}

	myTp1HitSeries[myIndex] = myHitTP1 || myHitSellTP1;
	myTp2HitSeries[myIndex] = myHitTP2 || myHitSellTP2;
}

// ===================== LABELS =====================
const myBuyLabelSeries = for_every(close, low, myBuySignal, (_c, _l, _b) => _b ? _l : null);
const mySellLabelSeries = for_every(close, high, mySellSignal, (_c, _h, _s) => _s ? _h : null);
const myTpHitLabelSeries = for_every(close, (myTp1HitSeries), myTp2HitSeries, (_c, _tp1, _tp2) => (_tp1 || _tp2) ? _c : null);

paint(myBuyLabelSeries, { name: 'BuySignal', style: 'labels_below', color: '#00C853' });
paint(mySellLabelSeries, { name: 'SellSignal', style: 'labels_above', color: '#E53935' });
paint(myTpHitLabelSeries, { name: 'TPHit', style: 'labels_above', color: '#FFC107' });

// ===================== SCANNER / STRATEGY SIGNALS =====================
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(myTp1HitSeries, 'TP1 Hit');
register_signal(myTp2HitSeries, 'TP2 Hit');