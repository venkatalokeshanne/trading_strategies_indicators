describe_indicator('EMA RSLAIK Strategy Diario', 'price');

// Converted from the given Pine Script v5 strategy. This recreates the
// EMA21/EMA89 trend filter, RSI momentum filter and ATR volatility filter,
// and simulates the single-position entry/stop/take-profit logic since
// TrendSpider Custom JS has no native broker/strategy engine.

const myEma21 = ema(close, 21);
const myEma89 = ema(close, 89);
const myRsi = rsi(close, 14);
const myAtr = atr(high, low, close, 14);
const myAtrMa = sma(myAtr, 20);

// Entry conditions, computed per-candle (no loops over indicator calls)
const myTrendOk = for_every(myEma21, myEma89, close, (_e21, _e89, _c) => _e21 > _e89 && _c > _e21);
const myMomentumOk = for_every(myRsi, _r => _r >= 55 && _r <= 75);
const myVolatilityOk = for_every(myAtr, myAtrMa, (_a, _am) => _a > _am);
const myLongCondition = for_every(myTrendOk, myMomentumOk, myVolatilityOk, (_t, _m, _v) => _t && _m && _v);

// Simulate single-position state machine (no pyramiding, like the original
// strategy default). We assume the entry fills at the close of the signal
// bar (Pine's "barstate.isconfirmed" entry), and the stop/take-profit are
// checked against each subsequent bar's high/low.
const myLongEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myStopPrice = series_of(null);
const myTakeProfit = series_of(null);

let myInTrade = false;
let myEntryPrice = null;
let myStopLevel = null;
let myTakeLevel = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (!myInTrade) {
		if (myLongCondition[myIndex]) {
			myInTrade = true;
			myEntryPrice = close[myIndex];
			myStopLevel = myEntryPrice - myAtr[myIndex] * 2.5;
			myTakeLevel = myEntryPrice + myAtr[myIndex] * 4;
			myLongEntrySignal[myIndex] = true;
		}
	}
	else {
		// Risk management levels are recomputed each bar in the original
		// script (always using the current ATR), so we mirror that here.
		myStopLevel = myEntryPrice - myAtr[myIndex] * 2.5;
		myTakeLevel = myEntryPrice + myAtr[myIndex] * 4;

		const myHitStop = low[myIndex] <= myStopLevel;
		const myHitTake = high[myIndex] >= myTakeLevel;

		if (myHitStop || myHitTake) {
			myLongExitSignal[myIndex] = true;
			myInTrade = false;
			myEntryPrice = null;
			myStopLevel = null;
			myTakeLevel = null;
		}
	}

	myStopPrice[myIndex] = myStopLevel;
	myTakeProfit[myIndex] = myTakeLevel;
}

paint(myEma21, { name: 'EMA21', color: 'orange', thickness: 2 });
paint(myEma89, { name: 'EMA89', color: 'blue', thickness: 2 });
paint(myStopPrice, { name: 'StopPrice', color: 'red', style: 'dotted' });
paint(myTakeProfit, { name: 'TakeProfit', color: 'green', style: 'dotted' });

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myLongExitSignal, 'Long Exit');