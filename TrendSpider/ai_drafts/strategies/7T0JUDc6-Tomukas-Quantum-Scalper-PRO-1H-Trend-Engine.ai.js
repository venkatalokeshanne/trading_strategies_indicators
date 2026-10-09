describe_indicator('Tomukas Premium Signals Only', 'price');

// NOTE: Custom JS indicators can't manage strategy state (position
// size, average price, pyramiding, SL/TP, trailing stops). Only the
// Long/Short entry conditions from the Pine script are reproduced
// here as signals (usable in Scanner/Alerts/Strategy Tester) and as
// on-chart labels. Exit logic (ATR based stop/limit/trail) is not
// expressible and is therefore omitted.

const emaTab = input.tab('EMA Lengths');
const emaRow1 = emaTab.row();
const myFastEMA = emaRow1.number('EMA Fast', 3, { min: 1, max: 500 });
const mySlowEMA = emaRow1.number('EMA Slow', 6, { min: 1, max: 500 });
const emaRow2 = emaTab.row();
const myPullEMA = emaRow2.number('Pullback EMA', 25, { min: 1, max: 500 });
const myTrendEMA = emaRow2.number('Trend EMA', 50, { min: 1, max: 500 });
const myMacroEMA = emaTab.number('Macro EMA', 200, { min: 1, max: 500 });

const momentumTab = input.tab('Momentum / Trend Strength');
const myRsiLen = momentumTab.number('RSI Length', 14, { min: 1, max: 200 });
const rsiRow = momentumTab.row();
const myRsiBuy = rsiRow.number('RSI Buy Above', 55, { min: 1, max: 99 });
const myRsiSell = rsiRow.number('RSI Sell Below', 45, { min: 1, max: 99 });
const myAdxLen = momentumTab.number('ADX Length', 14, { min: 1, max: 200 });
const myAdxMin = momentumTab.number('Min ADX', 22.0, { min: 0, max: 100, step: 0.1 });

const volTab = input.tab('Volume Filter');
const myVolLen = volTab.number('Volume MA', 20, { min: 1, max: 500 });
const myUseVol = volTab.boolean('Use Volume Filter', true);

// ---- Core series ----
const myEma3 = ema(close, myFastEMA);
const myEma6 = ema(close, mySlowEMA);
const myEma25 = ema(close, myPullEMA);
const myEma50 = ema(close, myTrendEMA);
const myEma200 = ema(close, myMacroEMA);

// MACD(12,26,9), computed manually since no dedicated macd() builtin exists.
const myMacdLine = sub(ema(close, 12), ema(close, 26));
const mySignalLine = ema(myMacdLine, 9);

const myRsi = rsi(close, myRsiLen);
const myAtr = atr(high, low, close, myAdxLen);
const myVolMA = sma(volume, myVolLen);

// ADX / DMI
const myAdxObject = indicators.adx(myAdxLen);

// ---- Helper: crossover / crossunder as boolean series ----
function myCrossOver(mySeriesA, mySeriesB) {
	return for_every(mySeriesA, mySeriesB, (_a, _b, _prev, _i) =>
		_i > 0 && _a > _b && mySeriesA[_i - 1] <= mySeriesB[_i - 1]
	);
}
function myCrossUnder(mySeriesA, mySeriesB) {
	return for_every(mySeriesA, mySeriesB, (_a, _b, _prev, _i) =>
		_i > 0 && _a < _b && mySeriesA[_i - 1] >= mySeriesB[_i - 1]
	);
}
function myAndAll(mySeriesArray) {
	return mySeriesArray.reduce((_acc, _cur) => for_every(_acc, _cur, (_x, _y) => Boolean(_x) && Boolean(_y)));
}

// ---- Conditions ----
const myVolOk = myUseVol
	? for_every(volume, myVolMA, (_v, _vma) => _v > _vma)
	: series_of(true);

const myBullTrend = for_every(close, myEma50, myEma200, (_c, _e50, _e200) => _c > _e50 && _e50 > _e200);
const myBearTrend = for_every(close, myEma50, myEma200, (_c, _e50, _e200) => _c < _e50 && _e50 < _e200);

const myLongPullback = for_every(low, myEma25, myEma50, (_l, _e25, _e50) => _l <= _e25 || _l <= _e50);
const myShortPullback = for_every(high, myEma25, myEma50, (_h, _e25, _e50) => _h >= _e25 || _h >= _e50);

const myEmaCrossOver = myCrossOver(myEma3, myEma6);
const myEmaCrossUnder = myCrossUnder(myEma3, myEma6);
const myMacdCrossOver = myCrossOver(myMacdLine, mySignalLine);
const myMacdCrossUnder = myCrossUnder(myMacdLine, mySignalLine);

const myRsiAboveBuy = for_every(myRsi, _r => _r > myRsiBuy);
const myRsiBelowSell = for_every(myRsi, _r => _r < myRsiSell);

const myDiPlusAboveMinus = for_every(myAdxObject.dmiPlus, myAdxObject.dmiMinus, (_p, _m) => _p > _m);
const myDiMinusAbovePlus = for_every(myAdxObject.dmiMinus, myAdxObject.dmiPlus, (_m, _p) => _m > _p);
const myAdxAboveMin = for_every(myAdxObject.adx, _a => _a > myAdxMin);

const myLongSignal = myAndAll([
	myBullTrend,
	myLongPullback,
	myEmaCrossOver,
	myMacdCrossOver,
	myRsiAboveBuy,
	myDiPlusAboveMinus,
	myAdxAboveMin,
	myVolOk
]);

const myShortSignal = myAndAll([
	myBearTrend,
	myShortPullback,
	myEmaCrossUnder,
	myMacdCrossUnder,
	myRsiBelowSell,
	myDiMinusAbovePlus,
	myAdxAboveMin,
	myVolOk
]);

// ---- Register scanning / strategy signals ----
register_signal(myLongSignal, 'Long Signal');
register_signal(myShortSignal, 'Short Signal');
register_signal(myBullTrend, 'Bull Trend');
register_signal(myBearTrend, 'Bear Trend');

// ---- Visuals: BUY/SELL labels ----
const myBuyMarks = for_every(myLongSignal, _s => _s ? constants.icons.triangle_up : null);
const mySellMarks = for_every(myShortSignal, _s => _s ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: '#00FFD1' });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: '#FF00AA' });

// Approximates Pine's bgcolor() by tinting candle colors for trend
// state, since there is no background-fill function available.
const myTrendColors = for_every(myBullTrend, myBearTrend, (_bull, _bear) =>
	_bull ? '#00FFD1' : (_bear ? '#FF00AA' : null)
);
color_candles(myTrendColors);