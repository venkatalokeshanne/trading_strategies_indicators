describe_indicator('NQ Scalping Strategy (EMA plus RSI plus ATR)', 'price');

// ───────────────────────────────────────────────────────────────
// NOTE: TrendSpider Custom JS indicators do not have a strategy
// engine (no strategy.entry/exit/position_size). This script
// reproduces the Pine Script SIGNAL LOGIC exactly (EMA/RSI/ATR,
// session filter, pullback band, trend/momentum conditions) and
// also SIMULATES the position/entry/exit/time-exit bookkeeping
// in plain JS so the Long/Short entry and exit bars match what
// the Pine strategy would produce, bar for bar. These simulated
// entries/exits are exposed as signals for scanning/alerts.
// ───────────────────────────────────────────────────────────────

const myEmaLen = input.number('EMA Length', 100, { min: 1 });
const myRsiLen = input.number('RSI Length', 14, { min: 1 });
const myRsiBull = input.number('RSI Bull Threshold', 55, { min: 0, max: 100, step: 0.5 });
const myRsiBear = input.number('RSI Bear Threshold', 45, { min: 0, max: 100, step: 0.5 });
const myAtrLen = input.number('ATR Length', 14, { min: 1 });
const myStopATR = input.number('Stop ATR Multiplier', 1.0, { min: 0.1, step: 0.1 });
const myTargetATR = input.number('Target ATR Multiplier', 1.2, { min: 0.1, step: 0.1 });
// Shortened title (was too long and caused "input(): name is too lengthy")
const myPullbackPct = input.number('Pullback Band %', 0.10, { min: 0, step: 0.01 });
const myUseSession = input.boolean('Use Session Filter', true);
const mySessionStartHour = input.number('Session Start Hour', 9, { min: 0, max: 23 });
const mySessionStartMinute = input.number('Session Start Min', 30, { min: 0, max: 59 });
const mySessionEndHour = input.number('Session End Hour', 16, { min: 0, max: 23 });
const mySessionEndMinute = input.number('Session End Min', 0, { min: 0, max: 59 });
const myUseTimeExit = input.boolean('Time Exit', true);
const myMaxBarsInTrade = input.number('Max Bars in Trade', 20, { min: 1 });

// ─── Core calculations ───
const myEma = ema(close, myEmaLen);
const myRsi = rsi(close, myRsiLen);
const myAtr = atr(high, low, close, myAtrLen);

// ─── Session filter (approximated using exchange time of each candle) ───
const mySessionFlags = time.map(_t => {
	const myParsed = time_of(_t);
	const myMinutesOfDay = myParsed.hours * 60 + myParsed.minutes;
	const myStartMinutes = mySessionStartHour * 60 + mySessionStartMinute;
	const myEndMinutes = mySessionEndHour * 60 + mySessionEndMinute;
	return myMinutesOfDay >= myStartMinutes && myMinutesOfDay < myEndMinutes;
});
const myInSession = for_every(close, (_c, _p, _i) => !myUseSession || mySessionFlags[_i]);

// ─── Pullback band around EMA ───
const myBand = mult(myEma, myPullbackPct / 100.0);
const myNearEMA = for_every(close, myEma, myBand, (_c, _e, _b) => Math.abs(_c - _e) <= _b);

// ─── Trend direction ───
const myBullTrend = for_every(close, myEma, (_c, _e) => _c > _e);
const myBearTrend = for_every(close, myEma, (_c, _e) => _c < _e);

// ─── Momentum confirmation ───
const myBullMom = for_every(myRsi, _r => _r >= myRsiBull);
const myBearMom = for_every(myRsi, _r => _r <= myRsiBear);

// ─── Entry signals ───
const myLongSignal = for_every(myInSession, myBullTrend, myNearEMA, myBullMom, (_s, _bt, _n, _bm) => _s && _bt && _n && _bm);
const myShortSignal = for_every(myInSession, myBearTrend, myNearEMA, myBearMom, (_s, _bt, _n, _bm) => _s && _bt && _n && _bm);

// ─── Simulate position / entries / exits / time exit bar by bar ───
const myLongEntryMarks = series_of(null);
const myShortEntryMarks = series_of(null);
const myLongExitMarks = series_of(null);
const myShortExitMarks = series_of(null);

let myPositionSize = 0;
let myEntryPrice = null;
let myBarsInTrade = 0;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	if (myPositionSize > 0) {
		myBarsInTrade += 1;
		const myLongStop = myEntryPrice - (myAtr[myIndex] * myStopATR);
		const myLongLimit = myEntryPrice + (myAtr[myIndex] * myTargetATR);
		const myHitStop = low[myIndex] <= myLongStop;
		const myHitLimit = high[myIndex] >= myLongLimit;
		const myHitTime = myUseTimeExit && myBarsInTrade >= myMaxBarsInTrade;

		if (myHitStop || myHitLimit || myHitTime) {
			myLongExitMarks[myIndex] = high[myIndex];
			myPositionSize = 0;
			myEntryPrice = null;
			myBarsInTrade = 0;
		}
	}
	else if (myPositionSize < 0) {
		myBarsInTrade += 1;
		const myShortStop = myEntryPrice + (myAtr[myIndex] * myStopATR);
		const myShortLimit = myEntryPrice - (myAtr[myIndex] * myTargetATR);
		const myHitStop = high[myIndex] >= myShortStop;
		const myHitLimit = low[myIndex] <= myShortLimit;
		const myHitTime = myUseTimeExit && myBarsInTrade >= myMaxBarsInTrade;

		if (myHitStop || myHitLimit || myHitTime) {
			myShortExitMarks[myIndex] = low[myIndex];
			myPositionSize = 0;
			myEntryPrice = null;
			myBarsInTrade = 0;
		}
	}

	if (myPositionSize === 0) {
		if (myLongSignal[myIndex]) {
			myPositionSize = 1;
			myEntryPrice = close[myIndex];
			myBarsInTrade = 0;
			myLongEntryMarks[myIndex] = low[myIndex];
		}
		else if (myShortSignal[myIndex]) {
			myPositionSize = -1;
			myEntryPrice = close[myIndex];
			myBarsInTrade = 0;
			myShortEntryMarks[myIndex] = high[myIndex];
		}
	}
}

// ─── Plotting ───
paint(myEma, { name: 'EMA', color: '#4DA3FF', thickness: 2 });
paint(myLongEntryMarks, { name: 'LongEntry', style: 'labels_below', color: '#26A69A' });
paint(myShortEntryMarks, { name: 'ShortEntry', style: 'labels_above', color: '#EF5350' });
paint(myLongExitMarks, { name: 'LongExit', style: 'labels_above', color: '#26A69A' });
paint(myShortExitMarks, { name: 'ShortExit', style: 'labels_below', color: '#EF5350' });

// ─── Signals for scanning, alerts, backtesting ───
register_signal(myLongSignal, 'Long Signal');
register_signal(myShortSignal, 'Short Signal');
register_signal(for_every(myLongEntryMarks, _v => _v !== null), 'Long Entry Executed');
register_signal(for_every(myShortEntryMarks, _v => _v !== null), 'Short Entry Executed');
register_signal(for_every(myLongExitMarks, _v => _v !== null), 'Long Exit Executed');
register_signal(for_every(myShortExitMarks, _v => _v !== null), 'Short Exit Executed');