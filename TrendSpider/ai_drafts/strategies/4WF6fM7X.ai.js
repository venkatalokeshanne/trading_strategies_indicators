describe_indicator('Naked K 5min Sniper', 'price');

// ===== Inputs (grouped since we have more than 4) =====
const myParamsTab = input.tab('Parameters');

const myTrendGroup = myParamsTab.group('Trend / Support-Resistance');
const myLookback = myTrendGroup.number('Support/Resistance Lookback', 6, { min: 3, max: 12 });
const mySmaLen = myTrendGroup.number('Trend SMA Length', 9, { min: 5, max: 20 });

const myAtrGroup = myParamsTab.group('ATR / Risk');
const myAtrLen = myAtrGroup.number('ATR Length', 7, { min: 5, max: 50 });
const myAtrMultSL = myAtrGroup.number('Stop Loss ATR Multiplier', 1.8, { min: 1.0, max: 10, step: 0.1 });
const myRrRatio = myAtrGroup.number('Risk Reward Ratio', 1.5, { min: 1.0, max: 10, step: 0.1 });

const myFilterGroup = myParamsTab.group('Filters');
const myUseVolumeFilter = myFilterGroup.boolean('Enable Volume Filter', true);
const myCooldownBars = myFilterGroup.number('Cooldown Bars', 3, { min: 0, max: 50 });

// ===== Trend filter =====
const mySmaFast = sma(close, mySmaLen);
const myUptrend = for_every(close, mySmaFast, (_c, _s) => _c > _s);
const myDowntrend = for_every(close, mySmaFast, (_c, _s) => _c < _s);

// ===== Support / Resistance zone =====
const myRecentLow = lowest(low, myLookback);
const myRecentHigh = highest(high, myLookback);
const myNearSupport = for_every(low, myRecentLow, (_l, _rl) => _l <= _rl * 1.002);
const myNearResistance = for_every(high, myRecentHigh, (_h, _rh) => _h >= _rh * 0.998);

// ===== Candle shape math =====
const myBody = for_every(open, close, (_o, _c) => Math.abs(_o - _c));
const myCandleRange = sub(high, low);
const myLowerShadow = for_every(open, close, low, (_o, _c, _l) => Math.min(_o, _c) - _l);
const myUpperShadow = for_every(open, close, high, (_o, _c, _h) => _h - Math.max(_o, _c));
const myAtrValue = atr(high, low, close, myAtrLen);

// Pin Bar logic
const myIsBullPin = for_every(myLowerShadow, myBody, myUpperShadow, myCandleRange, myAtrValue,
	(_ls, _b, _us, _cr, _a) => _ls >= 2 * _b && _us <= 0.3 * _b && _cr > _a * 0.5
);
const myIsBearPin = for_every(myUpperShadow, myBody, myLowerShadow, myCandleRange, myAtrValue,
	(_us, _b, _ls, _cr, _a) => _us >= 2 * _b && _ls <= 0.3 * _b && _cr > _a * 0.5
);

// Engulfing pattern
const myOpenPrev = shift(open, 1);
const myClosePrev = shift(close, 1);
const myBullEngulf = for_every(myOpenPrev, myClosePrev, open, close,
	(_op, _cp, _o, _c) => _op > _cp && _c > _o && _c > _op && _o < _cp
);
const myBearEngulf = for_every(myOpenPrev, myClosePrev, open, close,
	(_op, _cp, _o, _c) => _op < _cp && _c < _o && _c < _op && _o > _cp
);

// ===== Volume filter (optional) =====
const myVolAvg = sma(volume, 5);
const myVolOK = for_every(volume, myVolAvg, (_v, _va) => !myUseVolumeFilter || _v >= _va * 1.2);

// ===== Raw signal generation =====
const myBullishPattern = for_every(myIsBullPin, myBullEngulf, (_a, _b) => _a || _b);
const myBearishPattern = for_every(myIsBearPin, myBearEngulf, (_a, _b) => _a || _b);

const myHighPrev = shift(high, 1);
const myLowPrev = shift(low, 1);

const myLongSignalRaw = for_every(myUptrend, myNearSupport, myBullishPattern, close, myHighPrev, myVolOK,
	(_ut, _ns, _bp, _c, _hp, _v) => _ut && _ns && _bp && _c > _hp && _v
);
const myShortSignalRaw = for_every(myDowntrend, myNearResistance, myBearishPattern, close, myLowPrev, myVolOK,
	(_dt, _nr, _bp, _c, _lp, _v) => _dt && _nr && _bp && _c < _lp && _v
);

// ===== Cooldown control (stateful, sequential, no indicator calls inside loop) =====
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
let myLastTradeBar = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myInCooldown = myLastTradeBar !== null && (myIndex - myLastTradeBar) <= myCooldownBars;
	const myLong = Boolean(myLongSignalRaw[myIndex]) && !myInCooldown;
	const myShort = Boolean(myShortSignalRaw[myIndex]) && !myInCooldown;

	myLongSignal[myIndex] = myLong;
	myShortSignal[myIndex] = myShort;

	if (myLong || myShort) {
		myLastTradeBar = myIndex;
	}
}

// ===== Register signals for scanners / alerts / strategy tester =====
register_signal(myLongSignal, 'Long Signal');
register_signal(myShortSignal, 'Short Signal');

// ===== Visualization =====
const myBuyMarks = for_every(myLongSignal, low, (_sig, _l) => (_sig ? _l : null));
const mySellMarks = for_every(myShortSignal, high, (_sig, _h) => (_sig ? _h : null));

paint(mySmaFast, { name: 'SMA9', color: 'orange', thickness: 2 });
paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });