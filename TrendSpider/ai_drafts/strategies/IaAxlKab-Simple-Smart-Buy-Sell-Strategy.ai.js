describe_indicator('Simple Smart Buy Sell Strategy', 'price');

// EMA9, EMA20
const myEma9 = ema(close, 9);
const myEma20 = ema(close, 20);

// Session-anchored VWAP, computed manually (cumulative price*volume / cumulative volume),
// resetting at the start of every new trading session (replicates Pine's ta.vwap behavior).
const mySessionIds = time.map(_t => bar_at(_t).session);
const myVwap = series_of(null);
let myCumPV = 0;
let myCumVol = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myNewSession = myIndex === 0 || mySessionIds[myIndex] !== mySessionIds[myIndex - 1];
	if (myNewSession) {
		myCumPV = 0;
		myCumVol = 0;
	}
	myCumPV += close[myIndex] * volume[myIndex];
	myCumVol += volume[myIndex];
	myVwap[myIndex] = myCumVol !== 0 ? myCumPV / myCumVol : close[myIndex];
}

// ATR(14), used for TP/SL reference levels
const myAtr = atr(high, low, close, 14);

// Trend conditions
const myBullTrend = for_every(close, myVwap, myEma9, myEma20, (_c, _v, _e9, _e20) => _c > _v && _e9 > _e20);
const myBearTrend = for_every(close, myVwap, myEma9, myEma20, (_c, _v, _e9, _e20) => _c < _v && _e9 < _e20);

const myPrevHigh = shift(high, 1);
const myPrevLow = shift(low, 1);

// Buy: bullish trend, pullback into EMA9, momentum returns (close breaks prior high)
const myBuySignal = for_every(myBullTrend, low, myEma9, close, myPrevHigh, (_bull, _low, _e9, _close, _ph) => Boolean(_bull) && _low <= _e9 && _close > _ph);

// Sell: bearish trend, failed bounce into EMA9, momentum drops (close breaks prior low)
const mySellSignal = for_every(myBearTrend, high, myEma9, close, myPrevLow, (_bear, _high, _e9, _close, _pl) => Boolean(_bear) && _high >= _e9 && _close < _pl);

// Reference exit levels (informational only, computed at the current candle's ATR;
// these are not an actual backtested strategy, see note below)
const myBuyStop = for_every(close, myAtr, (_c, _a) => _c - _a);
const myBuyTarget = for_every(close, myAtr, (_c, _a) => _c + _a * 2);
const mySellStop = for_every(close, myAtr, (_c, _a) => _c + _a);
const mySellTarget = for_every(close, myAtr, (_c, _a) => _c - _a * 2);

// Plots
paint(myEma9, { name: 'EMA9', color: '#00FF7F', thickness: 2 });
paint(myEma20, { name: 'EMA20', color: '#EF5350', thickness: 2 });
paint(myVwap, { name: 'VWAP', color: '#FFA500', thickness: 2 });

// Buy/Sell markers
const myBuyLabels = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellLabels = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyLabels, { name: 'BuySignal', style: 'labels_below', color: '#00FF7F' });
paint(mySellLabels, { name: 'SellSignal', style: 'labels_above', color: '#EF5350' });

// Reference exit levels, only shown on signal candles (sparse)
const myBuyStopLine = for_every(myBuySignal, myBuyStop, (_b, _s) => _b ? _s : null);
const myBuyTargetLine = for_every(myBuySignal, myBuyTarget, (_b, _t) => _b ? _t : null);
const mySellStopLine = for_every(mySellSignal, mySellStop, (_s, _st) => _s ? _st : null);
const mySellTargetLine = for_every(mySellSignal, mySellTarget, (_s, _tg) => _s ? _tg : null);

paint(myBuyStopLine, { name: 'BuyStop', style: 'dotted', color: '#EF5350' });
paint(myBuyTargetLine, { name: 'BuyTarget', style: 'dotted', color: '#00FF7F' });
paint(mySellStopLine, { name: 'SellStop', style: 'dotted', color: '#00FF7F' });
paint(mySellTargetLine, { name: 'SellTarget', style: 'dotted', color: '#EF5350' });

// Signals for scanners, alerts and strategy tester
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');