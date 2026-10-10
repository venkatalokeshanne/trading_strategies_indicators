describe_indicator('1-Min Rapid Scalper (HA + ADX Trigger)', 'price');

// NOTE: This indicator reproduces the Pine Script's HA + ADX signal
// logic (longTrigger / shortTrigger) for scanning/alerting purposes.
// Order execution, ATR-based TP/SL management and the "1-bar exit"
// are strategy-level behaviors that cannot be reproduced in a
// Custom JS indicator (no strategy.entry/exit, no position tracking).
// Those are exposed as register_signal() outputs only, so they can be
// used in Scanners / Alerts; actual trade management must be done via
// TrendSpider's Strategy Tester module, not this script.

// -------------------- Inputs --------------------
const myMainTab = input.tab('Main Direction & Logic');
const myTradeDir = myMainTab.select('Trade Direction Toggle', 'Both', ['Long', 'Short', 'Both']);

const myIndTab = input.tab('Indicator Settings (ADX)');
const myAdxLen = myIndTab.number('ADX Length', 7, { min: 1, max: 100 });
const myAdxThresh = myIndTab.number('ADX Threshold', 25.0, { min: 0, max: 100 });

const myExitTab = input.tab('Exit Settings (reference only)');
const myUseAtr = myExitTab.boolean('Enable ATR Multiplier Exit', true);
const myAtrLen = myExitTab.number('ATR Length', 14, { min: 1, max: 100 });
const myTpMult = myExitTab.number('Take Profit (ATR Multiplier)', 5.0, { min: 0.1, max: 50 });
const mySlMult = myExitTab.number('Stop Loss (ATR Multiplier)', 1.0, { min: 0.1, max: 50 });
const myPlugPct = myExitTab.number('The Plug (Hard SL %)', 1.0, { min: 0.1, max: 50 });

// -------------------- Heikin Ashi (computed off current chart data) --------------------
const myHaOpen = series_of(null);
const myHaClose = series_of(null);
const myHaHigh = series_of(null);
const myHaLow = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	myHaClose[myIndex] = (open[myIndex] + high[myIndex] + low[myIndex] + close[myIndex]) / 4;

	if (myIndex === 0) {
		myHaOpen[myIndex] = (open[myIndex] + close[myIndex]) / 2;
	}
	else {
		myHaOpen[myIndex] = (myHaOpen[myIndex - 1] + myHaClose[myIndex - 1]) / 2;
	}

	myHaHigh[myIndex] = Math.max(high[myIndex], myHaOpen[myIndex], myHaClose[myIndex]);
	myHaLow[myIndex] = Math.min(low[myIndex], myHaOpen[myIndex], myHaClose[myIndex]);
}

const myHaSize = for_every(myHaClose, myHaOpen, (_c, _o) => Math.abs(_c - _o));
const myIsHaBull = for_every(myHaClose, myHaOpen, (_c, _o) => _c > _o);
const myIsHaBear = for_every(myHaClose, myHaOpen, (_c, _o) => _c < _o);
const myNoWickBull = for_every(myHaOpen, myHaLow, (_o, _l) => _o === _l);
const myNoWickBear = for_every(myHaOpen, myHaHigh, (_o, _h) => _o === _h);

// -------------------- Sequencer (shifted comparisons) --------------------
const myIsHaBullShift2 = shift(myIsHaBull, 2);
const myNoWickBullShift2 = shift(myNoWickBull, 2);
const myBull1 = for_every(myIsHaBullShift2, myNoWickBullShift2, (_b, _nw) => _b && _nw);

const myIsHaBullShift1 = shift(myIsHaBull, 1);
const myNoWickBullShift1 = shift(myNoWickBull, 1);
const myHaSizeShift1 = shift(myHaSize, 1);
const myHaSizeShift2 = shift(myHaSize, 2);
const myBull2 = for_every(myIsHaBullShift1, myNoWickBullShift1, myHaSizeShift1, myHaSizeShift2,
	(_b, _nw, _s1, _s2) => _b && _nw && _s1 > _s2);

const myBull3 = for_every(myIsHaBull, myNoWickBull, myHaSize, myHaSizeShift1,
	(_b, _nw, _s, _s1) => _b && _nw && _s > _s1);

const myIsHaBearShift3 = shift(myIsHaBear, 3);
const myColorFlipBull = myIsHaBearShift3;

const myIsHaBearShift2 = shift(myIsHaBear, 2);
const myNoWickBearShift2 = shift(myNoWickBear, 2);
const myBear1 = for_every(myIsHaBearShift2, myNoWickBearShift2, (_b, _nw) => _b && _nw);

const myIsHaBearShift1 = shift(myIsHaBear, 1);
const myNoWickBearShift1 = shift(myNoWickBear, 1);
const myBear2 = for_every(myIsHaBearShift1, myNoWickBearShift1, myHaSizeShift1, myHaSizeShift2,
	(_b, _nw, _s1, _s2) => _b && _nw && _s1 > _s2);

const myBear3 = for_every(myIsHaBear, myNoWickBear, myHaSize, myHaSizeShift1,
	(_b, _nw, _s, _s1) => _b && _nw && _s > _s1);

const myIsHaBullShift3 = shift(myIsHaBull, 3);
const myColorFlipBear = myIsHaBullShift3;

// -------------------- ADX Filter --------------------
const myAdxObject = indicators.adx(myAdxLen);
const myAdxValue = myAdxObject.adx;

const myLongTriggerRaw = for_every(myColorFlipBull, myBull1, myBull2, myBull3, myAdxValue,
	(_cf, _b1, _b2, _b3, _adx) => Boolean(_cf && _b1 && _b2 && _b3 && _adx > myAdxThresh));

const myShortTriggerRaw = for_every(myColorFlipBear, myBear1, myBear2, myBear3, myAdxValue,
	(_cf, _b1, _b2, _b3, _adx) => Boolean(_cf && _b1 && _b2 && _b3 && _adx > myAdxThresh));

const myLongAllowed = myTradeDir === 'Long' || myTradeDir === 'Both';
const myShortAllowed = myTradeDir === 'Short' || myTradeDir === 'Both';

const myLongTrigger = for_every(myLongTriggerRaw, _t => _t && myLongAllowed);
const myShortTrigger = for_every(myShortTriggerRaw, _t => _t && myShortAllowed);

// -------------------- Reference ATR exit levels (visual only) --------------------
const myAtrValue = atr(high, low, close, myAtrLen);
const myAtrValueShift1 = shift(myAtrValue, 1);

const myLongTp = for_every(myLongTrigger, close, myAtrValueShift1, (_t, _c, _a) => {
	if (!_t || !myUseAtr) return null;
	return _c + _a * myTpMult;
});

const myLongSl = for_every(myLongTrigger, close, myAtrValueShift1, (_t, _c, _a) => {
	if (!_t || !myUseAtr) return null;
	const myAtrStop = _c - _a * mySlMult;
	const myPlugStop = _c * (1 - myPlugPct / 100);
	return Math.max(myAtrStop, myPlugStop);
});

const myShortTp = for_every(myShortTrigger, close, myAtrValueShift1, (_t, _c, _a) => {
	if (!_t || !myUseAtr) return null;
	return _c - _a * myTpMult;
});

const myShortSl = for_every(myShortTrigger, close, myAtrValueShift1, (_t, _c, _a) => {
	if (!_t || !myUseAtr) return null;
	const myAtrStop = _c + _a * mySlMult;
	const myPlugStop = _c * (1 + myPlugPct / 100);
	return Math.min(myAtrStop, myPlugStop);
});

// -------------------- Painting --------------------
const myLongMarker = for_every(myLongTrigger, low, (_t, _l) => _t ? _l : null);
const myShortMarker = for_every(myShortTrigger, high, (_t, _h) => _t ? _h : null);

paint(myLongMarker, { name: 'LongTrigger', style: 'labels_below', color: 'green', thickness: 3 });
paint(myShortMarker, { name: 'ShortTrigger', style: 'labels_above', color: 'red', thickness: 3 });

paint(myLongTp, { name: 'LongTakeProfit', style: 'dotted', color: 'teal' });
paint(myLongSl, { name: 'LongStopLoss', style: 'dotted', color: 'maroon' });
paint(myShortTp, { name: 'ShortTakeProfit', style: 'dotted', color: 'teal' });
paint(myShortSl, { name: 'ShortStopLoss', style: 'dotted', color: 'maroon' });

// -------------------- Signals for Scanners / Alerts / Strategy Tester --------------------
register_signal(myLongTrigger, 'Long Trigger');
register_signal(myShortTrigger, 'Short Trigger');