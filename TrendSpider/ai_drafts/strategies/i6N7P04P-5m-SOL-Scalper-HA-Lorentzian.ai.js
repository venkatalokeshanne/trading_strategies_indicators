describe_indicator('5m SOL Scalper HA Lorentzian', 'price');

// --- Inputs ---
const myHaLen = input.number('HA Smoothing Length', 8, { min: 1, max: 100 });
const myLorWindow = input.number('Lorentzian Lookback', 14, { min: 1, max: 200 });
const myTpPercent = input.number('Take Profit %', 1.5, { min: 0.01, max: 100 }) / 100;
const mySlPercent = input.number('Stop Loss %', 0.8, { min: 0.01, max: 100 }) / 100;

// --- 1. Smoothed Heikin Ashi (via EMA smoothing of OHLC) ---
const mySOpen = ema(open, myHaLen);
const mySHigh = ema(high, myHaLen);
const mySLow = ema(low, myHaLen);
const mySClose = ema(close, myHaLen);

// haClose has a direct (non-recursive) formula, so it can be computed in one pass
const myHaClose = div(add(add(mySOpen, mySHigh), add(mySLow, mySClose)), 4);

// haOpen is recursive: haOpen[0] = (sOpen+sClose)/2, haOpen[n] = (haOpen[n-1] + haClose[n-1]) / 2
// We feed shift(haClose, 1) as the "previous haClose" value into for_every, since haClose
// itself is already fully known (not recursive).
const myShiftedHaClose = shift(myHaClose, 1);
const myHaOpen = for_every(mySOpen, mySClose, myShiftedHaClose, (_o, _c, _prevHaClose, _prevValue, _idx) => {
	if (_idx === 0) {
		return (_o + _c) / 2;
	}
	return (_prevValue + _prevHaClose) / 2;
});

const myHaGreen = for_every(myHaClose, myHaOpen, (_hc, _ho) => _hc > _ho);

// --- 2. Lorentzian Filter (Trend Intensity / velocity) ---
const myVelocitySource = sub(close, shift(close, myLorWindow));
const myLorentzVelocity = linreg(myVelocitySource, myLorWindow);
const myLorentzBullish = for_every(myLorentzVelocity, _v => _v > 0);
const myLorentzBearish = for_every(myLorentzVelocity, _v => _v < 0);

// --- 3. Execution Logic (crossover / crossunder reproduced manually) ---
const myShiftedHaOpenPrev = shift(myHaOpen, 1);
const myCrossOver = for_every(myHaClose, myHaOpen, myShiftedHaClose, myShiftedHaOpenPrev, (_hc, _ho, _phc, _pho) => _hc > _ho && _phc <= _pho);
const myCrossUnder = for_every(myHaClose, myHaOpen, myShiftedHaClose, myShiftedHaOpenPrev, (_hc, _ho, _phc, _pho) => _hc < _ho && _phc >= _pho);

const myLongCondition = for_every(myCrossOver, myLorentzBullish, (_co, _lb) => _co && _lb);
const myShortCondition = for_every(myCrossUnder, myLorentzBearish, (_cu, _lb) => _cu && _lb);

// --- Visuals ---
// plotcandle() has no equivalent in the Custom JS API, so the Smoothed Heikin Ashi
// candles are approximated with lines for Open/Close (High/Low omitted to avoid clutter).
const myHaCloseColor = for_every(myHaGreen, _g => _g ? '#1a9850' : '#d73027');

paint(myHaClose, { name: 'SHA Close', color: myHaCloseColor, thickness: 2 });
paint(myHaOpen, { name: 'SHA Open', color: 'gray', thickness: 1, style: 'dotted' });

const myBuyMarks = for_every(myLongCondition, low, (_l, _lo) => _l ? _lo : null);
const mySellMarks = for_every(myShortCondition, high, (_s, _hi) => _s ? _hi : null);

paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: 'red' });

// --- Signals for Scanner / Alerts / Strategy Tester ---
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');