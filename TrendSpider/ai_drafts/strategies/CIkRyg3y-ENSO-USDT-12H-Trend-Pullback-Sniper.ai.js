describe_indicator('ENSO Trend Pullback Sniper', 'price');

// ── Inputs ──────────────────────────────────────────────────────────────
const myEmaTab = input.tab('EMA');
const myEmaFastLen = myEmaTab.number('EMA Fast Length', 9, { min: 1, max: 200 });
const myEmaMidLen = myEmaTab.number('EMA Mid Length', 21, { min: 1, max: 200 });
const myEmaSlowLen = myEmaTab.number('EMA Slow Length', 50, { min: 1, max: 500 });

const myStochTab = input.tab('Stochastic RSI');
const myStochRow1 = myStochTab.row();
const myStochRsiLen = myStochRow1.number('Stoch RSI Length', 14, { min: 1, max: 200 });
const myStochK = myStochRow1.number('Stoch K Smoothing', 3, { min: 1, max: 50 });
const myStochRow2 = myStochTab.row();
const myStochD = myStochRow2.number('Stoch D Smoothing', 3, { min: 1, max: 50 });
const myStochOB = myStochRow2.number('Stoch Overbought', 80, { min: 50, max: 100 });
const myStochOS = myStochTab.number('Stoch Oversold', 20, { min: 0, max: 50 });

const myAtrTab = input.tab('ATR / Risk');
const myAtrLen = myAtrTab.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrRow = myAtrTab.row();
// Shortened input titles below; the platform rejects input names
// that are too long. These names were trimmed while keeping their meaning.
const mySlMulti = myAtrRow.number('SL ATR Mult', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myTp1Multi = myAtrRow.number('TP1 ATR Mult', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myTp2Multi = myAtrRow.number('TP2 ATR Mult', 3.0, { min: 0.1, max: 20, step: 0.1 });
const myPullbackATR = myAtrTab.number('Pullback Zone (ATR)', 1.0, { min: 0.1, max: 10, step: 0.1 });

// ── Core calculations ──────────────────────────────────────────────────
const myEmaFast = ema(close, myEmaFastLen);
const myEmaMid = ema(close, myEmaMidLen);
const myEmaSlow = ema(close, myEmaSlowLen);

// NOTE: Pine's ta.vwap resets every session; the engine's vwap() here is
// anchored from the first candle of the whole data set, which is the
// closest native equivalent available.
const myVwapVal = vwap();
const myAtrVal = atr(high, low, close, myAtrLen);

const myRsiVal = rsi(close, myStochRsiLen);
const myStochRaw = stochastic(myRsiVal, myRsiVal, myRsiVal, myStochRsiLen);
const myStochKVal = sma(myStochRaw, myStochK);
const myStochDVal = sma(myStochKVal, myStochD);
const myStochKPrev = shift(myStochKVal, 1);
const myStochDPrev = shift(myStochDVal, 1);

const myStochCrossUp = for_every(myStochKVal, myStochDVal, myStochKPrev, myStochDPrev, (_k, _d, _kp, _dp) => _k > _d && _kp <= _dp);
const myStochCrossDown = for_every(myStochKVal, myStochDVal, myStochKPrev, myStochDPrev, (_k, _d, _kp, _dp) => _k < _d && _kp >= _dp);

const myUptrendEMA = for_every(myEmaFast, myEmaMid, myEmaSlow, close, (_f, _m, _s, _c) => _f > _m && _c > _s);
const myDowntrendEMA = for_every(myEmaFast, myEmaMid, myEmaSlow, close, (_f, _m, _s, _c) => _f < _m && _c < _s);

const myBullishVWAP = for_every(close, myVwapVal, (_c, _v) => _c > _v);
const myBearishVWAP = for_every(close, myVwapVal, (_c, _v) => _c < _v);

const myNearEMA21 = for_every(close, myEmaMid, myAtrVal, (_c, _m, _a) => Math.abs(_c - _m) <= (_a * myPullbackATR));

const myStochOSCross = for_every(myStochCrossUp, myStochKPrev, (_cu, _kp) => _cu && _kp < myStochOS);
const myStochOBCross = for_every(myStochCrossDown, myStochKPrev, (_cd, _kp) => _cd && _kp > myStochOB);

const myLongCondition = for_every(
	myUptrendEMA, myBullishVWAP, myNearEMA21, myStochOSCross,
	(_u, _b, _n, _s) => _u && _b && _n && _s
);
const myShortCondition = for_every(
	myDowntrendEMA, myBearishVWAP, myNearEMA21, myStochOBCross,
	(_d, _b, _n, _s) => _d && _b && _n && _s
);

// ── Position simulation (approximation of the strategy engine) ────────
// NOTE: Partial exits (50% at TP1, 50% at TP2) and real order fills are
// not something a Custom JS indicator can execute. This loop approximates
// the strategy by tracking a single flat/long/short state, exiting fully
// at SL, TP2, or EMA50 invalidation, using intrabar high/low for touches.
const myLongEntry = series_of(false);
const myShortEntry = series_of(false);
const myExitSignal = series_of(false);

let myPosition = 0;
let mySlPrice = null;
let myTp1Price = null;
let myTp2Price = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPosition === 0) {
		if (myLongCondition[myIndex]) {
			myPosition = 1;
			mySlPrice = close[myIndex] - (myAtrVal[myIndex] * mySlMulti);
			myTp1Price = close[myIndex] + (myAtrVal[myIndex] * myTp1Multi);
			myTp2Price = close[myIndex] + (myAtrVal[myIndex] * myTp2Multi);
			myLongEntry[myIndex] = true;
		}
		else if (myShortCondition[myIndex]) {
			myPosition = -1;
			mySlPrice = close[myIndex] + (myAtrVal[myIndex] * mySlMulti);
			myTp1Price = close[myIndex] - (myAtrVal[myIndex] * myTp1Multi);
			myTp2Price = close[myIndex] - (myAtrVal[myIndex] * myTp2Multi);
			myShortEntry[myIndex] = true;
		}
	}
	else if (myPosition === 1) {
		if (low[myIndex] <= mySlPrice || high[myIndex] >= myTp2Price || close[myIndex] < myEmaSlow[myIndex]) {
			myExitSignal[myIndex] = true;
			myPosition = 0;
		}
	}
	else if (myPosition === -1) {
		if (high[myIndex] >= mySlPrice || low[myIndex] <= myTp2Price || close[myIndex] > myEmaSlow[myIndex]) {
			myExitSignal[myIndex] = true;
			myPosition = 0;
		}
	}
}

// ── Plots ───────────────────────────────────────────────────────────────
paint(myEmaFast, { name: 'EMA Fast', color: '#2ecc71', thickness: 1 });
paint(myEmaMid, { name: 'EMA Mid', color: '#f39c12', thickness: 2 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#e74c3c', thickness: 2 });
paint(myVwapVal, { name: 'VWAP', color: '#9b59b6', thickness: 1 });

const myLongMarks = for_every(myLongEntry, low, (_s, _l) => _s ? _l : null);
const myShortMarks = for_every(myShortEntry, high, (_s, _h) => _s ? _h : null);

paint(myLongMarks, { name: 'Long Signal', style: 'labels_below', color: '#2ecc71', thickness: 3 });
paint(myShortMarks, { name: 'Short Signal', style: 'labels_above', color: '#e74c3c', thickness: 3 });

// Approximation of bgcolor trend highlight using candle coloring
const myTrendColors = for_every(myUptrendEMA, myBullishVWAP, myDowntrendEMA, myBearishVWAP,
	(_u, _bv, _d, _bear) => (_u && _bv) ? 'rgba(46,204,113,0.15)' : (_d && _bear) ? 'rgba(231,76,60,0.15)' : null);
color_candles(myTrendColors);

// ── Scanner / Alert / Strategy signals ─────────────────────────────────
register_signal(myLongEntry, 'Long Entry');
register_signal(myShortEntry, 'Short Entry');
register_signal(myExitSignal, 'Position Exit');