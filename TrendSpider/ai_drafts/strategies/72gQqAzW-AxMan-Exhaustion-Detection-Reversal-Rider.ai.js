describe_indicator('Sniper V4 Liquidity and Fast Exhaustion', 'price');

// --- INPUTS ---
const myRsiLen = input.number('RSI Period', 14, { min: 1, max: 200 });
const myVolMult = input.number('Volume Sensitivity', 1.2, { min: 0.1, max: 10, step: 0.1 });
const myExpireBar = input.number('Entry Window (Candles)', 12, { min: 1, max: 200 });
const myLiqLookback = input.number('Liquidity Pool Lookback', 20, { min: 1, max: 500 });

// --- INDICATORS ---
const myRsi = rsi(close, myRsiLen);
const myVolAvg = sma(volume, 20);

const myPoolHigh = shift(highest(high, myLiqLookback), 1);
const myPoolLow = shift(lowest(low, myLiqLookback), 1);
const myPrevLow = shift(low, 1);
const myPrevHigh = shift(high, 1);
const myPrevClose = shift(close, 1);
const myPrevRsi = shift(myRsi, 1);

// Liquidity grabs
const myIsBullGrab = for_every(low, myPoolLow, close, (_l, _pl, _c) => (_pl != null && _l < _pl && _c > _pl));
const myIsBearGrab = for_every(high, myPoolHigh, close, (_h, _ph, _c) => (_ph != null && _h > _ph && _c < _ph));

// Exhaustion conditions
const myBullExhaustion = for_every(myRsi, volume, myVolAvg, low, myPrevLow, myIsBullGrab, (_r, _v, _va, _l, _pl, _grab) => {
	return (_r < 35) && (_v > _va * myVolMult) && ((_l < _pl) || _grab);
});

const myBearExhaustion = for_every(myRsi, volume, myVolAvg, high, myPrevHigh, myIsBearGrab, (_r, _v, _va, _h, _ph, _grab) => {
	return (_r > 65) && (_v > _va * myVolMult) && ((_h > _ph) || _grab);
});

// --- STATEFUL SEQUENTIAL LOGIC (mirrors Pine's var-based bar tracking and strategy position) ---
// This cannot be expressed with built-in vectorized functions because it depends on
// a running position state and "last exhaustion bar" memory, exactly like the Pine script.
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const myCloseLongSignal = series_of(false);
const myCloseShortSignal = series_of(false);
const myBullActive = series_of(false);
const myBearActive = series_of(false);

let myLastBullBar = 0;
let myLastBearBar = 0;
let myHasLastBullBar = false;
let myHasLastBearBar = false;
let myPositionSize = 0; // 0 = flat, 1 = long, -1 = short

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myBullExhaustion[myIndex]) {
		myLastBullBar = myIndex;
		myHasLastBullBar = true;
	}
	if (myBearExhaustion[myIndex]) {
		myLastBearBar = myIndex;
		myHasLastBearBar = true;
	}

	const myBullIsActive = myHasLastBullBar && ((myIndex - myLastBullBar) <= myExpireBar);
	const myBearIsActive = myHasLastBearBar && ((myIndex - myLastBearBar) <= myExpireBar);

	myBullActive[myIndex] = myBullIsActive;
	myBearActive[myIndex] = myBearIsActive;

	const myCrossoverClose = myIndex > 0 && close[myIndex] > myPrevHigh[myIndex] && close[myIndex - 1] <= myPrevHigh[myIndex - 1];
	const myCrossunderClose = myIndex > 0 && close[myIndex] < myPrevLow[myIndex] && close[myIndex - 1] >= myPrevLow[myIndex - 1];

	const myLong = myBullIsActive && myCrossoverClose && (myRsi[myIndex] > myPrevRsi[myIndex]) && (myPositionSize === 0);
	const myShort = myBearIsActive && myCrossunderClose && (myRsi[myIndex] < myPrevRsi[myIndex]) && (myPositionSize === 0);
	const myCloseLong = myBearExhaustion[myIndex] && (myPositionSize > 0);
	const myCloseShort = myBullExhaustion[myIndex] && (myPositionSize < 0);

	myLongSignal[myIndex] = myLong;
	myShortSignal[myIndex] = myShort;
	myCloseLongSignal[myIndex] = myCloseLong;
	myCloseShortSignal[myIndex] = myCloseShort;

	if (myLong) {
		myPositionSize = 1;
		myLastBullBar = 0;
		myHasLastBullBar = false;
	}
	if (myShort) {
		myPositionSize = -1;
		myLastBearBar = 0;
		myHasLastBearBar = false;
	}
	if (myCloseLong) {
		myPositionSize = 0;
	}
	if (myCloseShort) {
		myPositionSize = 0;
	}
}

// --- VISUALS ---
paint(myPoolHigh, { name: 'Liquidity Top', color: 'red', style: 'line' });
paint(myPoolLow, { name: 'Liquidity Bottom', color: 'green', style: 'line' });

const myBullExhaustionMarks = for_every(myBullExhaustion, low, (_e, _l) => _e ? _l : null);
const myBearExhaustionMarks = for_every(myBearExhaustion, high, (_e, _h) => _e ? _h : null);

paint(myBullExhaustionMarks, { name: 'Bull Exhaustion Marker', style: 'labels_below', color: 'gold' });
paint(myBearExhaustionMarks, { name: 'Bear Exhaustion Marker', style: 'labels_above', color: 'orange' });

const myLongMarks = for_every(myLongSignal, low, (_s, _l) => _s ? _l : null);
const myShortMarks = for_every(myShortSignal, high, (_s, _h) => _s ? _h : null);
const myCloseLongMarks = for_every(myCloseLongSignal, high, (_s, _h) => _s ? _h : null);
const myCloseShortMarks = for_every(myCloseShortSignal, low, (_s, _l) => _s ? _l : null);

paint(myLongMarks, { name: 'Long Entry Marker', style: 'labels_below', color: 'green' });
paint(myShortMarks, { name: 'Short Entry Marker', style: 'labels_above', color: 'red' });
paint(myCloseLongMarks, { name: 'Close Long Marker', style: 'labels_above', color: 'fuchsia' });
paint(myCloseShortMarks, { name: 'Close Short Marker', style: 'labels_below', color: 'aqua' });

// --- SIGNALS FOR SCANNERS, ALERTS AND STRATEGY TESTER ---
// Note: signal names must be distinct from the paint() names above, since both
// paint() and register_signal() share the same output namespace. Previously
// 'Bull Exhaustion' was used for both a paint() line and a register_signal(),
// which triggered the "already exists" error.
register_signal(myBullExhaustion, 'Bull Exhaustion Signal');
register_signal(myBearExhaustion, 'Bear Exhaustion Signal');
register_signal(myBullActive, 'Bull Ready State Active');
register_signal(myBearActive, 'Bear Ready State Active');
register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myShortSignal, 'Short Entry Signal');
register_signal(myCloseLongSignal, 'Close Long Exit');
register_signal(myCloseShortSignal, 'Close Short Exit');